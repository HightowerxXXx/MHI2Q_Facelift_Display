"""Minimal QNX IFS helpers: parse imagefs dirents, decompress LZO-compressed IFS."""
import stat
import struct

from lzo import lzo1x_decompress


def wsum(b):
    n = len(b) // 4
    return sum(struct.unpack('<%dI' % n, b[:n * 4])) & 0xffffffff


def parse_imagefs(fs):
    sig, flags, isz, hds, doff = struct.unpack_from('<7sBIII', fs, 0)
    assert sig == b'imagefs', sig
    ents = []
    p = doff
    while p < isz:
        size, ext, ino, mode, gid, uid, mtime = struct.unpack_from('<HHIIIII', fs, p)
        if size == 0:
            break
        b = p + 24
        if stat.S_ISREG(mode):
            off, fsz = struct.unpack_from('<II', fs, b)
            path = fs[b + 8:p + size].split(b'\0')[0].decode()
            ents.append(dict(t='f', path=path, off=off, size=fsz, dirent=p))
        elif stat.S_ISLNK(mode):
            so, ss = struct.unpack_from('<HH', fs, b)
            path = fs[b + 4:p + size].split(b'\0')[0].decode()
            ents.append(dict(t='l', path=path, target=fs[b + so:b + so + ss].rstrip(b'\0').decode()))
        else:
            ents.append(dict(t='o', path=fs[b:p + size].split(b'\0')[0].decode(), mode=oct(mode)))
        p += size
    return dict(flags=flags, image_size=isz, hdr_dir_size=hds, dir_offset=doff), ents


def decompress_ifs(img):
    """img: bytes starting with startup header. Returns (header fields, startup bytes, imagefs bytes, block list)."""
    f = struct.unpack_from('<IHBBHHIIIIIIIII', img, 0)
    assert f[0] == 0x00ff7eeb
    flags1, startup_size, stored_size, imagefs_size = f[2], f[11], f[12], f[14]
    comp = flags1 & 0x1c
    assert comp == 0x08, hex(comp)  # LZO
    p = startup_size
    out = bytearray()
    blocks = []
    while True:
        L = int.from_bytes(img[p:p + 2], 'big')
        if L == 0:
            break
        blk, end = lzo1x_decompress(img[p + 2:p + 2 + L])
        assert end == L
        blocks.append((p, L, len(blk)))
        out += blk
        p += 2 + L
    assert len(out) == imagefs_size, (hex(len(out)), hex(imagefs_size))
    return dict(flags1=flags1, startup_size=startup_size, stored_size=stored_size,
                imagefs_size=imagefs_size, comp_end=p), img[:startup_size], bytes(out), blocks
