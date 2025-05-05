"""
0 39 A0/D0
1 38 A1/D1
2 37 A2/D2
3 36 A3/D3
4 35 A4/D4
5 34 A5/D5
6 33 A6/D6
7 32 A7/D7
8 21 A8
9 22 A9
10 23 A10
11 24 A11
12 25 A12
13 26 A13
14 29 !PSEN
15 30 ALE
16 16 !WR
17 17 !RD

top 8 bits are cycles at 100mhz since last change
"""

import sys

class Record:
    def __init__(self, value):
        self.address = value & 0x3fff
        self.data = value & 0xff
        self.psen_al = value & 0x4000
        self.ale = value & 0x8000
        self.wr_al = value & 0x10000
        self.rd_al = value & 0x20000
        self.delay = (value & 0xff00000000) >> 32

    def __str__(self):
        return "0x%04x / 0x%02x - %s %s %s %s [%d]" % (
            self.address,
            self.data,
            "/PSEN" if self.psen_al else "     ",
            "ALE" if self.ale else "   ",
            "/RD" if self.rd_al else "   ",
            "/WR" if self.wr_al else "   ",
            self.delay
        )

def decode(line):
    global cycles
    value = int(line, 16)
    return Record(value)

with open(sys.argv[1], "r") as f:
    last_ale = 0
    last_psen = 1
    last_rd = 1
    last_wr = 1
    last_addr = 0
    seq = "   "
    for line in f.readlines():
        record = decode(line)
        addrlatch = last_ale and not record.ale
        rom = not last_psen and record.psen_al
        rd = not last_rd and record.rd_al
        wr = not last_wr and record.wr_al
        extra = ""
        if addrlatch:
            if record.address == last_addr + 1:
                seq = "SEQ"
            else:
                seq = "   "
            last_addr = record.address
        "SEQ" if seq else "   ",
        if rom:
            extra = "===   ROM[0x%04x] -> 0x%02x" % (last_addr, record.data) + " " + seq
        if rd:
            extra = "===   RAM[0x%04x] -> 0x%02x" % (last_addr, record.data) + " " + seq
        if wr:
            extra = "===   0x%02x -> RAM[0x%04x]" % (last_addr, record.data) + " " + seq
        print(
            str(record),
            "LATCH" if addrlatch else "     ",
            "ROM" if rom else "   ",
            "RD" if rd else "  ",
            "WR" if wr else "  ",
            extra
        )
        last_ale = record.ale
        last_psen = record.psen_al
        last_rd = record.rd_al
        last_wr = record.wr_al

