"""POSIX `cksum` (same output as the cksum tool on the QNX unit)."""
import sys

_T = []
for i in range(256):
    c = i << 24
    for _ in range(8):
        c = ((c << 1) ^ 0x04C11DB7) if c & 0x80000000 else (c << 1)
    _T.append(c & 0xffffffff)


def cksum(data):
    c = 0
    for b in data:
        c = ((c << 8) ^ _T[((c >> 24) ^ b) & 0xff]) & 0xffffffff
    n = len(data)
    while n:
        c = ((c << 8) ^ _T[((c >> 24) ^ (n & 0xff)) & 0xff]) & 0xffffffff
        n >>= 8
    return (~c) & 0xffffffff


if __name__ == '__main__':
    for f in sys.argv[1:]:
        d = open(f, 'rb').read()
        print(cksum(d), len(d), f)
