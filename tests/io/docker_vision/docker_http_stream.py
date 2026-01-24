#!/usr/bin/env python3

import socket
import struct
import time

import numpy as np
import cv2
from flask import Flask, Response

# =========================
# Network camera client
# =========================

class NetworkCamera:
    """
    Connects to the host TCP server and exposes a VideoCapture-like API:
      read() -> (ret, frame)
    Protocol: [4-byte length][JPEG bytes] per frame.
    """

    def __init__(self, host="127.0.0.1", port=6000):
        # With --net=host, 127.0.0.1 in the container reaches the host server.
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"[docker] Connecting to host {host}:{port} ...")
        self.sock.connect((host, port))
        print("[docker] Connected to host camera stream.")

    def _recv_exact(self, n: int):
        """Receive exactly n bytes or return None if connection is lost."""
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf

    def read(self):
        """
        Returns (ret, frame) similar to cv2.VideoCapture.read().
        """
        # Read 4-byte length header
        header = self._recv_exact(4)
        if header is None:
            return False, None

        (length,) = struct.unpack("!I", header)
        data = self._recv_exact(length)
        if data is None:
            return False, None

        # Decode JPEG to numpy array
        arr = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return False, None

        return True, frame

    def release(self):
        self.sock.close()


# =========================
# Processing + HTTP server
# =========================

app = Flask(__name__)

# Create a single global camera client
# With --net=host, the host server is reachable via 127.0.0.1:6000
cam = NetworkCamera(host="127.0.0.1", port=6000)


def process_frame(frame):
    """
    Place for your image processing.

    Right now this just draws:
      - a green rectangle in the center
      - FPS text
    You can replace this with MediaPipe / gesture logic later.
    """
    h, w = frame.shape[:2]
    cx, cy = w // 2, h // 2
    size = min(h, w) // 8
    cv2.rectangle(frame, (cx - size, cy - size), (cx + size, cy + size), (0, 255, 0), 2)
    return frame


def gen_frames():
    """
    Generator that pulls frames from NetworkCamera,
    runs processing, and yields MJPEG chunks for HTTP.
    """
    last_time = time.time()
    frames = 0

    while True:
        ret, frame = cam.read()
        if not ret or frame is None:
            # If host stopped or connection dropped, break
            print("[docker] No frame received, stopping generator.")
            break

        frames += 1
        now = time.time()
        if now - last_time >= 1.0:
            print(f"[docker] FPS ~ {frames}")
            frames = 0
            last_time = now

        # Process the frame (draw landmarks, etc.)
        frame = process_frame(frame)

        # Encode to JPEG for MJPEG stream
        ok, jpeg = cv2.imencode(".jpg", frame)
        if not ok:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
        )


@app.route("/stream")
def stream():
    return Response(
        gen_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/")
def index():
    # Simple HTML page showing the stream
    return (
        "<html><body>"
        "<h1>Docker Camera Stream</h1>"
        '<img src="/stream" />'
        "</body></html>"
    )


if __name__ == "__main__":
    # Run HTTP server on port 5001
    # Accessible as http://JETSON_IP:5001/ or http://localhost:5001/ when on the Jetson
    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)