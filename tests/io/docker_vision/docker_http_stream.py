# docker_http_stream.py
#
# 1. Receives H.264 RTP over UDP from host (port 5000)
# 2. Decodes via GStreamer into OpenCV frames
# 3. Runs a processing step on each frame (placeholder; plug MediaPipe here)
# 4. Streams the processed frames over HTTP (MJPEG) at /stream

from flask import Flask, Response
import cv2
import time

app = Flask(__name__)

# GStreamer pipeline for receiving the UDP RTP/H264 stream
GSTREAMER_UDP_PIPELINE = (
    "udpsrc port=5000 caps=application/x-rtp,media=video,encoding-name=H264,payload=96 ! "
    "rtph264depay ! avdec_h264 ! videoconvert ! appsink"
)

# Open the GStreamer pipeline via OpenCV
cap = cv2.VideoCapture(GSTREAMER_UDP_PIPELINE, cv2.CAP_GSTREAMER)
print("isOpened:", cap.isOpened())
if not cap.isOpened():
    raise RuntimeError("Failed to open GStreamer pipeline from UDP. "
                       "Check that the host gst-launch sender is running.")

def process_frame(frame):
    """
    Placeholder for your processing.

    This is where you will plug:
      - MediaPipe Hands
      - custom OpenCV drawing / overlays
      - gesture recognition, etc.

    For now, we just overlay FPS and a simple rectangle so you can see it's working.
    """
    # Example: draw a rectangle at the center
    h, w = frame.shape[:2]
    cx, cy = w // 2, h // 2
    size = min(h, w) // 8
    cv2.rectangle(frame, (cx - size, cy - size), (cx + size, cy + size), (0, 255, 0), 2)
    return frame

def gen_frames():
    """
    Generator that yields JPEG-encoded frames for MJPEG streaming.
    """
    last_time = time.time()
    frames = 0

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            # If no frame, just retry after a short sleep
            time.sleep(0.01)
            continue

        frames += 1
        now = time.time()
        if now - last_time >= 1.0:
            print(f"frames/sec ~ {frames}")
            frames = 0
            last_time = now

        # Run your processing step here
        frame = process_frame(frame)

        # Encode as JPEG
        ret_jpeg, jpeg = cv2.imencode(".jpg", frame)
        if not ret_jpeg:
            continue

        # Yield in MJPEG multipart format
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
        )

@app.route("/stream")
def stream():
    # HTTP endpoint for the MJPEG stream
    return Response(
        gen_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

if __name__ == "__main__":
    # Listen on all interfaces so you can access from your laptop:
    #   http://JETSON_IP:5001/stream
    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)
