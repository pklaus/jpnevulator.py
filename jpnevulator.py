#!/usr/bin/env python

"""
jpnevulator.py

A Python version of jpnevulator.

If you don't need jpnevulator CLI compatiblitity,
you could also use https://git.jim.sh/jim/terminal.git .

Usage of the original jpnevulator:

jpnevulator [--version] [--help] [--checksum] [--crc16=poly]
  [--crc8=poly] [--fuck-up] [--file=file] [--no-send]
  [--delay-line=microseconds] [--delay-byte=microseconds]
  [--print] [--size=size] [--tty=tty] [--pty [=alias]] [--width] [--pass]
  [--read] [--write] [--timing-print] [--timing-delta=microseconds]
  [--ascii] [--alias-separator=separator] [--byte-count]
  [--control] [--control-poll=microseconds] [--count=bytes] <file>

"""

import argparse
import sys
import time
from datetime import datetime as dt

import serial

try:
    clock = time.perf_counter
except AttributeError:
    clock = time.time

class MultiArg(argparse.Action):
    """
    An action adding the supplied values of multiple
    statements of the same optional argument to a list.

    inspired by http://stackoverflow.com/a/12461237/183995
    """
    def __call__(self, parser, namespace, values, option_strings=None):
        dest = getattr(namespace, self.dest, None) 
        #print(self.dest, dest, self.default, values, option_strings)
        if(not hasattr(dest,'append') or dest == self.default):
            dest = []
            setattr(namespace, self.dest, dest)
            parser.set_defaults(**{self.dest:None}) 
        dest.append(values)

def port_def(string):
    if ':' in string:
        port, _, alias = string.partition(':')
    else:
        port, alias = string, None
    if '@' in port:
        port, _, baudrate = port.partition('@')
        try:
            baudrate = int(baudrate)
        except ValueError:
            raise argparse.ArgumentTypeError('the specified baudrate is not an integer')
    else:
        baudrate = None
    return {'port': port, 'alias': alias, 'baudrate': baudrate}

def hex_format(chunk):
    try:
        return ' '.join('{:02X}'.format(byte) for byte in chunk)
    except ValueError:
        return ' '.join('{:02X}'.format(ord(byte)) for byte in chunk)

def ascii_format(chunk):
    printable = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
    try:
        chars = [chr(i) for i in chunk]
        return ''.join([char if char in printable else '.' for char in chars])
    except TypeError:
        chars = chunk
        return ''.join([char if char in printable else '.' for char in chars])

def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[1])
    parser.add_argument('-r', '--read', action='store_true', help='Put the program in read mode. This way you read the data from the given serial device(s) and write it to the file given or stdout if none given. See the read options section for more read specific options.')
    parser.add_argument('-w', '--write', action='store_true', help='Put the program in write mode. This way you read data from a given file or stdin if none given and write it to the serial device(s) given. See the write options section for more write specific options.')
    parser.add_argument('-t', '--tty', type=port_def, dest='ttys', action=MultiArg, metavar='NAME:ALIAS', help="The serial device to read from or write to. Use multiple times to read/write from/to more than one serial device(s). For handy reference you can also separate an alias from the tty name with a collon ':'. If a collon is for some strange reason part of your device name, you can use the --alias-separator option to specify another separation string. If an alias is given it will be used as the name of the serial device.")
    parser.add_argument('-e', '--timing-delta', type=int, metavar='MICROSECONDS', default=100000, help='The timing delta is the amount of microseconds between two bytes that the latter is considered to be part of a new package. The default is 100 miliseconds. Use this option in conjunction with the --timing-print option.')
    parser.add_argument('-g', '--timing-print', action='store_true', help='Print a line of timing information before every continues stream of bytes. When multiple serial devices are given also print the name or alias of the device where the data is coming from.')
    parser.add_argument('-a', '--ascii', action='store_true', help="Besides the hexadecimal output also display an extra column with the data in the ASCII representation. Non printable characters are displayed as a dot '.'. The ASCII data is displayed after the hexadecimal data.")
    parser.add_argument('-u', '--baudrate', type=int, default=9600, help='The baudrate to open the serial port at.')
    parser.add_argument('-i', '--width', type=int, default=16, help='The number of bytes to display on one line. The default is 16.')
    args = parser.parse_args()

    if not args.ttys:
        parser.error('please provide at least one --tty')

    num = 0
    ttys = args.ttys
    for tty in ttys:
        if not tty['baudrate']: tty['baudrate'] = args.baudrate
        if not tty['alias']: tty['alias'] = 'Port' + str(num)
        tty['buffer'] = b''
        tty['ser'] = serial.Serial(tty['port'], baudrate=tty['baudrate'], timeout=0)
        tty['last_byte'] = clock()
        num += 1

    try:
        while True:
            for tty in ttys:
                new_data = tty['ser'].read()
                if len(new_data) > 0:
                    tty['buffer'] += new_data
                    tty['last_byte'] = clock()
            for tty in ttys:
                if tty['buffer'] and (clock() - tty['last_byte']) > args.timing_delta/1E6:
                    line = '{0}: {1}\n'.format(dt.now().isoformat(' '), tty['alias'])
                    sys.stdout.write(line)
                    while tty['buffer']:
                        chunk = tty['buffer'][:args.width]
                        tty['buffer'] = tty['buffer'][args.width:]
                        fmt = "{{hex:{0}s}}".format(args.width*3)
                        line = fmt.format(hex=hex_format(chunk))
                        if args.ascii:
                            fmt = "{{ascii:{0}s}}".format(args.width)
                            line += ' ' + fmt.format(ascii=ascii_format(chunk))
                        line = line.strip()
                        line += '\n'
                        sys.stdout.write(line)
                    sys.stdout.flush()
    except KeyboardInterrupt:
        sys.exit(1)

if __name__ == "__main__": main()
