#!/usr/bin/env python3

import socket
import struct
import time

import numpy as np
import cv2
from flask import Flask, Response

import mediapipe as mp

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

# Create one global Hands object
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)
# =========================
# Network camera client
# =========================

class NetworkCamera:
    def __init__(self, host="127.0.0.1", port=6000):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"[docker] Connecting to host {host}:{port} ...")
        self.sock.connect((host, port))
        print("[docker] Connected to host camera stream.")

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf

    def read(self):
        # Read header: width, height, channels
        header = self._recv_exact(12)  # 3 * 4 bytes
        if header is None:
            return False, None

        w, h, c = struct.unpack("!III", header)
        num_bytes = w * h * c

        data = self._recv_exact(num_bytes)
        if data is None:
            return False, None

        arr = np.frombuffer(data, dtype=np.uint8)
        frame = arr.reshape((h, w, c))
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
    Run MediaPipe Hands on the frame and draw landmarks.
    """
    # Make sure the frame is writable (copy detaches from read-only buffer)
    frame = frame.copy()

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = hands.process(rgb)

    if res.multi_hand_landmarks:
        for hand_lms in res.multi_hand_landmarks:
            mp_draw.draw_landmarks(
                frame,
                hand_lms,
                mp_hands.HAND_CONNECTIONS,
            )

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