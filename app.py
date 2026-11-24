import os
import re
import secrets
import sqlite3
import unicodedata
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from threading import Lock

import cv2
import mediapipe as mp
import numpy as np
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

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
app.secret_key = os.environ.get("SIGNTALK_SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
if os.environ.get("VERCEL"):
    DATABASE_PATH = Path("/tmp") / "signtalk-users.sqlite3"
else:
    DATABASE_PATH = BASE_DIR / "data" / "users.sqlite3"
DATA_DIRECTORY = BASE_DIR / "data"
AUDIO_DIRECTORY = BASE_DIR / "audio"
VIDEO_SAMPLE_DIRECTORY = BASE_DIR / "Video_mau"
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".ogg", ".wav"}
VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".webm"}
DATA_EXTENSIONS = {".npy"}


def normalize_label(label):
    return unicodedata.normalize("NFC", label).casefold()


def normalize_catalog_label(label):
    decomposed = unicodedata.normalize("NFD", str(label))
    without_marks = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]", "", without_marks.casefold())


def count_vocabulary_files():
    if not DATA_DIRECTORY.is_dir():
        return 0
    return sum(
        1
        for path in DATA_DIRECTORY.iterdir()
        if (
            path.is_file()
            and path.suffix.lower() in DATA_EXTENSIONS
            and normalize_label(path.stem) != normalize_label("bình_thường")
        )
    )


AUDIO_FILES_BY_LABEL = {
    normalize_label(path.stem): path.name
    for path in AUDIO_DIRECTORY.iterdir()
    if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
} if AUDIO_DIRECTORY.is_dir() else {}


@contextmanager
def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def build_video_catalog():
    display_labels = {
        normalize_catalog_label(label): display_label
        for label, display_label in ExpressionHandler.MAPPING.items()
    }
    folders = {}
    if VIDEO_SAMPLE_DIRECTORY.is_dir():
        folders = {
            normalize_catalog_label(path.name): path
            for path in VIDEO_SAMPLE_DIRECTORY.iterdir()
            if path.is_dir()
        }

    vocabulary = {
        folder_key: folder.name
        for folder_key, folder in folders.items()
    }

    catalog = []
    for label_key, label in sorted(
        vocabulary.items(),
        key=lambda item: display_labels.get(item[0], item[1]).casefold(),
    ):
        folder = folders.get(label_key)
        videos = sorted(
            (
                path
                for path in folder.iterdir()
                if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
            ) if folder else [],
            key=lambda path: path.name.casefold(),
        )
        catalog.append(
            {
                "label": display_labels.get(
                    label_key,
                    label.replace("_", " "),
                ),
                "key": label.replace("_", " "),
                "videos": [
                    {
                        "url": url_for(
                            "sample_video",
                            filename=f"{folder.name}/{video.name}",
                        )
                    }
                    for video in videos
                ],
            }
        )
    return catalog


def initialize_database():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                comment TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS contributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount_vnd INTEGER NOT NULL CHECK (amount_vnd > 0),
                message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )


def csrf_token():
    token = session.get("_csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def validate_csrf_token():
    submitted_token = request.form.get("csrf_token", "")
    stored_token = session.get("_csrf_token", "")
    return bool(stored_token) and secrets.compare_digest(submitted_token, stored_token)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify(error="Vui lòng đăng nhập để tiếp tục."), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


initialize_database()

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
@login_required
def index():
    with get_db_connection() as connection:
        user = connection.execute(
            "SELECT id, username, display_name, created_at FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    return render_template(
        "index.html",
        user=user,
        csrf_token=csrf_token(),
        active_page="studio",
    )


@app.get("/guide")
@login_required
def guide():
    with get_db_connection() as connection:
        user = connection.execute(
            "SELECT id, username, display_name, created_at FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    video_catalog = build_video_catalog()
    available_video_count = sum(bool(item["videos"]) for item in video_catalog)
    vocabulary_count = count_vocabulary_files()
    return render_template(
        "guide.html",
        user=user,
        csrf_token=csrf_token(),
        active_page="guide",
        video_catalog=video_catalog,
        vocabulary_count=vocabulary_count,
        video_count=sum(len(item["videos"]) for item in video_catalog),
        available_video_count=available_video_count,
        pending_video_count=vocabulary_count - available_video_count,
    )


@app.route("/reviews", methods=["GET", "POST"])
@login_required
def reviews():
    if request.method == "POST":
        if not validate_csrf_token():
            flash("Phiên gửi đánh giá đã hết hạn. Vui lòng thử lại.", "error")
            return redirect(url_for("reviews"))

        try:
            rating = int(request.form.get("rating", ""))
        except ValueError:
            rating = 0
        comment = request.form.get("comment", "").strip()
        if not 1 <= rating <= 5:
            flash("Vui lòng chọn số sao từ 1 đến 5.", "error")
        elif not 3 <= len(comment) <= 1000:
            flash("Nhận xét cần dài từ 3 đến 1.000 ký tự.", "error")
        else:
            with get_db_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO reviews (user_id, rating, comment)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        rating = excluded.rating,
                        comment = excluded.comment,
                        created_at = CURRENT_TIMESTAMP
                    """,
                    (session["user_id"], rating, comment),
                )
            flash("Cảm ơn bạn đã gửi đánh giá!", "success")
            return redirect(url_for("reviews"))

    with get_db_connection() as connection:
        user = connection.execute(
            "SELECT id, username, display_name FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
        if user is None:
            session.clear()
            return redirect(url_for("login"))
        review_stats = connection.execute(
            "SELECT COUNT(*) AS count, AVG(rating) AS average FROM reviews"
        ).fetchone()
        review_list = connection.execute(
            """
            SELECT reviews.rating, reviews.comment, reviews.created_at,
                   users.display_name
            FROM reviews
            JOIN users ON users.id = reviews.user_id
            ORDER BY reviews.created_at DESC, reviews.id DESC
            """
        ).fetchall()
        own_review = connection.execute(
            "SELECT rating, comment FROM reviews WHERE user_id = ?",
            (user["id"],),
        ).fetchone()

    return render_template(
        "reviews.html",
        user=user,
        csrf_token=csrf_token(),
        active_page="reviews",
        review_count=review_stats["count"],
        average_rating=review_stats["average"] or 0,
        review_list=review_list,
        own_review=own_review,
    )


@app.route("/contribute", methods=["GET", "POST"])
@login_required
def contribute():
    if request.method == "POST":
        if not validate_csrf_token():
            flash("Phiên gửi đóng góp đã hết hạn. Vui lòng thử lại.", "error")
            return redirect(url_for("contribute"))

        try:
            amount = int(request.form.get("amount_vnd", ""))
        except ValueError:
            amount = 0
        message = request.form.get("message", "").strip()
        if not 0 < amount <= 9223372036854775807:
            flash("Số tiền phải lớn hơn 0 và nằm trong giới hạn cho phép.", "error")
        elif len(message) > 500:
            flash("Lời nhắn không được vượt quá 500 ký tự.", "error")
        else:
            with get_db_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO contributions (user_id, amount_vnd, message)
                    VALUES (?, ?, ?)
                    """,
                    (session["user_id"], amount, message),
                )
            flash(
                "Đã ghi nhận mức đóng góp dự kiến. Đây chưa phải giao dịch thanh toán.",
                "success",
            )
            return redirect(url_for("contribute"))

    with get_db_connection() as connection:
        user = connection.execute(
            "SELECT id, username, display_name FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
        if user is None:
            session.clear()
            return redirect(url_for("login"))
        contribution_stats = connection.execute(
            """
            SELECT COUNT(*) AS count, COALESCE(SUM(amount_vnd), 0) AS total
            FROM contributions
            """
        ).fetchone()

    return render_template(
        "contribute.html",
        user=user,
        csrf_token=csrf_token(),
        active_page="contribute",
        contribution_count=contribution_stats["count"],
        contribution_total=contribution_stats["total"],
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))
    if request.method == "POST":
        if not validate_csrf_token():
            flash("Phiên đăng nhập đã hết hạn. Vui lòng thử lại.", "error")
            return redirect(url_for("login"))
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with get_db_connection() as connection:
            user = connection.execute(
                "SELECT id, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Tên đăng nhập hoặc mật khẩu không chính xác.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("index"))
    return render_template("auth.html", mode="login", csrf_token=csrf_token())


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("index"))
    if request.method == "POST":
        if not validate_csrf_token():
            flash("Phiên đăng ký đã hết hạn. Vui lòng thử lại.", "error")
            return redirect(url_for("register"))
        username = request.form.get("username", "").strip()
        display_name = request.form.get("display_name", "").strip()
        password = request.form.get("password", "")

        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
            flash("Tên đăng nhập cần dài 3–32 ký tự, chỉ gồm chữ không dấu, số, dấu chấm, gạch ngang hoặc gạch dưới.", "error")
        elif not 2 <= len(display_name) <= 60:
            flash("Tên hiển thị cần dài từ 2 đến 60 ký tự.", "error")
        elif not 8 <= len(password) <= 128:
            flash("Mật khẩu cần dài từ 8 đến 128 ký tự.", "error")
        else:
            try:
                with get_db_connection() as connection:
                    cursor = connection.execute(
                        """
                        INSERT INTO users (username, display_name, password_hash)
                        VALUES (?, ?, ?)
                        """,
                        (username, display_name, generate_password_hash(password)),
                    )
                session.clear()
                session["user_id"] = cursor.lastrowid
                return redirect(url_for("index"))
            except sqlite3.IntegrityError:
                flash("Tên đăng nhập này đã được sử dụng.", "error")
    return render_template("auth.html", mode="register", csrf_token=csrf_token())


@app.post("/logout")
@login_required
def logout():
    if not validate_csrf_token():
        flash("Không thể đăng xuất do phiên không hợp lệ. Vui lòng thử lại.", "error")
        return redirect(url_for("index"))
    session.clear()
    return redirect(url_for("login"))


@app.get("/audio/<path:filename>")
@login_required
def audio_file(filename):
    return send_from_directory(AUDIO_DIRECTORY, filename, conditional=True)


@app.get("/sample-videos/<path:filename>")
@login_required
def sample_video(filename):
    return send_from_directory(VIDEO_SAMPLE_DIRECTORY, filename, conditional=True)


@app.post("/api/predict")
@login_required
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
            face_detected = bool(face_results.multi_face_landmarks)
            face_center = None
            if face_detected:
                face_center = np.mean(
                    [
                        [landmark.x, landmark.y]
                        for landmark in face_results.multi_face_landmarks[0].landmark
                    ],
                    axis=0,
                ).tolist()
            if not hand_results.multi_hand_landmarks:
                return jsonify(
                    label=None,
                    display_label="Đưa tay vào khung hình",
                    face_detected=face_detected,
                    face_center=face_center,
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
        audio_url=(
            url_for(
                "audio_file",
                filename=AUDIO_FILES_BY_LABEL[normalize_label(str(expression))],
            )
            if normalize_label(str(expression)) in AUDIO_FILES_BY_LABEL
            else None
        ),
        face_detected=face_detected,
        face_center=face_center,
        hands_detected=bool(hand_results.multi_hand_landmarks),
        hand_landmarks=hand_landmarks.tolist(),
    )


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify(error="Ảnh camera vượt quá dung lượng cho phép."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
