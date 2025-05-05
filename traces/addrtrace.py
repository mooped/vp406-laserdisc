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

import argparse
import copy
from disasm51.instructions import ArgType, Instructions
from disasm51.utils import binary_hint

parser = argparse.ArgumentParser(
    prog='8051 Trace Analyzer',
    description='Convert a trace of the 8051 address/data bus and some control pins into a readable instruction trace')
parser.add_argument('filename', type=str, help='Input filename')
parser.add_argument('-s', '--skip', type=int, default=0, help='Number of records in the input file to skip, use this to start disassembling on an instruction boundary')
parser.add_argument('-v', '--verbose', action='store_true', help='Print each decoded record and detected reads/writes interleaved with the decoded data')

args = parser.parse_args()

instructions = Instructions()

filename = args.filename
skip = args.skip

def hexdump(buffer):
    return " ".join(map(lambda x: "%02x" % x, buffer))

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

def format_instruction(addr, buffer):
    instruction = instructions[buffer[0]]
    addr_rel = addr + instruction.length    # Start of next instruction
    ibuffer = copy.deepcopy(buffer) # Working copy of the buffer
    val = ibuffer.pop(0) # Pop bytes from the buffer as they are consumed

    # Process args in sequence
    args = []
    hints = ''
    for arg in instruction.args or []:
        argtype = arg
        if arg == ArgType.LABEL:
            val = ((val << 8) | ibuffer.pop(0))
        elif arg == ArgType.ADDR:
            val = (addr_rel & 0xf800) | val | ((buffer[0] << 3) & 0x0700)
            argtype = ArgType.LABEL
        elif arg == ArgType.REL:
            if val >= 0x80:
                val = val = 0x100
            val = addr_rel + val
            argtype = ArgType.LABEL
            if val < 0:
                # Error case
                argtype = None
            if arg == ArgType.IMM:
                hints += utils.binary_hint(val)

        if arg == ArgType.BIT:
            suffix = '.%d' % (val & 7)
            if val >= 0x80:
                val = val & 0xfb            # SFR
            else:
                val = 0x20 | (val >> 3)     # RAM
            argtype = ArgType.DATA
        else:
            suffix = ''

        if argtype == ArgType.DATA and val >= 0x80:
            hints += 'unknown SFR %02x' % val

        if argtype == ArgType.LABEL and val == addr:
            val_out = '$'   # Jump to self
        elif argtype == ArgType.LABEL:
            val_out = '%04xh' % val
        else:
            val_out = '%02x' % val
        
        # Accumulate decoded args
        args.append(val_out + suffix)

    # Format using the instruction mnemonic
    formatted = instruction.mnemonic.format(*args)
    if hints:
        formatted = formatted + '\t' + hints

    return formatted

class Trace:
    def __init__(self):
        self.last_addr = -1
        self.instruction_start = -1
        self.instruction_sequential = False
        self.buffer = []

    def flush(self, sequential=True):
        self.buffer = []
        self.instruction_start = self.last_addr
        self.instruction_sequential = sequential

    def iread(self, addr, data):
        if addr == self.last_addr:  # Ignore duplicate reads - long running instructions can reread the same byte
            return

        sequential = addr == self.last_addr + 1
        seq = "SEQ" if sequential else "   "

        instruction = ""
        ibuffer = []

        # If not sequential we just took a jump, so flush the disassembly buffer
        if not sequential:
            self.flush(False)

        if args.verbose:
            print("%s READ ROM[0x%04x]: 0x%02x - %s" % (seq, addr, data))

        # Buffer bytes until we have a complete instruction 
        if addr != self.last_addr:
            self.buffer.append(data)

            # If the buffer doesn't start with a valid instruction, immediately flush it - likely at start of trace
            if not self.buffer[0] in instructions:
                print("FLUSH - invalid opcode %02h" % self.buffer[0])
                self.flush(sequential)
            else:
                instruction = instructions[self.buffer[0]]
                # Does buffer length match instruction lengthj
                if len(self.buffer) > instruction.length:
                    print("ERROR - buffer length exceeds instruction length %s" % hexdump(self.buffer))
                if len(self.buffer) >= instruction.length:
                    print("EXECUTE 0x%04x: %s    %s %s" % (self.instruction_start, hexdump(self.buffer).ljust(9), format_instruction(self.instruction_start, self.buffer).ljust(40), "SEQ" if self.instruction_sequential else "   "))
                    self.flush(sequential)

        self.last_addr = addr

    def read(self, addr, data):
        print("                                READ RAM[0x%04x]: 0x%02x" % (addr, data))

    def write(self, addr, data):
        print("                               WRITE RAM[0x%04x]: 0x%02x" % (addr, data))

with open(filename, "r") as f:
    trace = Trace()
    last_ale = 0
    last_psen = 1
    last_rd = 1
    last_wr = 1
    last_addr = 0
    for line in f.readlines():
        # Skip some records to start on an instruction boundary
        if skip > 0:
            skip -= 1
            #continue
        record = decode(line)
        addrlatch = last_ale and not record.ale
        rom = not last_psen and record.psen_al
        rd = not last_rd and record.rd_al
        wr = not last_wr and record.wr_al
        extra = ""
        if addrlatch:
            last_addr = record.address
        if rom:
            extra = "===   ROM[0x%04x] -> 0x%02x" % (last_addr, record.data)
            trace.iread(last_addr, record.data)
        if rd:
            extra = "===   RAM[0x%04x] -> 0x%02x" % (last_addr, record.data)
            trace.read(last_addr, record.data)
        if wr:
            extra = "===   0x%02x -> RAM[0x%04x]" % (last_addr, record.data)
            trace.write(last_addr, record.data)
        if args.verbose:
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

