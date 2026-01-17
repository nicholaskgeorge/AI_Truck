# System Dependencies (Jetson)

This project relies on system-provided OpenCV and GStreamer for camera access.

Install on Jetson with:

```bash
sudo apt update
sudo apt install -y \
  python3-opencv \
  gstreamer1.0-tools \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-ugly
