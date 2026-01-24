import time
import signal
import cv2
import threading
import argparse
from io_libraries.camera.JetsonCamera import Camera
from io_libraries.camera.Focuser import Focuser
from io_libraries.camera.Autofocus import FocusState, doFocus
import socket
import struct

exit_ = False
def sigint_handler(signum, frame):
    global exit_
    exit_ = True

signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)


def start_server(host="0.0.0.0", port=6000):
    """
    Simple TCP server that accepts a single client (the Docker container)
    and yields a connected socket.
    """
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(1)
    print(f"[host] Waiting for Docker client on {host}:{port} ...")
    conn, addr = srv.accept()
    print(f"[host] Client connected from {addr}")
    return conn

def send_frame(conn, frame):
    """
    JPEG-encode and send a single frame over TCP as:
      [4 bytes length in network order][JPEG bytes]
    """
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        return
    data = buf.tobytes()
    length = len(data)
    header = struct.pack("!I", length)  # 4-byte unsigned int, network byte order
    conn.sendall(header + data)

if __name__ == "__main__":
    i2c_bus = 2
    camera = Camera()
    focuser = Focuser(i2c_bus)
    focuser.verbose = False

    focusState = FocusState()
    focusState.verbose = False
    doFocus(camera, focuser, focusState)

    start = time.time()
    frame_count = 0

    conn = start_server(host="0.0.0.0", port=6000)

    while not exit_:
        frame = camera.getFrame(2000)

        cv2.imshow("Test", frame)
        key = cv2.waitKey(1)
        if key == ord('q'):
            exit_ = True
        if key == ord('f'):
            if focusState.isFinish():
                focusState.reset()
                doFocus(camera, focuser, focusState)
            else:
                print("Focus is not done yet.")

        send_frame(conn, frame)

        frame_count += 1
        if time.time() - start >= 1:
            print("{}fps".format(frame_count))
            start = time.time()
            frame_count = 0

    camera.close()