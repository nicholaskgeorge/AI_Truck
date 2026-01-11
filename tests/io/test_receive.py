from communication import NetLink, NetLinkConfig

link = NetLink(NetLinkConfig(
    udp_bind=("0.0.0.0", 5005),
))

print("UDP receiver listening on 0.0.0.0:5005")
while True:
    pkt = link.recv_udp()
    if pkt is None:
        continue
    data, addr = pkt
    print(f"RX UDP {len(data)} bytes from {addr}: {data!r}")