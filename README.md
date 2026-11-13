# Adaptive communication network with failure recovery (UDP)

Mini project 1, Computer Networks, Team 1.

A file is sent over UDP across a Mininet network that has two paths. When a link on the main path breaks, the POX controller moves traffic to the backup path. Packets lost during the break are requested again by the receiver and resent by the sender, so the file still arrives complete.

```
        +---- s2 ----+          path A (main)
  h1 -- s1           s4 -- h2
        +---- s3 ----+          path B (backup)
```

## Files

| File | What it does |
|---|---|
| `topology/topo.py` | Builds the network in Mininet |
| `controller/adaptive.py` | POX controller: installs rules, switches path when a link goes down |
| `controller/run.sh` | Starts POX with the controller |
| `app/sender.py` | Sends a file over UDP, resends chunks the receiver asks for |
| `app/receiver.py` | Receives the file, asks for missing chunks (NACK) |
| `app/protocol.py` | Packet format used by both |
| `tests/run_tests.py` | Automated system tests (8 test cases) |
| `docs/SRS.md` | Software requirements specification |
| `docs/TEST_PLAN.md` | Test plan and test cases |

## Setup (once, on Ubuntu 22.04 or 24.04)

```
sudo apt update
sudo apt install -y mininet openvswitch-switch git
git clone https://github.com/noxrepo/pox ~/pox
```

## Run it by hand

Terminal 1, the controller (leave it running):
```
cd ~/adaptive-network
./controller/run.sh
```

Terminal 2, the network:
```
cd ~/adaptive-network
sudo python3 topology/topo.py
```

At the `mininet>` prompt:
```
pingall
h1 head -c 20M /dev/urandom > /tmp/big.bin
h2 python3 app/receiver.py --out /tmp/copy.bin > /tmp/rx.log &
h1 python3 app/sender.py --dest 10.0.0.2 --file /tmp/big.bin --rate 500 &
link s1 s2 down
link s1 s2 up
sh sleep 45; tail -n 2 /tmp/rx.log
sh cmp /tmp/big.bin /tmp/copy.bin && echo IDENTICAL
exit
```

Type `link s1 s2 down` within a few seconds of starting the sender, so the break happens while the file is moving (the transfer takes about 40 s).

What you should see:
- Terminal 1: `port s1-eth2 is DOWN`, then `REROUTE path A -> path B`, and after `link s1 s2 up`, `REROUTE path B -> path A`.
- `rx.log`: `COMPLETE: 20972 chunks, N were lost and recovered, ...` with N above zero.
- `IDENTICAL`.

Useful extra commands at the prompt: `sh ovs-ofctl dump-flows s1` shows which port s1 sends traffic to (2 = path A, 3 = path B).

## Run the automated tests

With the controller running in terminal 1:
```
sudo python3 tests/run_tests.py
```
It takes about 1.5 minutes and ends with `8 of 8 tests passed`. If Mininet crashed earlier, run `sudo mn -c` first.

## Put it on GitHub

```
cd ~/adaptive-network
git init
git add .
git commit -m "Adaptive communication network with failure recovery"
git branch -M main
git remote add origin https://github.com/<your-username>/adaptive-network.git
git push -u origin main
```
Create the empty repository on github.com first. When asked for a password, use a personal access token (GitHub, Settings, Developer settings, Personal access tokens).
