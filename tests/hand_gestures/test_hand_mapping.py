import time
import signal
import threading
import argparse
import io_libraries.camera.JetsonCamera
print(io_libraries.camera.JetsonCamera.__file__)
from io_libraries.camera.JetsonCamera import Camera
from io_libraries.camera.Focuser import Focuser
from io_libraries.camera.Autofocus import FocusState, doFocus
import cv2
from ultralytics import YOLO
import subprocess

subprocess.run(["sudo", "systemctl", "restart", "nvargus-daemon"], check=True)

import torch

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Using device:", device)


i2c_bus = 2
camera = Camera()
focuser = Focuser(i2c_bus)
focuser.verbose = False


focusState = FocusState()
focusState.verbose = False
doFocus(camera, focuser, focusState)

print("Done with the focus setup")

# Open the camera
# cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
print("Getting the handle")
cap = camera.get_cv2_handle()

if not cap.isOpened():
    print("❌ Error: Camera failed to open.")
    print("   Please verify the GStreamer pipeline and camera connection.")
    exit(1)

print("!!!!!!!!! the open cv side of this is done!!!!!""")

print("before loading model")
# Load YOLO pose model
model = YOLO("yolov8n-pose.pt")  # change to a bigger model for more accuracy
model.to(device)

print("📸 Starting live pose stream. Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ Frame grab failed — retrying...")
        continue

    # Run pose inference
    results = model(frame, verbose=False)

    # Annotate frame with keypoints + skeleton
    if len(results) > 0:
        annotated = results[0].plot()
    else:
        annotated = frame

    # Display live window
    cv2.imshow("Pose Live", annotated)

    # Quit on 'q' key
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()