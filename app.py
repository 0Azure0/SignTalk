from pathlib import Path
from threading import Lock

import cv2
import mediapipe as mp
import numpy as np
from flask import Flask, jsonify, render_template, request

from config import (
    HAND_DETECTION_CONFIDENCE,
    HAND_MODEL_COMPLEXITY,
    MODEL_CONFIDENCE,
    MODEL_NAME,
)
from utils.feature_extraction import extract_features, extract_hand_result
from utils.model import ASLClassificationModel
from utils.strings import ExpressionHandler


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

mp_face_mesh = mp.solutions.face_mesh
mp_hands = mp.solutions.hands
expression_handler = ExpressionHandler()
model = ASLClassificationModel.load_model(str(BASE_DIR / "models" / MODEL_NAME))
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=MODEL_CONFIDENCE,
    min_tracking_confidence=MODEL_CONFIDENCE,
)
hands = mp_hands.Hands(
    static_image_mode=True,
    max_num_hands=2,
    model_complexity=HAND_MODEL_COMPLEXITY,
    min_detection_confidence=HAND_DETECTION_CONFIDENCE,
    min_tracking_confidence=HAND_DETECTION_CONFIDENCE,
)
inference_lock = Lock()


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/predict")
def predict():
    image_bytes = request.get_data()
    if not image_bytes:
        return jsonify(error="Không nhận được hình ảnh từ camera."), 400

    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return jsonify(error="Ảnh gửi lên không hợp lệ."), 400

    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    try:
        with inference_lock:
            face_results = face_mesh.process(rgb_image)
            hand_results = hands.process(rgb_image)
            if not hand_results.multi_hand_landmarks:
                return jsonify(
                    label=None,
                    display_label="Đưa tay vào khung hình",
                    face_detected=bool(face_results.multi_face_landmarks),
                    hands_detected=False,
                    hand_landmarks=None,
                )
            hand_landmarks = extract_hand_result(mp_hands, hand_results)
            expression = model.predict(
                extract_features(mp_hands, face_results, hand_results)
            )
    except Exception:
        app.logger.exception("Lỗi khi xử lý khung hình camera")
        return jsonify(error="Không thể phân tích khung hình. Vui lòng thử lại."), 500

    return jsonify(
        label=expression,
        display_label=expression_handler.MAPPING.get(expression, str(expression)),
        face_detected=bool(face_results.multi_face_landmarks),
        hands_detected=bool(hand_results.multi_hand_landmarks),
        hand_landmarks=hand_landmarks.tolist(),
    )


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify(error="Ảnh camera vượt quá dung lượng cho phép."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
