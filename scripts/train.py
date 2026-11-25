import argparse
import pickle
from pathlib import Path
import sys
import time

import numpy as np
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import GroupKFold
from sklearn.svm import SVC

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from config import HAND_DETECTION_CONFIDENCE, HAND_MODEL_COMPLEXITY
from utils.feature_extraction import FEATURE_COUNT, normalize_hand_features

from scripts.video_to_data import VIDEO_EXTENSIONS, process_video

CV_SPLITS = 5


def load_dataset(data_dir, videos_dir, confidence, frame_step):
    data_files = {
        data_file.stem: data_file
        for data_file in data_dir.glob("*.npy")
    } if data_dir.is_dir() else {}
    video_files_by_class = {
        class_dir.name: sorted(
            path
            for path in class_dir.iterdir()
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
        )
        for class_dir in videos_dir.iterdir()
        if class_dir.is_dir()
    } if videos_dir is not None and videos_dir.is_dir() else {}
    video_files_by_class = {
        label: paths for label, paths in video_files_by_class.items() if paths
    }

    class_names = sorted(set(data_files) | set(video_files_by_class))
    if not class_names:
        raise FileNotFoundError(
            f"No .npy training data found in {data_dir} "
            f"or labeled videos in {videos_dir}"
        )

    features = []
    sample_labels = []
    groups = []
    mapping = {}
    next_group = 0
    skipped_video_count = 0
    skipped_class_count = 0

    face_mesh = None
    hands = None
    if video_files_by_class:
        import mediapipe as mp

        face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=confidence,
            min_tracking_confidence=confidence,
        )
        hands = mp.solutions.hands.Hands(
            static_image_mode=True,
            max_num_hands=2,
            model_complexity=HAND_MODEL_COMPLEXITY,
            min_detection_confidence=HAND_DETECTION_CONFIDENCE,
            min_tracking_confidence=HAND_DETECTION_CONFIDENCE,
        )

    try:
        for class_name in class_names:
            class_samples = []
            class_groups = []
            video_paths = video_files_by_class.get(class_name, [])

            if video_paths:
                used_video_count = 0
                for video_path in video_paths:
                    samples, frame_count, skipped_count = process_video(
                        video_path,
                        face_mesh,
                        hands,
                        frame_step,
                        require_hand=True,
                    )
                    if frame_count == 0:
                        skipped_video_count += 1
                        print(
                            f"[SKIP] Video {video_path}: no frames could be read; "
                            "excluded from training."
                        )
                        continue
                    if not samples:
                        skipped_video_count += 1
                        print(
                            f"[SKIP] Video {video_path}: no hand landmarks "
                            f"detected in {frame_count} frames; "
                            "excluded from training."
                        )
                        continue

                    samples = np.asarray(samples, dtype=np.float32)
                    for indices in np.array_split(
                        np.arange(len(samples)), CV_SPLITS
                    ):
                        if len(indices):
                            class_samples.extend(samples[indices])
                            class_groups.extend([next_group] * len(indices))
                            next_group += 1

                    used_video_count += 1
                    print(
                        f"Video {video_path}: "
                        f"{len(samples)} hand frames from {frame_count} frames"
                        + (f", {skipped_count} invalid frames" if skipped_count else "")
                    )

                print(
                    f"{class_name}: using {used_video_count}/{len(video_paths)} "
                    "video(s); "
                    f"ignoring {data_files[class_name].name if class_name in data_files else 'no .npy file'}"
                )
                if not class_samples:
                    skipped_class_count += 1
                    print(
                        f"[SKIP] Class {class_name}: no usable videos; "
                        "class excluded from training."
                    )
                    continue
            else:
                data_file = data_files[class_name]
                samples = np.load(data_file).astype(np.float32)
                if samples.ndim != 2 or samples.shape[1] != FEATURE_COUNT:
                    raise ValueError(
                        f"{data_file} must have shape (samples, {FEATURE_COUNT}); "
                        f"received {samples.shape}"
                    )
                if not np.isfinite(samples).all():
                    raise ValueError(f"{data_file} contains non-finite features")
                if len(samples) < CV_SPLITS:
                    raise ValueError(
                        f"{data_file} needs at least {CV_SPLITS} samples for validation"
                    )
                class_samples.extend(samples)

                for indices in np.array_split(np.arange(len(samples)), CV_SPLITS):
                    if len(indices):
                        class_groups.extend([next_group] * len(indices))
                        next_group += 1

                print(f"{class_name}: using {len(samples)} samples from {data_file.name}")

            features.extend(class_samples)
            sample_labels.extend([len(mapping)] * len(class_samples))
            groups.extend(class_groups)
            mapping[len(mapping)] = class_name
    finally:
        if face_mesh is not None:
            face_mesh.close()
        if hands is not None:
            hands.close()

    print(
        f"Skipped videos: {skipped_video_count}; "
        f"classes with no usable samples: {skipped_class_count}"
    )
    if not features:
        raise ValueError("No usable training samples were found.")

    return (
        normalize_hand_features(np.vstack(features)),
        np.asarray(sample_labels),
        np.asarray(groups),
        mapping,
    )


def main():
    parser = argparse.ArgumentParser(description="Train the SignTalk classifier")
    parser.add_argument("--model_name", default="model", help="Name of the output model")
    parser.add_argument("--dir", default="models", help="Output directory")
    parser.add_argument("--video_dir", default="videos", help="Folders of labeled videos")
    parser.add_argument(
        "--data_only",
        action="store_true",
        help="Train only from cached .npy files; do not process videos",
    )
    parser.add_argument("--confidence", type=float, default=0.5)
    parser.add_argument("--step", type=int, default=2, help="Process every Nth video frame")
    args = parser.parse_args()

    if not 0 <= args.confidence <= 1:
        parser.error("--confidence must be between 0 and 1")
    if args.step < 1:
        parser.error("--step must be at least 1")

    total_started = time.perf_counter()
    print("[1/3] Loading and preparing training data...")
    data_started = time.perf_counter()
    data_dir = ROOT_DIR / "data"
    videos_dir = None
    if not args.data_only:
        videos_dir = Path(args.video_dir)
        if not videos_dir.is_absolute():
            videos_dir = ROOT_DIR / videos_dir
    X, y, groups, mapping = load_dataset(
        data_dir, videos_dir, args.confidence, args.step
    )
    print(
        f"[1/3] Ready: {len(X)} samples, {len(mapping)} classes, "
        f"{len(np.unique(groups))} groups "
        f"({time.perf_counter() - data_started:.1f}s)"
    )

    class_ids = np.arange(len(mapping))
    out_of_fold_predictions = np.empty_like(y)
    splitter = GroupKFold(n_splits=CV_SPLITS)
    cv_started = time.perf_counter()
    print(f"[2/3] Starting {CV_SPLITS}-fold grouped validation...")

    for fold, (train_indices, validation_indices) in enumerate(
        splitter.split(X, y, groups),
        start=1,
    ):
        fold_started = time.perf_counter()
        train_class_count = len(np.unique(y[train_indices]))
        validation_class_count = len(np.unique(y[validation_indices]))
        print(
            f"[CV {fold}/{CV_SPLITS}] Fitting: "
            f"train={len(train_indices)}, validation={len(validation_indices)}, "
            f"classes train/validation="
            f"{train_class_count}/{validation_class_count}"
        )

        classifier = SVC(
            kernel="rbf",
            C=30,
            class_weight="balanced",
            decision_function_shape="ovo",
        )
        classifier.fit(X[train_indices], y[train_indices])
        fold_predictions = classifier.predict(X[validation_indices])
        out_of_fold_predictions[validation_indices] = fold_predictions

        fold_accuracy = accuracy_score(y[validation_indices], fold_predictions)
        fold_f1 = f1_score(
            y[validation_indices],
            fold_predictions,
            labels=class_ids,
            average="macro",
            zero_division=0,
        )
        print(
            f"[CV {fold}/{CV_SPLITS}] Complete in "
            f"{time.perf_counter() - fold_started:.1f}s: "
            f"accuracy={fold_accuracy * 100:.2f}%, macro F1={fold_f1:.3f}"
        )

    cv_elapsed = time.perf_counter() - cv_started
    print(
        f"[2/3] 5-fold out-of-fold result ({cv_elapsed:.1f}s): "
        f"accuracy={accuracy_score(y, out_of_fold_predictions) * 100:.2f}%, "
        f"macro F1={f1_score(y, out_of_fold_predictions, average='macro'):.3f}"
    )
    print(
        classification_report(
            y,
            out_of_fold_predictions,
            labels=class_ids,
            target_names=[mapping[index] for index in class_ids],
            zero_division=0,
        )
    )

    print(f"[3/3] Fitting final model on all {len(X)} samples...")
    final_started = time.perf_counter()
    final_model = SVC(
        kernel="rbf",
        C=30,
        class_weight="balanced",
        decision_function_shape="ovo",
    )
    final_model.fit(X, y)
    print(f"[3/3] Final fit complete in {time.perf_counter() - final_started:.1f}s")

    output_dir = Path(args.dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / f"{args.model_name.removesuffix('.pkl')}.pkl"
    with model_path.open("wb") as model_file:
        pickle.dump((final_model, mapping), model_file)
    print(f"Saved model to {model_path}")
    print(f"Total elapsed time: {time.perf_counter() - total_started:.1f}s")


if __name__ == "__main__":
    main()
