"""Build the patched ifs2 head image (10.1\" facelift display) from your OWN ifs2 dump."""
import os

import struct, sys, re
from ifstool import decompress_ifs, parse_imagefs, wsum
from lzo import lzo1x_decompress
from lzoc import compress
from cksum import cksum

def repack_nested(outer, oents, name, path, editfn):
    e = next(x for x in oents if x['path'] == name)
    nxt = min(x['off'] for x in oents if x['t'] == 'f' and x['off'] > e['off'])
    img = bytes(outer[e['off']:e['off'] + e['size']])
    h, startup, fs0, blocks = decompress_ifs(img)
    fs = bytearray(fs0)
    _, ients = parse_imagefs(fs)
    edits = path if isinstance(path, dict) else {path: editfn}
    for pth, fn in edits.items():
        fe = next(x for x in ients if x['path'] == pth)
        old = bytes(fs[fe['off']:fe['off'] + fe['size']])
        new = fn(old)
        assert len(new) == len(old)
        fs[fe['off']:fe['off'] + fe['size']] = new
        if pth.endswith('.xml'): last = new
    isz = struct.unpack_from('<I', fs, 8)[0]
    fs[isz - 4:isz] = b'\0' * 4
    fs[isz - 4:isz] = struct.pack('<I', (-wsum(fs[:isz])) & 0xffffffff)
    stream = bytearray()
    for bi, (p, L, ul) in enumerate(blocks):
        a = bi * 65536
        if fs[a:a + ul] == fs0[a:a + ul]:
            stream += img[p:p + 2 + L]
        else:
            c = compress(fs[a:a + ul]); b2, end = lzo1x_decompress(c)
            assert b2 == fs[a:a + ul] and end == len(c)
            stream += len(c).to_bytes(2, 'big') + c
    stream += b'\0\0'
    n = bytearray(startup) + stream
    while len(n) % 4: n.append(0)
    n += b'\0' * 4; st = len(n)
    struct.pack_into('<I', n, 0x28, st)
    ss = h['startup_size']
    struct.pack_into('<I', n, ss - 4, 0)
    struct.pack_into('<I', n, ss - 4, (-wsum(n[:ss])) & 0xffffffff)
    struct.pack_into('<I', n, st - 4, (-wsum(n[:st])) & 0xffffffff)
    assert wsum(n[:st]) == 0 and decompress_ifs(bytes(n))[2] == bytes(fs)
    assert e['off'] + len(n) <= nxt and set(outer[e['off'] + e['size']:nxt]) <= {0}
    outer[e['off']:e['off'] + e['size']] = b'\0' * e['size']
    outer[e['off']:e['off'] + len(n)] = n
    struct.pack_into('<I', outer, e['dirent'] + 28, len(n))
    return new

def xml_edit(vals):
    def f(xml):
        i = xml.find(b"<Display ID='4'>"); j = xml.find(b'</VideoMode>', i)
        blk = xml[i:j].decode()
        for key, val in vals.items():
            m = re.search(r'(\n\s*)(%s)(\s*)= \'([^\']*)\'' % key, blk)
            assert m, key
            sp = m.group(3); diff = len(val) - len(m.group(4))
            assert len(sp) - diff >= 1
            rep = m.group(1) + key + ' ' * (len(sp) - diff) + "= '" + val + "'"
            blk = blk[:m.start()] + rep + blk[m.end():]
        out = xml[:i] + blk.encode() + xml[j:]
        assert len(out) == len(xml)
        return out
    return f

def dm_edit(w, hgt, mode='free'):
    def f(js):
        lines = js.decode('latin1').split('\n')
        assert '"LVDS1"' in lines[49]
        add = ', "width" : %d, "height" : %d, "scale_mode" : "%s"' % (w, hgt, mode)
        lines[49] = lines[49].replace('"LVDS1"', '"LVDS1"' + add, 1)
        ci = next(k for k, l in enumerate(lines) if 'for engineering purposes' in l)
        lines[ci] = lines[ci][:len(lines[ci]) - len(add)]
        out = '\n'.join(lines)
        if True:  # scale rear-view camera + TopView to 1540x720
            cut = out.index('"hbprod"'); a, b = out[:cut], out[cut:]
            r0 = a.index('"rvc"'); t0 = a.index('"target"', r0); t1 = a.index('}', t0)
            blk = a[t0:t1]
            nb = blk.replace('"y": 56', '"y": 84').replace('"w": 720', '"w": 1083')
            assert '"y": 84' in nb and '1083' in nb and '"h": 384' in nb
            nb = nb.replace('"h": 384', '"h": 576')
            a = a[:t0] + nb + a[t1:]
            z0 = a.index('"zfas"'); t0 = a.index('"target"', z0); t1 = a.index('}', t0)
            blk = a[t0:t1]; nb = blk.replace('"w": 1024', '"w": 1540').replace('"h": 480', '"h": 720')
            assert nb != blk
            a = a[:t0] + nb + a[t1:]
            grow = len(a) + len(b) - len(out)
            k = a.index('#this block configures the RVC')
            a = a[:k] + '#this block configures the RVC'[:30 - grow] + a[k + 30:]
            out = a + b
        return out.encode('latin1')
    return f


ORIG_IFS2 = (2802035159, 104857600)   # cksum of untouched ifs2 (MHI2Q P5092 / SW 1329)
RESULT_HEAD = (277332389, 40894464)   # expected cksum of the generated head image
HEAD_LEN = 40894464                   # 39 MiB - only this part is changed


def anim_patch(b):
    """libdm_modAnim.so: force startup-animation window/viewport to 1540x720 (animation stays 1024x480 internally)."""
    b = bytearray(b)
    assert b[0x258c:0x2590] == bytes.fromhex('0190a0e1') and b[0x2594:0x2598] == bytes.fromhex('02b0a0e1'), 'unexpected libdm_modAnim.so'
    b[0x258c:0x2590] = (0xE3009604).to_bytes(4, 'little')   # movw r9,  #1540
    b[0x2594:0x2598] = (0xE300B2D0).to_bytes(4, 'little')   # movw r11, #720
    return bytes(b)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit('usage: python3 build_ifs2.py <ifs2_original.img> <ifs2_facelift_head.img>')
    src_path, dst_path = sys.argv[1:]
    outer = bytearray(open(src_path, 'rb').read())
    ck = (cksum(outer), len(outer))
    if ck != ORIG_IFS2:
        sys.exit('ABORT: input cksum %s %s does not match the tested firmware %s %s' % (ck + ORIG_IFS2))
    # Panel timing for 10.1" LG LPM101G235A (80A919620), see docs/TECHNICAL.md
    timing = dict(uActiveH='1540', uFrontPorchH='52', uPulseWidthH='8', uBackPorchH='104',
                  uActiveV='720', uFrontPorchV='36', uPulseWidthV='4', uBackPorchV='6',
                  uPixelFreq='78316', uRefreshRate='60000')
    oh, oe = parse_imagefs(outer)
    repack_nested(outer, oe, 'ifs_display.img', 'proc/boot/qcdisplaycfg_MMX2.xml', xml_edit(timing))
    repack_nested(outer, oe, 'ifs_coreservices3.img', {
        'etc/eso/production/displaymanager.json': dm_edit(2316, 1080),
        'mnt/app/eso/lib/libdm_modAnim.so': anim_patch}, None)
    osz = oh['image_size']
    struct.pack_into('<I', outer, osz - 4, 0)
    struct.pack_into('<I', outer, osz - 4, (-wsum(outer[:osz])) & 0xffffffff)
    assert wsum(outer[:osz]) == 0
    out = bytes(outer[:HEAD_LEN])
    ck = (cksum(out), len(out))
    if ck != RESULT_HEAD:
        sys.exit('ABORT: result cksum %s %s differs from expected %s %s' % (ck + RESULT_HEAD))
    open(dst_path, 'wb').write(out)
    print('OK: %s  cksum %d %d' % ((dst_path,) + ck))
