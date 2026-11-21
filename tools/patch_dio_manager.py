"""Patch your OWN stock dio_manager so CarPlay runs full-screen 1536x720 (stream + window)."""
import struct, sys
from cksum import cksum

ORIG = (1446556070, 691203)
RESULT = (2811786567, 691203)
OFF = 0x676cc   # file offset of vaddr 0x1676cc (resolution setup in START_CARPLAY path)
CODE = [0xE59720E8,  # ldr  r2, [r7, #0xe8]
        0xE3001600,  # movw r1, #1536
        0xE582122C,  # str  r1, [r2, #0x22c]   window width
        0xE5821224,  # str  r1, [r2, #0x224]   resolution width (sent to iPhone)
        0xE30012D0,  # movw r1, #720
        0xE5821230,  # str  r1, [r2, #0x230]   window height
        0xE5821228,  # str  r1, [r2, #0x228]   resolution height
        0xEA000002]  # b    0x1676f8

if len(sys.argv) != 3:
    sys.exit('usage: python3 patch_dio_manager.py <dio_manager_original> <dio_manager_patched>')
d = bytearray(open(sys.argv[1], 'rb').read())
if (cksum(d), len(d)) != ORIG:
    sys.exit('ABORT: input dio_manager does not match the tested firmware')
for i, w in enumerate(CODE):
    struct.pack_into('<I', d, OFF + 4 * i, w)
if (cksum(d), len(d)) != RESULT:
    sys.exit('ABORT: result cksum differs from expected')
open(sys.argv[2], 'wb').write(d)
print('OK: cksum', cksum(d), len(d))
