"""POX controller: send traffic on path A, move it to path B when a link fails.

Start it with:  ./controller/run.sh
"""
import time

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import IPAddr

log = core.getLogger("adaptive")

H1, H2 = IPAddr("10.0.0.1"), IPAddr("10.0.0.2")

# Each path is the set of (switch, port) pairs it uses.
PATHS = {
    "A": {(1, 2), (2, 1), (2, 2), (4, 2)},   # s1 - s2 - s4
    "B": {(1, 3), (3, 1), (3, 2), (4, 3)},   # s1 - s3 - s4
}
EDGE_PORT = {"A": 2, "B": 3}   # port on s1 and s4 that leads into each path


class Adaptive(object):
    def __init__(self):
        self.conns = {}          # dpid -> connection
        self.down = set()        # (dpid, port) pairs that are down
        self.path = "A"
        core.openflow.addListeners(self)

    def add_rule(self, dpid, out_port, in_port=None, dst=None):
        msg = of.ofp_flow_mod()
        msg.priority = 100
        if in_port is not None:
            msg.match.in_port = in_port
        if dst is not None:
            msg.match.dl_type = 0x0800
            msg.match.nw_dst = dst
        msg.actions.append(of.ofp_action_output(port=out_port))
        self.conns[dpid].send(msg)   # same match + priority replaces the old rule

    def install(self, dpid):
        if dpid not in self.conns:
            return
        if dpid in (2, 3):                   # middle switches: just pass through
            self.add_rule(dpid, 2, in_port=1)
            self.add_rule(dpid, 1, in_port=2)
        elif dpid == 1:
            self.add_rule(1, 1, dst=H1)
            self.add_rule(1, EDGE_PORT[self.path], dst=H2)
        elif dpid == 4:
            self.add_rule(4, 1, dst=H2)
            self.add_rule(4, EDGE_PORT[self.path], dst=H1)

    def _handle_ConnectionUp(self, event):
        # Forget old port states for this switch (a new Mininet run reuses
        # the same switch names) and take the current ones from the switch.
        dpid = event.dpid
        self.conns[dpid] = event.connection
        self.down = {(d, p) for (d, p) in self.down if d != dpid}
        for port in event.connection.features.ports:
            if port.state & of.OFPPS_LINK_DOWN or port.config & of.OFPPC_PORT_DOWN:
                self.down.add((dpid, port.port_no))
        log.info("switch s%d connected", dpid)
        self.install(dpid)
        self.choose_path(time.time())

    def _handle_PortStatus(self, event):
        t0 = time.time()
        key = (event.dpid, event.port)
        desc = event.ofp.desc
        is_down = (event.deleted or desc.config & of.OFPPC_PORT_DOWN
                   or desc.state & of.OFPPS_LINK_DOWN)
        if is_down:
            self.down.add(key)
        else:
            self.down.discard(key)
        log.info("port s%d-eth%d is %s", event.dpid, event.port,
                 "DOWN" if is_down else "UP")
        self.choose_path(t0)

    def choose_path(self, t0):
        # Prefer A; use B only if A is broken; if both are broken, stay put.
        if not PATHS["A"] & self.down:
            best = "A"
        elif not PATHS["B"] & self.down:
            best = "B"
        else:
            log.warning("both paths are down, waiting for a repair")
            return
        if best != self.path:
            old, self.path = self.path, best
            self.install(1)
            self.install(4)
            log.warning("REROUTE path %s -> path %s (rules sent in %.1f ms)",
                        old, best, (time.time() - t0) * 1000)


def launch():
    core.registerNew(Adaptive)
