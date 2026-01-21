#!/usr/bin/env python3
"""
Host-side camera streamer for Jetson (IMX519 / Argus).

Starts a GStreamer pipeline that:
- captures from nvarguscamerasrc
- encodes to H.264 (low latency)
- streams over UDP to localhost:5000

This script is meant to run on the Jetson host OS (not in Docker).
"""

import subprocess
import signal
import sys
import time


GST_PIPELINE = [
    "gst-launch-1.0",
    "-v",
    "nvarguscamerasrc", "sensor-id=0",
    "!",
    "video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1,format=NV12",
    "!",
    "nvvidconv",
    "!",
    "video/x-raw,format=I420",
    "!",
    "x264enc",
    "tune=zerolatency",
    "bitrate=2000",
    "speed-preset=ultrafast",
    "!",
    "rtph264pay",
    "config-interval=1",
    "pt=96",
    "!",
    "udpsink",
    "host=127.0.0.1",
    "port=5000",
]


def main():
    print("[host-camera] Starting camera UDP stream…")

    proc = subprocess.Popen(
        GST_PIPELINE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    def shutdown(signum, frame):
        print("\n[host-camera] Shutting down camera stream…")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Optional: monitor output so you know it's alive
    try:
        while True:
            line = proc.stderr.readline()
            if line:
                print("[gst]", line.strip())
            else:
                time.sleep(0.1)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
