"""Patch graphics.conf inside your OWN mifs dump: display 4 1024x480 -> 1540x720."""
import sys
import struct
from prov import decomp_prov
from ifstool import decompress_ifs, parse_imagefs, wsum

from cksum import cksum
W = '1540'
if len(sys.argv) != 3:
    sys.exit('usage: python3 build_mifs.py <mifs_original.img> <mifs_facelift.img>')
d = bytearray(open(sys.argv[1], 'rb').read()); base = 0x448
if (cksum(d), len(d)) != (4082701332, 10485760):
    sys.exit('ABORT: input mifs does not match the tested firmware')
img = bytes(d[base:])
h, st, fs, blocks = decompress_ifs(img)
_, ents = parse_imagefs(fs)
g = next(e for e in ents if e['path'] == 'proc/boot/graphics.conf')
gc = fs[g['off']:g['off'] + g['size']]
a = g['off'] + gc.find(b'1024 x 480 @ 60')
isz = h['imagefs_size']

# expected new imagefs
exp = bytearray(fs)
exp[a:a + 15] = (W + ' x 720 @ 60').encode()
exp[isz - 4:isz] = b'\0\0\0\0'
exp[isz - 4:isz] = struct.pack('<I', (-wsum(exp[:isz])) & 0xffffffff)
assert wsum(exp[:isz]) == 0

# patch literal bytes in compressed stream (block 23)
bi = a // 65536
p, L, ul = blocks[bi]
src = bytearray(img[p + 2:p + 2 + L])
out, prov = decomp_prov(bytes(src))
for o in list(range(a, a + 15)) + list(range(isz - 4, isz)):
    if exp[o] != fs[o]:
        sidx = prov[o - bi * 65536]
        assert sidx >= 0, ('not literal', o)
        src[sidx] = exp[o]
d[base + p + 2:base + p + 2 + L] = src

# fix stored-stream checksum (last 4 bytes of stored region)
s = h['stored_size']
struct.pack_into('<I', d, base + s - 4, 0)
struct.pack_into('<I', d, base + s - 4, (-wsum(d[base:base + s])) & 0xffffffff)
assert wsum(d[base:base + s]) == 0

# verify full decompression equals expected
h2, st2, fs2, _ = decompress_ifs(bytes(d[base:]))
assert fs2 == bytes(exp), 'mismatch (later match references patched bytes?)'
assert wsum(d[base:base + h['startup_size']]) == 0
if (cksum(d), len(d)) != (1799675391, 10485760):
    sys.exit('ABORT: result cksum differs from expected')
open(sys.argv[2], 'wb').write(d)
print('OK: graphics.conf display 4 -> 1540 x 720 @ 60, cksum', cksum(d), len(d))
