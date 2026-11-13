#!/usr/bin/env python3
"""Automated system tests. Start the controller first, then run:

  sudo python3 tests/run_tests.py

Each test sends a 5 MB file from h1 to h2 (about 10 s at 500 packets/s)
and breaks links while it is moving.
"""
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "topology"))
from topo import make_net                       # noqa: E402
from mininet.log import setLogLevel             # noqa: E402

APP = os.path.join(ROOT, "app")


def path_in_use(net):
    """Return 'A' or 'B' from the s1 rule for 10.0.0.2."""
    flows = net["s1"].cmd("ovs-ofctl dump-flows s1")
    m = re.search(r'nw_dst=10\.0\.0\.2 actions=output:"?(?:s1-eth)?(\d+)', flows)
    return {"2": "A", "3": "B"}.get(m.group(1) if m else "", "?")


def transfer(net, events=()):
    """Send the file; run each (seconds, action) in events while it moves."""
    h1, h2 = net["h1"], net["h2"]
    h2.cmd("rm -f /tmp/copy.bin")
    h2.cmd("python3 %s/receiver.py --out /tmp/copy.bin > /tmp/rx.log 2>&1 &" % APP)
    time.sleep(0.5)
    h1.cmd("python3 %s/sender.py --dest 10.0.0.2 --file /tmp/big.bin "
           "--rate 500 > /tmp/tx.log 2>&1 &" % APP)
    start = time.time()
    seen = []
    for at, action in events:
        time.sleep(max(0, start + at - time.time()))
        seen.append(action(net))
    for _ in range(60):                         # wait up to 60 s
        if "COMPLETE" in open("/tmp/rx.log").read():
            break
        time.sleep(1)
    rx = open("/tmp/rx.log").read().strip().splitlines()
    same = h2.cmd("cmp -s /tmp/big.bin /tmp/copy.bin && echo SAME").strip()
    h1.cmd("pkill -f app/sender.py")
    h2.cmd("pkill -f app/receiver.py")
    return same == "SAME", (rx[-1] if rx else "(no output)"), seen


def down(a, b):
    def act(net):
        net.configLinkStatus(a, b, "down")
        time.sleep(0.5)
        return path_in_use(net)
    return act


def up(a, b):
    def act(net):
        net.configLinkStatus(a, b, "up")
        time.sleep(0.5)
        return path_in_use(net)
    return act


def main():
    setLogLevel("warning")
    net = make_net()
    time.sleep(3)                               # let the switches connect
    net["h1"].cmd("head -c 5M /dev/urandom > /tmp/big.bin")
    results = []

    def check(tc, name, ok, detail):
        results.append(ok)
        print("%-5s %-45s %s   %s" % (tc, name, "PASS" if ok else "FAIL", detail),
              flush=True)

    try:
        loss = net.ping([net["h1"], net["h2"]], timeout=1)
        check("TC-1", "h1 and h2 can reach each other", loss == 0,
              "ping loss %d%%" % loss)
        check("TC-2", "traffic starts on path A", path_in_use(net) == "A",
              "path " + path_in_use(net))

        ok, last, _ = transfer(net)
        check("TC-3", "file transfer with no failure", ok, last)

        ok, last, seen = transfer(net, [(3, down("s1", "s2")), (7, up("s1", "s2"))])
        check("TC-4", "cut s1-s2 during transfer: moves to B",
              seen[0] == "B", "path after cut: " + seen[0])
        check("TC-5", "link restored: moves back to A",
              seen[1] == "A", "path after repair: " + seen[1])
        check("TC-6", "file intact after cut and repair", ok, last)

        ok, last, seen = transfer(net, [(3, down("s2", "s4")), (7, up("s2", "s4"))])
        check("TC-7", "cut s2-s4 (far side of A): file intact",
              ok and seen[0] == "B", last)

        ok, last, seen = transfer(net, [(3, down("s1", "s2")), (3.1, down("s1", "s3")),
                                        (6, up("s1", "s3")), (8, up("s1", "s2"))])
        check("TC-8", "both paths down for 3 s: file intact", ok, last)
    finally:
        net.stop()

    print("\n%d of %d tests passed" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
