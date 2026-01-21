import cv2
import time

gst = (
    "udpsrc port=5000 caps=application/x-rtp,media=video,encoding-name=H264,payload=96 ! "
    "rtph264depay ! avdec_h264 ! videoconvert ! appsink"
)

cap = cv2.VideoCapture(gst, cv2.CAP_GSTREAMER)

print("isOpened:", cap.isOpened())
if not cap.isOpened():
    raise RuntimeError("Failed to open GStreamer pipeline from UDP. Check that the host sender is running.")

last_print = time.time()
frames = 0

while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        print("no frame")
        time.sleep(0.1)
        continue

    

    frames += 1
    now = time.time()
    if now - last_print >= 1.0:
        print(f"frames/sec ~ {frames}")
        frames = 0
        last_print = now
