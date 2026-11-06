import argparse
import pickle
from pathlib import Path
import sys

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
    } if videos_dir.is_dir() else {}
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
                for video_path in video_paths:
                    samples, frame_count, skipped_count = process_video(
                        video_path,
                        face_mesh,
                        hands,
                        frame_step,
                        require_hand=True,
                    )
                    if not samples:
                        raise ValueError(
                            f"No hand landmarks detected in {video_path}. "
                            "Check the video framing and camera quality."
                        )

                    samples = np.asarray(samples, dtype=np.float32)
                    for indices in np.array_split(
                        np.arange(len(samples)), CV_SPLITS
                    ):
                        if len(indices):
                            class_samples.extend(samples[indices])
                            class_groups.extend([next_group] * len(indices))
                            next_group += 1

                    print(
                        f"Video {video_path}: "
                        f"{len(samples)} hand frames from {frame_count} frames"
                        + (f", {skipped_count} invalid frames" if skipped_count else "")
                    )

                print(
                    f"{class_name}: using {len(video_paths)} video(s); "
                    f"ignoring {data_files[class_name].name if class_name in data_files else 'no .npy file'}"
                )
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
    parser.add_argument("--confidence", type=float, default=0.5)
    parser.add_argument("--step", type=int, default=2, help="Process every Nth video frame")
    args = parser.parse_args()

    if not 0 <= args.confidence <= 1:
        parser.error("--confidence must be between 0 and 1")
    if args.step < 1:
        parser.error("--step must be at least 1")

    data_dir = ROOT_DIR / "data"
    videos_dir = Path(args.video_dir)
    if not videos_dir.is_absolute():
        videos_dir = ROOT_DIR / videos_dir
    X, y, groups, mapping = load_dataset(
        data_dir, videos_dir, args.confidence, args.step
    )
    class_ids = np.arange(len(mapping))
    out_of_fold_predictions = np.empty_like(y)
    splitter = GroupKFold(n_splits=CV_SPLITS)

    for train_indices, validation_indices in splitter.split(X, y, groups):
        classifier = SVC(
            kernel="rbf",
            C=30,
            class_weight="balanced",
            decision_function_shape="ovo",
        )
        classifier.fit(X[train_indices], y[train_indices])
        out_of_fold_predictions[validation_indices] = classifier.predict(
            X[validation_indices]
        )

    print(f"Training examples: {len(X)}. Num classes: {len(mapping)}")
    print(
        "5-fold time-blocked validation: "
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

    final_model = SVC(
        kernel="rbf",
        C=30,
        class_weight="balanced",
        decision_function_shape="ovo",
    )
    final_model.fit(X, y)

    output_dir = Path(args.dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / f"{args.model_name.removesuffix('.pkl')}.pkl"
    with model_path.open("wb") as model_file:
        pickle.dump((final_model, mapping), model_file)
    print(f"Saved model to {model_path}")


if __name__ == "__main__":
    main()
