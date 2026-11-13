# Adaptive communication network with failure recovery (UDP)

Computer Networks mini project 1, Team 1, PES University.

Team: Tanay Shah, Vanshika Kakumanu, Thushara Lakshmi N, Siddharth Kancharla
Guide: Prof. CVSN Reddy

A file is sent over UDP across a Mininet network that has two paths. When a link on the main path breaks, the POX controller moves traffic to the backup path. Packets lost during the break are requested again by the receiver and resent by the sender, so the file still arrives complete and unchanged.

```
        +---- s2 ----+          path A (main)
  h1 -- s1           s4 -- h2
        +---- s3 ----+          path B (backup)
```

Two layers of recovery work together:
- **Network layer (controller):** detects a link failure from the switch's port-down event and rewrites the rules on s1 and s4 to use path B. It moves traffic back to path A when the link is repaired.
- **Application layer (sender and receiver):** every chunk is numbered; the receiver sends a NACK listing missing chunks every 0.2 s, and the sender resends them.

## Files

| File | What it does |
|---|---|
| `topology/topo.py` | Builds the network in Mininet (2 hosts, 4 switches, 2 paths) |
| `controller/adaptive.py` | POX controller: installs rules, switches path when a link goes down or comes back |
| `controller/run.sh` | Starts POX with the controller |
| `app/protocol.py` | Packet format shared by sender and receiver (DATA, END, NACK, DONE) |
| `app/sender.py` | Sends a file over UDP, resends chunks the receiver asks for |
| `app/receiver.py` | Receives the file, asks for missing chunks, writes the file when complete |
| `tests/run_tests.py` | Automated system tests TC-1 to TC-8 |
| `docs/SRS.pdf` | Software requirements specification (IEEE / Wiegers template) |
| `docs/TEST_PLAN.pdf` | IEEE 829 test plan, test cases, results and evidence |

## Requirements

- Ubuntu 22.04 or 24.04 (a virtual machine with 2 CPUs and 4 GB RAM is enough)
- Mininet 2.3, Open vSwitch, Python 3
- POX 0.7.0 (branch gar-experimental). POX supports OpenFlow 1.0 only, so the project uses OpenFlow 1.0.

## Setup (once)

```
sudo apt update
sudo apt install -y mininet openvswitch-switch git
git clone https://github.com/noxrepo/pox ~/pox
git clone https://github.com/<your-username>/adaptive-network.git
cd adaptive-network
chmod +x controller/run.sh
```

## Run the automated tests

Terminal 1, the controller (leave it running):
```
cd adaptive-network
./controller/run.sh
```

Terminal 2:
```
cd adaptive-network
sudo python3 tests/run_tests.py
```
It takes about 1.5 minutes and ends with `8 of 8 tests passed`. If Mininet crashed earlier, run `sudo mn -c` first, and restart the controller before each new run.

## Run the demo by hand

With the controller running in terminal 1, start the network in terminal 2:
```
sudo python3 topology/topo.py
```

At the `mininet>` prompt:
```
pingall
sh ovs-ofctl dump-flows s1
h1 head -c 20M /dev/urandom > /tmp/big.bin
h2 python3 app/receiver.py --out /tmp/copy.bin > /tmp/rx.log &
h1 python3 app/sender.py --dest 10.0.0.2 --file /tmp/big.bin --rate 500 &
link s1 s2 down
sh ovs-ofctl dump-flows s1
link s1 s2 up
sh sleep 45; tail -n 2 /tmp/rx.log
sh cmp /tmp/big.bin /tmp/copy.bin && echo IDENTICAL
exit
```
Type `link s1 s2 down` within a few seconds of starting the sender, so the break happens while the file is moving (the transfer takes about 42 s).

What you should see:
- `dump-flows` before the cut: the rule for `nw_dst=10.0.0.2` outputs to `s1-eth2` (path A); after the cut, to `s1-eth3` (path B).
- Terminal 1: `port s1-eth2 is DOWN`, `REROUTE path A -> path B (rules sent in 0.6 ms)`, and after the repair `REROUTE path B -> path A`.
- `rx.log`: `COMPLETE: 20972 chunks, N were lost and recovered, 0 duplicates` with N above zero.
- `IDENTICAL`.

Always leave Mininet with `exit`. The DOWN and "both paths are down" lines printed during `exit` are normal shutdown messages.

## Test results

All 11 test cases passed on Ubuntu 22.04 (Python 3.10, Mininet 2.3, POX 0.7.0):

| Measure | Result |
|---|---|
| Rule change after a link failure | 0.6 ms |
| Chunks lost and recovered, single link cut | 6 to 8 |
| Chunks lost and recovered, both paths down for 3 s | 1,245 |
| Received file identical to the original | every run |

Full results and screenshots: `docs/TEST_PLAN.pdf`.

## Useful commands

| Command | Effect |
|---|---|
| `sh ovs-ofctl dump-flows s1` | show s1's rules (port 2 = path A, port 3 = path B) |
| `link s1 s2 down` / `up` | cut or repair a link |
| `sudo mn -c` | clean up after a crash |