import argparse
import pickle
import time
from pathlib import Path

import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT_DIR = Path(__file__).resolve().parents[1]
POINT_SHAPE = (76, 3)


def resample_sequence(sequence, frame_count):
    positions = np.linspace(0, len(sequence) - 1, frame_count)
    left = positions.astype(np.intp)
    right = np.minimum(left + 1, len(sequence) - 1)
    weights = (positions - left).astype(np.float32)[:, None, None]
    return (
        sequence[left] * (1.0 - weights)
        + sequence[right] * weights
    ).astype(np.float32, copy=False)


def load_split(split_dir, label_to_id, frame_count, split_name):
    if not split_dir.is_dir():
        raise FileNotFoundError(f"{split_name} data directory not found: {split_dir}")

    files = []
    labels = []
    for class_dir in sorted(path for path in split_dir.iterdir() if path.is_dir()):
        npy_files = sorted(class_dir.glob("*.npy"))
        if not npy_files:
            continue
        if class_dir.name not in label_to_id:
            raise ValueError(
                f"Class {class_dir.name!r} in {split_name} is missing from training data"
            )
        files.extend(npy_files)
        labels.extend([label_to_id[class_dir.name]] * len(npy_files))

    if not files:
        raise ValueError(f"No .npy sequence files found in {split_dir}")

    features = np.empty(
        (len(files), frame_count * POINT_SHAPE[0] * POINT_SHAPE[1]),
        dtype=np.float32,
    )
    for index, file_path in enumerate(files):
        sequence = np.load(file_path, allow_pickle=False)
        if sequence.ndim != 3 or sequence.shape[1:] != POINT_SHAPE:
            raise ValueError(
                f"{file_path} must have shape (frames, {POINT_SHAPE[0]}, "
                f"{POINT_SHAPE[1]}); received {sequence.shape}"
            )
        if len(sequence) == 0 or not np.isfinite(sequence).all():
            raise ValueError(f"{file_path} is empty or contains non-finite values")

        features[index] = resample_sequence(
            sequence.astype(np.float32, copy=False),
            frame_count,
        ).reshape(-1)

        if (index + 1) % 1000 == 0 or index + 1 == len(files):
            print(f"[{split_name}] Loaded {index + 1}/{len(files)} sequences")

    return features, np.asarray(labels, dtype=np.int64)


def main():
    parser = argparse.ArgumentParser(
        description="Train an isolated classifier for (frames, 76, 3) keypoint sequences."
    )
    parser.add_argument(
        "--train-dir",
        type=Path,
        default=ROOT_DIR / "processed" / "keypoints_splited" / "train",
    )
    parser.add_argument(
        "--test-dir",
        type=Path,
        default=ROOT_DIR / "processed" / "keypoints_splited" / "test",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT_DIR / "models" / "vsl_test1.pkl",
    )
    parser.add_argument("--frames", type=int, default=16)
    parser.add_argument("--max-iter", type=int, default=50)
    parser.add_argument("--jobs", type=int, default=-1)
    args = parser.parse_args()

    if args.frames < 1 or args.max_iter < 1 or args.jobs == 0:
        parser.error("--frames and --max-iter must be positive; --jobs cannot be 0")

    train_classes = sorted(
        path.name
        for path in args.train_dir.iterdir()
        if path.is_dir() and any(path.glob("*.npy"))
    ) if args.train_dir.is_dir() else []
    if len(train_classes) < 2:
        raise ValueError(
            f"Expected at least two classes with .npy files in {args.train_dir}"
        )

    label_to_id = {label: index for index, label in enumerate(train_classes)}
    id_to_label = {index: label for label, index in label_to_id.items()}
    print(
        f"Classes: {len(label_to_id)}; sequence input: "
        f"(variable frames, {POINT_SHAPE[0]}, {POINT_SHAPE[1]}); "
        f"resampled frames: {args.frames}"
    )

    started = time.perf_counter()
    X_train, y_train = load_split(
        args.train_dir,
        label_to_id,
        args.frames,
        "train",
    )
    X_test, y_test = load_split(
        args.test_dir,
        label_to_id,
        args.frames,
        "test",
    )
    print(
        f"Loaded train={len(y_train)}, test={len(y_test)} sequences "
        f"({time.perf_counter() - started:.1f}s)"
    )

    model = make_pipeline(
        StandardScaler(),
        SGDClassifier(
            loss="hinge",
            class_weight="balanced",
            max_iter=args.max_iter,
            tol=1e-3,
            n_jobs=args.jobs,
            random_state=42,
        ),
    )
    print(
        f"Training linear sequence classifier: "
        f"{X_train.shape[0]} samples x {X_train.shape[1]} features..."
    )
    fit_started = time.perf_counter()
    model.fit(X_train, y_train)
    print(f"Fit complete in {time.perf_counter() - fit_started:.1f}s")

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    macro_f1 = f1_score(
        y_test,
        predictions,
        labels=np.arange(len(label_to_id)),
        average="macro",
        zero_division=0,
    )
    print(
        f"Test metrics: accuracy={accuracy * 100:.2f}%, "
        f"macro F1={macro_f1:.3f}"
    )

    report = classification_report(
        y_test,
        predictions,
        labels=np.arange(len(label_to_id)),
        target_names=train_classes,
        zero_division=0,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report_path = args.output.with_name(f"{args.output.stem}_report.txt")
    report_path.write_text(report, encoding="utf-8")

    artifact = {
        "format": "signtalk-keypoint-sequence-linear-v1",
        "model": model,
        "id_to_label": id_to_label,
        "input_point_shape": POINT_SHAPE,
        "resampled_frame_count": args.frames,
        "test_accuracy": accuracy,
        "test_macro_f1": macro_f1,
    }
    with args.output.open("wb") as model_file:
        pickle.dump(artifact, model_file, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"Saved isolated model to {args.output}")
    print(f"Saved per-class test report to {report_path}")


if __name__ == "__main__":
    main()
