import { useEffect, useRef, useState } from "react";
import Icon from "../components/Icon";
import { verifyCameraCapture } from "../api";

const DISCLAIMER =
  "This prototype verifies face presence for demonstration only and does not connect to live INEC, BVAS, or NIMC systems.";

function frameHasVisualData(context, width, height) {
  const { data } = context.getImageData(0, 0, width, height);
  let total = 0;
  let totalSquared = 0;
  let samples = 0;

  for (let index = 0; index < data.length; index += 64) {
    const brightness = (data[index] + data[index + 1] + data[index + 2]) / 3;
    total += brightness;
    totalSquared += brightness * brightness;
    samples += 1;
  }

  const mean = total / samples;
  const variance = totalSquared / samples - mean * mean;
  return mean > 8 && variance > 20;
}

export default function BiometricVerification({ session, onEndSession, onVerified }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const [cameraState, setCameraState] = useState("idle");
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState("");
  const [capturedImage, setCapturedImage] = useState("");
  const [detectionMode, setDetectionMode] = useState("");

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function openCamera() {
    setError("");
    setCameraState("requesting");

    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraState("error");
      setError("Camera access is not supported in this browser. Use a modern browser on HTTPS or localhost.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 960 }, height: { ideal: 720 } },
        audio: false
      });
      streamRef.current = stream;
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
      setCameraState("live");
    } catch {
      setCameraState("error");
      setError("Camera permission is required to continue prototype face verification.");
    }
  }

  async function scanFace() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < 2) {
      setError("The camera is still preparing. Wait a moment and scan again.");
      return;
    }

    setIsBusy(true);
    setError("");

    try {
      const width = 480;
      const sourceRatio = video.videoWidth && video.videoHeight ? video.videoHeight / video.videoWidth : 0.75;
      const height = Math.round(width * sourceRatio);
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d", { willReadFrequently: true });
      context.drawImage(video, 0, 0, width, height);

      if (!frameHasVisualData(context, width, height)) {
        throw new Error("The captured frame is too dark or blank. Improve the lighting and scan again.");
      }

      let mode = "camera-frame-capture-fallback";
      if ("FaceDetector" in window) {
        try {
          const detector = new window.FaceDetector({ fastMode: true, maxDetectedFaces: 1 });
          const faces = await detector.detect(canvas);
          if (faces.length === 0) {
            throw new Error("No face-like structure was detected. Centre your face in the guide and scan again.");
          }
          mode = "native-face-detector";
        } catch (detectionError) {
          if (detectionError.message?.startsWith("No face-like")) {
            throw detectionError;
          }
          mode = "camera-frame-capture-fallback";
        }
      }

      const image = canvas.toDataURL("image/jpeg", 0.78);
      await verifyCameraCapture(session.token, mode);
      setCapturedImage(image);
      setDetectionMode(mode);
      setCameraState("verified");
      streamRef.current?.getTracks().forEach((track) => track.stop());
    } catch (scanError) {
      setError(scanError.message || "Camera-based prototype verification failed.");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="page camera-page">
      <div className="camera-intro">
        <span className="section-kicker section-kicker--light">Step 2 of 3</span>
        <h1>Camera-based prototype face verification</h1>
        <p>
          Allow camera access, centre your face inside the guide, and capture one frame
          to confirm face presence for this active session.
        </p>
        <div className="camera-profile">
          <span><Icon name="user" size={22} /></span>
          <div>
            <strong>{session?.profile?.displayName || "Eligible voter"}</strong>
            <small>{session?.profile?.voterCategory || "Eligible Diaspora Voter"}</small>
          </div>
        </div>
        <div className="camera-disclaimer">
          <Icon name="shield" size={20} />
          <span>{DISCLAIMER}</span>
        </div>
        <div className="active-session-notice">
          <strong>An accredited voter session is already active.</strong>
          <span>End the current session before accrediting another voter.</span>
          <button className="button button--light button--small" type="button" onClick={onEndSession}>
            <Icon name="logout" size={16} />
            End Session
          </button>
        </div>
      </div>

      <div className="camera-workspace">
        <div className={`camera-preview camera-preview--${cameraState}`}>
          {capturedImage ? (
            <img src={capturedImage} alt="Captured session profile" />
          ) : (
            <video ref={videoRef} playsInline muted />
          )}
          <canvas ref={canvasRef} hidden />
          <span className="camera-guide">
            <i />
            <i />
            <i />
            <i />
          </span>
          {cameraState === "idle" || cameraState === "requesting" || cameraState === "error" ? (
            <div className="camera-placeholder">
              <span><Icon name="camera" size={34} /></span>
              <strong>{cameraState === "requesting" ? "Requesting camera access..." : "Camera is off"}</strong>
              <small>Your captured frame stays in this browser session.</small>
            </div>
          ) : null}
          {cameraState === "live" ? <span className="camera-live"><i /> Camera live</span> : null}
          {cameraState === "verified" ? (
            <span className="camera-verified"><Icon name="check" size={16} /> Face presence verified</span>
          ) : null}
        </div>

        <div className="camera-status-panel">
          <div className="camera-status-copy">
            <span className="section-kicker">Verification status</span>
            <h2>
              {cameraState === "verified"
                ? "Session profile captured"
                : cameraState === "live"
                  ? "Position your face in the guide"
                  : "Open your camera to begin"}
            </h2>
            <p>
              {detectionMode === "native-face-detector"
                ? "This browser provided native face-presence detection."
                : "If native face detection is unavailable, the development fallback validates and captures a live camera frame."}
            </p>
          </div>

          <div className="confirmation-list camera-checklist">
            <div><Icon name="check" size={18} /><span>Camera permission required</span></div>
            <div><Icon name="check" size={18} /><span>No frame sent to the backend</span></div>
            <div><Icon name="check" size={18} /><span>Session-only profile image</span></div>
          </div>

          {error ? <div className="status status--error"><strong>Camera verification</strong><span>{error}</span></div> : null}

          {cameraState === "idle" || cameraState === "error" ? (
            <button className="button button--primary button--wide" type="button" onClick={openCamera}>
              <Icon name="camera" size={18} />
              Open Camera
            </button>
          ) : null}
          {cameraState === "live" ? (
            <button className="button button--primary button--wide" type="button" onClick={scanFace} disabled={isBusy}>
              {isBusy ? <span className="spinner spinner--small" /> : <Icon name="camera" size={18} />}
              {isBusy ? "Scanning Face..." : "Scan Face"}
            </button>
          ) : null}
          {cameraState === "verified" ? (
            <button
              className="button button--primary button--wide"
              type="button"
              onClick={() => onVerified({ capturedImage, detectionMode })}
            >
              Continue to Dashboard
              <Icon name="arrow" size={18} />
            </button>
          ) : null}
          <button className="text-button camera-end-session" type="button" onClick={onEndSession}>
            End Session
          </button>
        </div>
      </div>
    </section>
  );
}
