#!/usr/bin/env python3
"""Receive a file over UDP, ask for missing chunks, write the file when complete.

  python3 app/receiver.py --out /tmp/copy.bin
"""
import argparse
import socket
import time

from protocol import DATA, END, DONE, PORT, pack, unpack, pack_nack

NACK_EVERY = 0.2      # seconds between checks for missing chunks
MAX_PER_NACK = 300    # sequence numbers per NACK packet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=float, default=60,
                    help="give up if nothing arrives for this long")
    a = ap.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))
    sock.settimeout(NACK_EVERY)

    got = {}              # seq -> chunk
    asked = set()         # seqs we have NACKed at least once
    total = None          # known once END arrives
    highest = -1
    sender = None
    dups = 0
    last_packet = time.time()
    last_check = time.time()
    print("waiting on UDP port %d" % PORT, flush=True)

    while True:
        try:
            packet, sender = sock.recvfrom(65535)
            last_packet = time.time()
            kind, number, body = unpack(packet)
            if kind == DATA:
                if number in got:
                    dups += 1
                else:
                    got[number] = body
                    highest = max(highest, number)
            elif kind == END:
                total = number
        except socket.timeout:
            if time.time() - last_packet > a.timeout:
                print("FAILED: nothing received for %d s" % a.timeout, flush=True)
                return 1

        if total is not None and len(got) == total:
            break

        # Every NACK_EVERY seconds, ask for the gaps we can see.
        if sender and time.time() - last_check >= NACK_EVERY:
            last_check = time.time()
            end = total if total is not None else highest
            missing = [s for s in range(end) if s not in got][:MAX_PER_NACK]
            if missing:
                asked.update(missing)
                sock.sendto(pack_nack(missing), sender)
                print("missing %d chunks, NACK sent" % len(missing), flush=True)

    with open(a.out, "wb") as f:
        for seq in range(total):
            f.write(got[seq])
    for _ in range(3):
        sock.sendto(pack(DONE, 0), sender)
    print("COMPLETE: %d chunks, %d were lost and recovered, %d duplicates"
          % (total, len(asked), dups), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
