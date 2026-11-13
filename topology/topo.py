#!/usr/bin/env python3
"""Mininet topology: two hosts joined by two paths.

        +---- s2 ----+          path A (primary)
  h1 -- s1           s4 -- h2
        +---- s3 ----+          path B (backup)

Port numbers (fixed by the order links are added):
  s1: 1 = h1, 2 = s2, 3 = s3        s4: 1 = h2, 2 = s2, 3 = s3
  s2: 1 = s1, 2 = s4                s3: 1 = s1, 2 = s4

Run (with the POX controller already running):
  sudo python3 topology/topo.py
Cut a link from the Mininet prompt with:  link s1 s2 down
"""
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.log import setLogLevel


class TwoPathTopo(Topo):
    def build(self):
        h1 = self.addHost("h1", ip="10.0.0.1/24")
        h2 = self.addHost("h2", ip="10.0.0.2/24")
        s1, s2, s3, s4 = [self.addSwitch("s%d" % i) for i in range(1, 5)]
        self.addLink(h1, s1)    # s1 port 1
        self.addLink(h2, s4)    # s4 port 1
        self.addLink(s1, s2)    # s1 port 2, s2 port 1
        self.addLink(s1, s3)    # s1 port 3, s3 port 1
        self.addLink(s2, s4)    # s2 port 2, s4 port 2
        self.addLink(s3, s4)    # s3 port 2, s4 port 3


def make_net():
    net = Mininet(topo=TwoPathTopo(), switch=OVSSwitch, autoSetMacs=True,
                  controller=lambda name: RemoteController(
                      name, ip="127.0.0.1", port=6633))
    net.start()
    net.staticArp()     # no ARP broadcasts, so the loop never floods
    return net


if __name__ == "__main__":
    setLogLevel("info")
    net = make_net()
    CLI(net)
    net.stop()
