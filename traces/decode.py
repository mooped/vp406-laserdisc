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

cycles = 0

def decode(line):
    global cycles
    value = int(line, 16)
    address = value & 0x3fff
    data = value & 0xff
    psen_al = value & 0x4000
    ale = value & 0x8000
    rd_al = value & 0x20000
    wr_al = value & 0x10000
    delay = (value & 0xff00000000) >> 32

    cycles += delay

    return "0x%04x / 0x%02x - %s %s %s %s [%d]" % (
            address,
            data,
            "/PSEN" if psen_al else "     ",
            "ALE" if ale else "   ",
            "/RD" if rd_al else "   ",
            "/WR" if wr_al else "   ",
            delay
        )

with open("log6.txt", "r") as f:
    for line in f.readlines():
        print(decode(line))

print("Total Cycles:", cycles)
