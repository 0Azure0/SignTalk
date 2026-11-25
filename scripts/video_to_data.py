"""
Convert pre-recorded videos into training data for the existing
Sign-Language-Classification project.

Folder example:

videos/
├── Me/
│   ├── 01.mp4
│   ├── 02.mp4
│   └── 03.mp4
├── Thank_you/
│   ├── 01.mp4
│   └── 02.mp4
└── Yes/
    └── 01.mp4

Run:

python scripts/video_to_data.py --input "videos/Me" --pose_name="Me"

The generated file will be:

data/Me.npy
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np


# ============================================================
# FIX IMPORT PATH
# ============================================================

# Cho phép chạy:
# python scripts/video_to_data.py
#
# và vẫn import được:
# utils.feature_extraction

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORT FEATURE EXTRACTION
# ============================================================

from utils.feature_extraction import (
    FEATURE_COUNT,
    extract_features,
    extract_hand_result,
)
from config import HAND_DETECTION_CONFIDENCE, HAND_MODEL_COMPLEXITY


# ============================================================
# SUPPORTED VIDEO TYPES
# ============================================================

VIDEO_EXTENSIONS = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".webm",
    ".wmv",
}


# ============================================================
# GET VIDEO FILES
# ============================================================

def get_video_files(input_path: Path) -> list[Path]:
    """
    Lấy danh sách video từ:

    1. Một file video
    2. Một folder chứa nhiều video
    """

    # Trường hợp input là một file
    if input_path.is_file():

        if input_path.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError(
                f"File khong phai video duoc ho tro: {input_path}"
            )

        return [input_path]

    # Trường hợp input là folder
    if input_path.is_dir():

        files = [
            p
            for p in sorted(input_path.iterdir())
            if p.is_file()
            and p.suffix.lower() in VIDEO_EXTENSIONS
        ]

        return files

    raise FileNotFoundError(
        f"Khong tim thay file/folder: {input_path}"
    )


# ============================================================
# PROCESS ONE VIDEO
# ============================================================

def process_video(
    video_path: Path,
    face_mesh,
    hands,
    step: int,
    require_hand: bool = False,
) -> tuple[list[np.ndarray], int, int]:

    """
    Đọc một video và chuyển từng frame thành feature vector.

    Parameters
    ----------
    video_path:
        Đường dẫn video.

    face_mesh:
        MediaPipe Face Mesh.

    hands:
        MediaPipe Hands.

    step:
        Chỉ xử lý mỗi N frame.

        step = 1:
            xử lý tất cả frame.

        step = 2:
            xử lý 1 frame / 2 frame.

        step = 3:
            xử lý 1 frame / 3 frame.

    Returns
    -------
    features:
        Danh sách feature vector.

    total_frames:
        Tổng số frame đọc được từ video.

    skipped_frames:
        Số frame không thể tạo feature.
    """

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():

        print(
            f"  [LOI] Khong mo duoc video: {video_path}"
        )

        return [], 0, 0

    features = []

    total_frames = 0
    skipped_frames = 0

    while True:

        success, image = cap.read()

        if not success:
            break

        total_frames += 1

        # ====================================================
        # FRAME SAMPLING
        # ====================================================

        # Ví dụ step = 2:
        # frame 1 -> xử lý
        # frame 2 -> bỏ
        # frame 3 -> xử lý
        # frame 4 -> bỏ

        if (total_frames - 1) % step != 0:
            continue

        # ====================================================
        # BGR -> RGB
        # ====================================================

        image_rgb = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2RGB
        )

        image_rgb.flags.writeable = False

        # ====================================================
        # MEDIAPIPE
        # ====================================================

        face_results = face_mesh.process(
            image_rgb
        )

        hand_results = hands.process(
            image_rgb
        )

        if require_hand and not hand_results.multi_hand_landmarks:
            continue

        # ====================================================
        # EXTRACT FEATURES
        # ====================================================

        try:

            # ------------------------------------------------
            # CASE 1:
            # Có khuôn mặt
            # ------------------------------------------------

            if face_results.multi_face_landmarks:

                feature = extract_features(
                    mp.solutions.hands,
                    face_results,
                    hand_results,
                )

            # ------------------------------------------------
            # CASE 2:
            # Không có khuôn mặt
            #
            # feature_extraction.py hiện tại sẽ crash nếu
            # gọi extract_face_result() khi không có face.
            #
            # Vì vậy ta thay 2 face features bằng [0, 0].
            # ------------------------------------------------

            else:

                hand_features = extract_hand_result(
                    mp.solutions.hands,
                    hand_results,
                )

                feature = np.hstack(
                    (
                        np.zeros(
                            2,
                            dtype=np.float32
                        ),
                        hand_features,
                    )
                )

            # =================================================
            # CONVERT TO NUMPY
            # =================================================

            feature = np.asarray(
                feature,
                dtype=np.float32
            ).reshape(-1)

            # =================================================
            # CHECK FEATURE
            # =================================================

            if feature.size == 0:

                skipped_frames += 1
                continue

            features.append(feature)

        except Exception as e:

            skipped_frames += 1

            print(
                f"  [CANH BAO] "
                f"Bo qua frame {total_frames}: "
                f"{type(e).__name__}: {e}"
            )

    cap.release()

    return (
        features,
        total_frames,
        skipped_frames,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Convert videos into .npy training data."
        )
    )

    # --------------------------------------------------------
    # INPUT
    # --------------------------------------------------------

    parser.add_argument(
        "--input",
        required=True,
        help=(
            "Duong dan den 1 video "
            "hoac folder chua cac video."
        ),
    )

    # --------------------------------------------------------
    # POSE NAME
    # --------------------------------------------------------

    parser.add_argument(
        "--pose_name",
        required=True,
        help=(
            "Ten class. "
            "Vi du: Me, Hello, Thank_you, Dia_chi."
        ),
    )

    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    parser.add_argument(
        "--confidence",
        type=float,
        default=0.5,
        help=(
            "MediaPipe detection/tracking confidence. "
            "Mac dinh: 0.5"
        ),
    )

    # --------------------------------------------------------
    # FRAME STEP
    # --------------------------------------------------------

    parser.add_argument(
        "--step",
        type=int,
        default=2,
        help=(
            "Lay 1 frame moi moi N frame. "
            "Mac dinh: 2."
        ),
    )

    parser.add_argument(
        "--append",
        action="store_true",
        help="Append generated samples to an existing data/<pose_name>.npy file.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing data/<pose_name>.npy file.",
    )

    args = parser.parse_args()

    # ========================================================
    # VALIDATE
    # ========================================================

    if args.step < 1:

        raise ValueError(
            "--step phai >= 1"
        )

    if not 0.0 <= args.confidence <= 1.0:

        raise ValueError(
            "--confidence phai nam trong khoang 0.0 -> 1.0"
        )

    # ========================================================
    # INPUT PATH
    # ========================================================

    input_path = Path(args.input)

    video_files = get_video_files(
        input_path
    )

    if not video_files:
        raise FileNotFoundError(f"No supported videos found in {input_path}")

    # ========================================================
    # OUTPUT DIRECTORY
    # ========================================================

    output_dir = Path("data")

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        output_dir / f"{args.pose_name}.npy"
    )

    if args.append and args.overwrite:
        parser.error("--append and --overwrite cannot be used together")
    if output_path.exists() and not (args.append or args.overwrite):
        parser.error(
            f"{output_path} already exists; use --append to keep its samples "
            "or --overwrite to replace it"
        )

    # ========================================================
    # INFORMATION
    # ========================================================

    print("=" * 60)
    print("VIDEO -> TRAINING DATA")
    print("=" * 60)

    print(
        f"Input      : {input_path}"
    )

    print(
        f"Pose name  : {args.pose_name}"
    )

    print(
        f"Confidence : {args.confidence}"
    )

    print(
        f"Frame step : {args.step}"
    )

    print(
        f"So video   : {len(video_files)}"
    )

    print(
        f"Output     : {output_path}"
    )

    print("=" * 60)

    # ========================================================
    # MEDIAPIPE FACE MESH
    # ========================================================

    mp_face_mesh = mp.solutions.face_mesh

    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=args.confidence,
        min_tracking_confidence=args.confidence,
    )

    # ========================================================
    # MEDIAPIPE HANDS
    # ========================================================

    mp_hands = mp.solutions.hands

    hands = mp_hands.Hands(
        static_image_mode=True,
        max_num_hands=2,
        model_complexity=HAND_MODEL_COMPLEXITY,
        min_detection_confidence=HAND_DETECTION_CONFIDENCE,
        min_tracking_confidence=HAND_DETECTION_CONFIDENCE,
    )

    # ========================================================
    # ALL FEATURES
    # ========================================================

    all_features = []

    total_frames = 0
    total_skipped = 0

    # ========================================================
    # PROCESS VIDEOS
    # ========================================================

    try:

        for index, video_path in enumerate(
            video_files,
            start=1
        ):

            print(
                f"\n[{index}/{len(video_files)}] "
                f"{video_path.name}"
            )

            features, frames, skipped = process_video(
                video_path,
                face_mesh,
                hands,
                args.step,
                require_hand=True,
            )

            total_frames += frames
            total_skipped += skipped

            all_features.extend(
                features
            )

            print(
                f"  Frames doc      : {frames}"
            )

            print(
                f"  Samples tao ra  : {len(features)}"
            )

            print(
                f"  Frames bo qua   : {skipped}"
            )

    finally:

        face_mesh.close()
        hands.close()

    # ========================================================
    # CHECK RESULT
    # ========================================================

    if not all_features:
        raise ValueError(
            f"No hand samples were extracted from videos in {input_path}"
        )

    # ========================================================
    # CREATE NUMPY ARRAY
    # ========================================================

    X = np.asarray(
        all_features,
        dtype=np.float32
    )

    # ========================================================
    # CHECK FEATURE DIMENSION
    # ========================================================

    print("\nKiem tra du lieu...")

    print(
        f"Feature shape: {X.shape}"
    )

    # Project hiện tại sử dụng:
    #
    # Face:
    #   2 features
    #
    # Hands:
    #   21 landmarks x 2 coordinates
    #   x 2 hands
    #   = 84 features
    #
    # Tổng:
    #   2 + 84 = 86

    if X.ndim != 2:

        print(
            "[CANH BAO] "
            "Du lieu khong co dang 2 chieu."
        )

    if X.shape[1] != FEATURE_COUNT:
        raise ValueError(
            f"Expected {FEATURE_COUNT} features per sample, got {X.shape[1]}"
        )

    if args.append and output_path.exists():
        existing = np.load(output_path).astype(np.float32)
        if existing.ndim != 2 or existing.shape[1] != FEATURE_COUNT:
            raise ValueError(
                f"{output_path} must have shape (samples, {FEATURE_COUNT}) "
                "to append video features"
            )
        if not np.isfinite(existing).all():
            raise ValueError(f"{output_path} contains non-finite features")
        X = np.vstack((existing, X))

    # ========================================================
    # SAVE
    # ========================================================

    np.save(
        output_path,
        X
    )

    # ========================================================
    # RESULT
    # ========================================================

    print("\n" + "=" * 60)
    print("HOAN TAT")
    print("=" * 60)

    print(
        f"Class          : {args.pose_name}"
    )

    print(
        f"Feature shape  : {X.shape}"
    )

    print(
        f"Tong frames    : {total_frames}"
    )

    print(
        f"Tong samples   : {len(X)}"
    )

    print(
        f"Tong bo qua    : {total_skipped}"
    )

    print(
        f"Da luu         : {output_path}"
    )

    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()