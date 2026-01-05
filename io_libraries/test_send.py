import time
from communication import NetLink, NetLinkConfig

JETSON_HOST = "10.42.0.86"  # change to what works for you
link = NetLink(NetLinkConfig(
    udp_peer=(JETSON_HOST, 5005),
))

i = 0
while True:
    msg = f"hello-udp-{i}".encode()
    link.send_udp(msg)
    print("TX UDP:", msg)
    i += 1
    time.sleep(0.2)