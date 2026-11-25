const video = document.getElementById("camera-video");
const canvas = document.getElementById("capture-canvas");
const startButton = document.getElementById("start-camera");
const stopButton = document.getElementById("stop-camera");
const placeholder = document.getElementById("camera-placeholder");
const cameraFooter = document.getElementById("camera-footer");
const livePill = document.getElementById("live-pill");
const toast = document.getElementById("toast");
const speechToggle = document.getElementById("speech-toggle");
const speechSupported = "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
const audioPlaybackSupported = typeof Audio !== "undefined";
let speechEnabled = false;
let activeAudio = null;

let cameraStream = null;
let analysisTimer = null;
let isSendingFrame = false;
let toastTimer = null;
let missingVietnameseVoiceNotified = false;
let scanPhase = "scanning";
let gestureStartedAt = 0;
let lastMotionAt = 0;
let lastHandAt = 0;
let previousLandmarks = null;
let faceAnchor = null;
let faceStableSince = 0;
let gesturePredictions = [];
let gestureAudioUrls = new Map();
let gestureFrameCount = 0;
let spokenGestureLabel = null;

const MIN_GESTURE_MS = 1800;
const END_AFTER_STILL_MS = 1400;
const END_AFTER_HAND_LOST_MS = 900;
const MAX_GESTURE_MS = 10000;
const MOTION_THRESHOLD = 0.018;
const FACE_MOTION_THRESHOLD = 0.02;
const STILL_DETECTION_MS = 1800;

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("visible");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("visible"), 4500);
}

function updateSpeechToggle() {
  speechToggle.setAttribute("aria-pressed", String(speechEnabled));
  document.getElementById("speech-toggle-status").textContent =
    speechEnabled ? "Đang bật" : "Đang tắt";
}

function setSpeechEnabled(enabled, persist = true) {
  speechEnabled = enabled && (speechSupported || audioPlaybackSupported);
  updateSpeechToggle();
  if (persist) {
    try {
      localStorage.setItem(speechToggle.dataset.preferenceKey, String(speechEnabled));
    } catch (error) {
      showToast("Không thể lưu tùy chọn đọc trên trình duyệt này.");
    }
  }
  if (!speechEnabled) stopSpeechPlayback();
}

function stopSpeechPlayback() {
  if (speechSupported) window.speechSynthesis.cancel();
  if (activeAudio) {
    activeAudio.pause();
    activeAudio.currentTime = 0;
    activeAudio = null;
  }
}

function speakResult(word, audioUrl) {
  if (!speechEnabled) return;
  stopSpeechPlayback();
  if (audioUrl && audioPlaybackSupported) {
    const audio = new Audio(audioUrl);
    activeAudio = audio;
    const handleAudioError = () => {
      if (activeAudio !== audio) return;
      activeAudio = null;
      showToast("Không thể phát file âm thanh. Hãy kiểm tra kết nối và thiết bị âm thanh.");
    };
    audio.addEventListener("ended", () => {
      if (activeAudio === audio) activeAudio = null;
    }, { once: true });
    audio.addEventListener("error", handleAudioError, { once: true });
    const playback = audio.play();
    if (playback) playback.catch(handleAudioError);
    return;
  }
  if (!speechSupported) {
    showToast("Không có file âm thanh cho từ này và trình duyệt không hỗ trợ đọc văn bản.");
    return;
  }

  const speechText = word
    .normalize("NFC")
    .replace(/\p{Extended_Pictographic}/gu, "")
    .replace(/[\uFE0E\uFE0F\u200D]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  const utterance = new SpeechSynthesisUtterance(speechText);
  utterance.lang = "vi-VN";
  utterance.rate = 0.95;
  const voices = window.speechSynthesis.getVoices();
  const vietnameseVoice = voices.find(
    (voice) => voice.lang.toLowerCase() === "vi-vn",
  ) || voices.find(
    (voice) => /^vi(?:-|$)/i.test(voice.lang),
  );
  if (!vietnameseVoice) {
    if (!missingVietnameseVoiceNotified) {
      showToast("Chưa tìm thấy giọng tiếng Việt. Hãy cài giọng tiếng Việt cho Windows rồi khởi động lại Cốc Cốc.");
      missingVietnameseVoiceNotified = true;
    }
    return;
  }
  utterance.voice = vietnameseVoice;
  utterance.onerror = (event) => {
    if (event.error !== "canceled" && event.error !== "interrupted") {
      showToast("Không thể phát âm kết quả. Hãy kiểm tra thiết bị âm thanh của bạn.");
    }
  };
  window.speechSynthesis.speak(utterance);
}

function initializeSpeechToggle() {
  if (!speechSupported && !audioPlaybackSupported) {
    speechToggle.disabled = true;
    document.getElementById("speech-toggle-status").textContent = "Trình duyệt không hỗ trợ";
    return;
  }
  try {
    setSpeechEnabled(
      localStorage.getItem(speechToggle.dataset.preferenceKey) === "true",
      false,
    );
  } catch (error) {
    setSpeechEnabled(false, false);
    showToast("Không thể đọc tùy chọn đọc đã lưu trên trình duyệt này.");
  }
}

function setDetectionStatus(result) {
  const status = document.getElementById("detection-status");
  if (scanPhase === "recording") {
    status.textContent = "Đang nhận diện trực tiếp…";
    return;
  }
  if (result.hands_detected && result.face_detected) {
    status.textContent = "Đã nhận diện tay — hãy thực hiện ký hiệu";
  } else if (result.hands_detected) {
    status.textContent = "Đã nhận diện tay — hãy thực hiện ký hiệu";
  } else if (result.face_detected) {
    status.textContent = "Đang tìm bàn tay…";
  } else {
    status.textContent = "Đưa tay vào khung hình";
  }
}

function measureMotion(current, previous) {
  if (!previous || current.length !== previous.length) return Infinity;
  let total = 0;
  let count = 0;
  for (let index = 0; index < current.length; index += 2) {
    const currentPresent = Math.abs(current[index]) + Math.abs(current[index + 1]) > 1e-6;
    const previousPresent = Math.abs(previous[index]) + Math.abs(previous[index + 1]) > 1e-6;
    if (!currentPresent && !previousPresent) continue;
    if (currentPresent !== previousPresent) {
      total += 0.1;
    } else {
      total += Math.hypot(
        current[index] - previous[index],
        current[index + 1] - previous[index + 1],
      );
    }
    count += 1;
  }
  return count ? total / count : 0;
}

function resetGesture() {
  scanPhase = "scanning";
  gestureStartedAt = 0;
  lastMotionAt = 0;
  lastHandAt = 0;
  previousLandmarks = null;
  gesturePredictions = [];
  gestureAudioUrls = new Map();
  gestureFrameCount = 0;
  spokenGestureLabel = null;
  document.getElementById("camera-tip").innerHTML =
    "<span>✧</span> Đưa tay vào khung hình để xem kết quả nhận diện trực tiếp.";
  document.getElementById("result-word").innerHTML =
    `Sẵn sàng<span class="result-period">.</span>`;
  document.getElementById("result-description").textContent =
    "Kết quả sẽ cập nhật ngay khi SignTalk nhận diện được ký hiệu.";
  document.getElementById("analysis-status").innerHTML = "<i></i> Đang chờ ký hiệu";
  document.getElementById("face-status").textContent = "—";
  document.getElementById("hands-status").textContent = "—";
  document.getElementById("live-pill").innerHTML = "<i></i> ĐANG QUÉT";
}

function getWinningPrediction(predictions) {
  const counts = new Map();
  for (const label of predictions) {
    counts.set(label, (counts.get(label) || 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0] || null;
}

function getStableSpeechLabel(predictions) {
  const recent = predictions.slice(-4);
  if (recent.length < 3) return null;
  const winner = getWinningPrediction(recent);
  return winner && winner[1] >= Math.ceil(recent.length * 0.75)
    ? winner[0]
    : null;
}

function updatePersonStillness(result, now) {
  if (!result.face_detected || !result.face_center) {
    faceAnchor = null;
    faceStableSince = 0;
    document.getElementById("result-word").innerHTML =
      `Đang chờ<span class="result-period">.</span>`;
    document.getElementById("result-description").textContent =
      "Đưa khuôn mặt vào khung hình để theo dõi trạng thái.";
    document.getElementById("analysis-status").innerHTML = "<i></i> Đang chờ người";
    document.getElementById("detection-status").textContent = "Chưa phát hiện người";
    document.getElementById("live-pill").innerHTML = "<i></i> ĐANG QUÉT";
    return;
  }

  const currentCenter = result.face_center;
  if (!faceAnchor) {
    faceAnchor = currentCenter;
    faceStableSince = now;
  } else if (Math.hypot(
    currentCenter[0] - faceAnchor[0],
    currentCenter[1] - faceAnchor[1],
  ) > FACE_MOTION_THRESHOLD) {
    faceAnchor = currentCenter;
    faceStableSince = now;
  }

  if (now - faceStableSince >= STILL_DETECTION_MS) {
    document.getElementById("result-word").innerHTML =
      `Đứng yên<span class="result-period">.</span>`;
    document.getElementById("result-description").textContent =
      "Không phát hiện chuyển động rõ trong khung hình.";
    document.getElementById("analysis-status").innerHTML = "<i></i> Đứng yên";
    document.getElementById("detection-status").textContent = "Đứng yên";
    document.getElementById("camera-tip").innerHTML =
      "<span>✧</span> SignTalk đang theo dõi; kết quả sẽ đổi khi bạn di chuyển hoặc làm ký hiệu.";
    document.getElementById("live-pill").innerHTML = "<i></i> ĐỨNG YÊN";
    return;
  }

  document.getElementById("result-word").innerHTML =
    `Đang quan sát<span class="result-period">.</span>`;
  document.getElementById("result-description").textContent =
    "SignTalk đang theo dõi chuyển động của bạn.";
  document.getElementById("analysis-status").innerHTML = "<i></i> Đang theo dõi";
  document.getElementById("detection-status").textContent = "Đang theo dõi chuyển động";
  document.getElementById("live-pill").innerHTML = "<i></i> ĐANG QUÉT";
}

function finishGesture(message) {
  if (scanPhase !== "recording") return;
  scanPhase = "scanning";
  const winner = getWinningPrediction(gesturePredictions);
  const agreement = winner ? Math.round((winner[1] / gesturePredictions.length) * 100) : 0;

  if (winner) {
    document.getElementById("result-word").innerHTML =
      `${escapeHtml(winner[0])}<span class="result-period">.</span>`;
    document.getElementById("result-description").textContent =
      `Đã tổng hợp ${gestureFrameCount} khung hình · ${agreement}% khung hình đồng thuận`;
    if (winner[0] !== spokenGestureLabel) {
      speakResult(winner[0], gestureAudioUrls.get(winner[0]));
      spokenGestureLabel = winner[0];
    }
  } else {
    document.getElementById("result-word").innerHTML =
      `Chưa nhận diện<span class="result-period">.</span>`;
    document.getElementById("result-description").textContent =
      "Chưa đủ dữ liệu để nhận diện. Hãy đưa tay rõ hơn vào khung hình rồi thử lại.";
  }
  document.getElementById("analysis-status").innerHTML = "<i></i> Đang tiếp tục quét";
  document.getElementById("detection-status").textContent = "Đang chờ ký hiệu tiếp theo";
  document.getElementById("camera-tip").innerHTML =
    `<span>✧</span> ${message || "Kết quả đã tổng hợp; SignTalk đang tự động nhận diện ký hiệu tiếp theo."}`;
  document.getElementById("live-pill").innerHTML = "<i></i> ĐANG QUÉT";
}

function consumeFrame(result) {
  const now = performance.now();
  document.getElementById("face-status").textContent =
    result.face_detected ? "Đã phát hiện" : "Chưa phát hiện";
  document.getElementById("hands-status").textContent =
    result.hands_detected ? "Đã phát hiện" : "Chưa phát hiện";

  setDetectionStatus(result);

  if (result.hands_detected && result.label) {
    faceAnchor = null;
    faceStableSince = 0;
    if (scanPhase === "scanning") {
      scanPhase = "recording";
      gestureStartedAt = now;
      lastMotionAt = now;
      previousLandmarks = null;
      gesturePredictions = [];
      gestureAudioUrls = new Map();
      gestureFrameCount = 0;
      spokenGestureLabel = null;
      document.getElementById("analysis-status").innerHTML = "<i></i> Đang ghi nhận động tác";
      document.getElementById("live-pill").innerHTML = "<i></i> ĐANG GHI NHẬN";
      document.getElementById("camera-tip").innerHTML =
        "<span>✧</span> Kết quả ký hiệu đang được cập nhật theo thời gian thực.";
    }

    const motion = measureMotion(result.hand_landmarks, previousLandmarks);
    if (motion > MOTION_THRESHOLD) lastMotionAt = now;
    previousLandmarks = result.hand_landmarks;
    lastHandAt = now;
    gesturePredictions.push(result.display_label);
    if (result.audio_url) {
      gestureAudioUrls.set(result.display_label, result.audio_url);
    }
    gestureFrameCount += 1;
    const winner = getWinningPrediction(gesturePredictions);
    if (winner) {
      document.getElementById("result-word").innerHTML =
        `${escapeHtml(winner[0])}<span class="result-period">.</span>`;
      document.getElementById("result-description").textContent =
        `Đang nhận diện trực tiếp · ${gestureFrameCount} khung hình`;
    }
    const stableSpeechLabel = getStableSpeechLabel(gesturePredictions);
    if (stableSpeechLabel && stableSpeechLabel !== spokenGestureLabel) {
      speakResult(stableSpeechLabel, gestureAudioUrls.get(stableSpeechLabel));
      spokenGestureLabel = stableSpeechLabel;
    }
    document.getElementById("analysis-status").innerHTML = "<i></i> Đang nhận diện trực tiếp";
  } else if (scanPhase === "recording") {
    previousLandmarks = null;
  } else {
    updatePersonStillness(result, now);
  }

  if (scanPhase !== "recording") return;
  const elapsed = now - gestureStartedAt;
  const handMissingFor = now - lastHandAt;
  const stillFor = now - lastMotionAt;
  if (
    elapsed >= MAX_GESTURE_MS ||
    (elapsed >= MIN_GESTURE_MS &&
      (handMissingFor >= END_AFTER_HAND_LOST_MS || stillFor >= END_AFTER_STILL_MS))
  ) {
    finishGesture();
  }
}

async function analyzeFrame() {
  if (
    !cameraStream ||
    isSendingFrame ||
    video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA
  ) return;
  isSendingFrame = true;
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const context = canvas.getContext("2d", { alpha: false });
  context.setTransform(1, 0, 0, 1, 0, 0);
  context.drawImage(video, 0, 0, canvas.width, canvas.height);

  try {
    const frame = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.8));
    if (!frame) throw new Error("Không thể tạo ảnh từ camera.");
    const response = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "image/jpeg" },
      body: frame,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Không thể phân tích hình ảnh.");

    consumeFrame(result);
  } catch (error) {
    showToast(error.message || "Có lỗi khi kết nối đến máy chủ.");
    stopCamera();
  } finally {
    isSendingFrame = false;
  }
}

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = value;
  return element.innerHTML;
}

async function startCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    showToast("Trình duyệt không hỗ trợ camera. Hãy mở SignTalk bằng Chrome hoặc Edge.");
    return;
  }
  startButton.disabled = true;
  startButton.textContent = "Đang kết nối…";
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
    });
    video.srcObject = cameraStream;
    await video.play();
    placeholder.hidden = true;
    cameraFooter.hidden = false;
    startButton.hidden = true;
    stopButton.hidden = false;
    livePill.classList.add("is-live");
    livePill.innerHTML = "<i></i> ĐANG HOẠT ĐỘNG";
    resetGesture();
    analysisTimer = window.setInterval(analyzeFrame, 300);
    analyzeFrame();
  } catch (error) {
    startButton.disabled = false;
    startButton.innerHTML = "<span>▣</span> Bật camera";
    let message = "Không thể bật camera. Hãy kiểm tra quyền truy cập camera.";
    if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
      message = "Bạn chưa cấp quyền camera. Hãy cho phép truy cập camera trong trình duyệt.";
    } else if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
      message = "Không tìm thấy camera trên thiết bị này.";
    }
    showToast(message);
  }
}

function stopCamera() {
  if (analysisTimer) window.clearInterval(analysisTimer);
  analysisTimer = null;
  stopSpeechPlayback();
  if (cameraStream) cameraStream.getTracks().forEach((track) => track.stop());
  cameraStream = null;
  video.srcObject = null;
  placeholder.hidden = false;
  cameraFooter.hidden = true;
  startButton.hidden = false;
  startButton.disabled = false;
  startButton.innerHTML = "<span>▣</span> Bật camera";
  stopButton.hidden = true;
  livePill.classList.remove("is-live");
  livePill.innerHTML = "<i></i> CHỜ KẾT NỐI";
  document.getElementById("analysis-status").textContent = "Chưa bắt đầu";
  document.getElementById("face-status").textContent = "—";
  document.getElementById("hands-status").textContent = "—";
  scanPhase = "scanning";
}

startButton.addEventListener("click", startCamera);
stopButton.addEventListener("click", stopCamera);
speechToggle.addEventListener("click", () => setSpeechEnabled(!speechEnabled));
window.addEventListener("pagehide", stopCamera);
initializeSpeechToggle();
