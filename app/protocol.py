"""Packet formats shared by sender.py and receiver.py.

Every packet starts with 5 bytes: type (1 byte) + number (4 bytes).
  DATA  number = sequence number, followed by the file chunk
  END   number = total number of chunks (sent after the last chunk)
  NACK  number = how many sequence numbers follow (4 bytes each)
  DONE  number = 0 (receiver has the whole file)
"""
import struct

DATA, END, NACK, DONE = 1, 2, 3, 4
HEADER = struct.Struct("!BI")
CHUNK = 1000          # bytes of file per DATA packet
PORT = 5001           # receiver's UDP port


def pack(kind, number, body=b""):
    return HEADER.pack(kind, number) + body


def unpack(packet):
    kind, number = HEADER.unpack_from(packet)
    return kind, number, packet[HEADER.size:]


def pack_nack(seqs):
    return pack(NACK, len(seqs), struct.pack("!%dI" % len(seqs), *seqs))


def unpack_nack(body, count):
    return list(struct.unpack("!%dI" % count, body[:4 * count]))
