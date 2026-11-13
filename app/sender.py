#!/usr/bin/env python3
"""Send a file over UDP and resend any chunk the receiver reports missing.

  python3 app/sender.py --dest 10.0.0.2 --file /tmp/big.bin --rate 500
"""
import argparse
import socket
import threading
import time

from protocol import DATA, END, NACK, DONE, CHUNK, PORT, pack, unpack, unpack_nack


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True)
    ap.add_argument("--file", required=True)
    ap.add_argument("--rate", type=int, default=500, help="packets per second")
    ap.add_argument("--timeout", type=float, default=30,
                    help="give up if the receiver is silent this long")
    a = ap.parse_args()

    data = open(a.file, "rb").read()
    chunks = [data[i:i + CHUNK] for i in range(0, len(data), CHUNK)]
    total = len(chunks)
    dest = (a.dest, PORT)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    done = threading.Event()
    stats = {"resent": 0}
    last_heard = [time.time()]

    def listen():
        # Handle NACKs from the receiver: resend the chunks it lists.
        while not done.is_set():
            packet, _ = sock.recvfrom(65535)
            kind, number, body = unpack(packet)
            last_heard[0] = time.time()
            if kind == NACK:
                for seq in unpack_nack(body, number):
                    if seq < total:
                        sock.sendto(pack(DATA, seq, chunks[seq]), dest)
                        stats["resent"] += 1
            elif kind == DONE:
                done.set()

    threading.Thread(target=listen, daemon=True).start()

    start = time.time()
    gap = 1.0 / a.rate
    for seq, chunk in enumerate(chunks):
        sock.sendto(pack(DATA, seq, chunk), dest)
        wait = start + (seq + 1) * gap - time.time()
        if wait > 0:
            time.sleep(wait)

    # Keep announcing the end until the receiver says it has everything.
    last_heard[0] = time.time()
    while not done.wait(0.3):
        sock.sendto(pack(END, total), dest)
        if time.time() - last_heard[0] > a.timeout:
            print("FAILED: receiver silent for %d s" % a.timeout, flush=True)
            return 1

    print("sent %d chunks in %.1f s, resent %d" %
          (total, time.time() - start, stats["resent"]), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
