const video = document.getElementById("camera-video");
const canvas = document.getElementById("capture-canvas");
const startButton = document.getElementById("start-camera");
const stopButton = document.getElementById("stop-camera");
const placeholder = document.getElementById("camera-placeholder");
const cameraFooter = document.getElementById("camera-footer");
const livePill = document.getElementById("live-pill");
const toast = document.getElementById("toast");
const continueButton = document.getElementById("continue-scan");

let cameraStream = null;
let analysisTimer = null;
let isSendingFrame = false;
let toastTimer = null;
let scanPhase = "scanning";
let gestureStartedAt = 0;
let lastMotionAt = 0;
let lastHandAt = 0;
let previousLandmarks = null;
let gesturePredictions = [];
let gestureFrameCount = 0;

const MIN_GESTURE_MS = 1800;
const END_AFTER_STILL_MS = 1400;
const END_AFTER_HAND_LOST_MS = 900;
const MAX_GESTURE_MS = 10000;
const MOTION_THRESHOLD = 0.018;

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("visible");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("visible"), 4500);
}

function setDetectionStatus(result) {
  const status = document.getElementById("detection-status");
  if (scanPhase === "recording") {
    status.textContent = "Đang ghi nhận trọn động tác…";
    return;
  }
  if (scanPhase === "review") {
    status.textContent = "Động tác đã hoàn tất";
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
  gestureFrameCount = 0;
  continueButton.hidden = true;
  document.getElementById("camera-tip").innerHTML =
    "<span>✧</span> Đưa tay vào khung hình; SignTalk sẽ chờ bạn hoàn thành động tác.";
  document.getElementById("result-word").innerHTML =
    `Sẵn sàng<span class="result-period">.</span>`;
  document.getElementById("result-description").textContent =
    "Kết quả sẽ hiện sau khi bạn hoàn thành một động tác.";
  document.getElementById("analysis-status").innerHTML = "<i></i> Đang chờ động tác";
  document.getElementById("face-status").textContent = "—";
  document.getElementById("hands-status").textContent = "—";
  document.getElementById("live-pill").innerHTML = "<i></i> ĐANG QUÉT";
}

function finishGesture(message) {
  if (scanPhase !== "recording") return;
  scanPhase = "review";
  const counts = new Map();
  for (const label of gesturePredictions) {
    counts.set(label, (counts.get(label) || 0) + 1);
  }
  const winner = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
  const agreement = winner ? Math.round((winner[1] / gesturePredictions.length) * 100) : 0;

  if (winner) {
    document.getElementById("result-word").innerHTML =
      `${escapeHtml(winner[0])}<span class="result-period">.</span>`;
    document.getElementById("result-description").textContent =
      `Tổng hợp ${gestureFrameCount} khung hình · ${agreement}% khung hình đồng thuận`;
  } else {
    document.getElementById("result-word").innerHTML =
      `Chưa nhận diện<span class="result-period">.</span>`;
    document.getElementById("result-description").textContent =
      "Chưa đủ dữ liệu để nhận diện. Hãy đưa tay rõ hơn vào khung hình rồi thử lại.";
  }
  document.getElementById("analysis-status").textContent = "Động tác hoàn tất";
  document.getElementById("detection-status").textContent = "Động tác đã hoàn tất";
  document.getElementById("camera-tip").innerHTML =
    `<span>✧</span> ${message || "Kết quả đã tổng hợp từ toàn bộ động tác."}`;
  document.getElementById("live-pill").innerHTML = "<i></i> ĐÃ HOÀN TẤT";
  continueButton.hidden = false;
}

function consumeFrame(result) {
  const now = performance.now();
  document.getElementById("face-status").textContent =
    result.face_detected ? "Đã phát hiện" : "Chưa phát hiện";
  document.getElementById("hands-status").textContent =
    result.hands_detected ? "Đã phát hiện" : "Chưa phát hiện";

  if (scanPhase === "review") return;
  setDetectionStatus(result);

  if (result.hands_detected && result.label) {
    if (scanPhase === "scanning") {
      scanPhase = "recording";
      gestureStartedAt = now;
      lastMotionAt = now;
      document.getElementById("analysis-status").innerHTML = "<i></i> Đang ghi nhận động tác";
      document.getElementById("live-pill").innerHTML = "<i></i> ĐANG GHI NHẬN";
      document.getElementById("camera-tip").innerHTML =
        "<span>✧</span> Hãy thực hiện trọn ký hiệu; SignTalk sẽ tự tổng hợp khi động tác dừng.";
    }

    const motion = measureMotion(result.hand_landmarks, previousLandmarks);
    if (motion > MOTION_THRESHOLD) lastMotionAt = now;
    previousLandmarks = result.hand_landmarks;
    lastHandAt = now;
    gesturePredictions.push(result.display_label);
    gestureFrameCount += 1;
  } else if (scanPhase === "recording") {
    previousLandmarks = null;
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
    scanPhase === "review" ||
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
  continueButton.hidden = true;
  scanPhase = "scanning";
}

startButton.addEventListener("click", startCamera);
stopButton.addEventListener("click", stopCamera);
continueButton.addEventListener("click", () => {
  if (!cameraStream) return;
  resetGesture();
  analyzeFrame();
});
window.addEventListener("pagehide", stopCamera);
