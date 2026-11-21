"""Pure-Python LZO1X decompressor (port of lib/lzo/lzo1x_decompress_safe.c logic)."""


def lzo1x_decompress(src, start=0):
    ip = start
    out = bytearray()
    state = 0
    if src[ip] > 17:
        t = src[ip] - 17
        ip += 1
        out += src[ip:ip + t]
        ip += t
        state = t if t < 4 else 4
    while True:
        t = src[ip]
        ip += 1
        if t < 16:
            if state == 0:
                if t == 0:
                    while src[ip] == 0:
                        t += 255
                        ip += 1
                    t += 15 + src[ip]
                    ip += 1
                t += 3
                out += src[ip:ip + t]
                ip += t
                state = 4
                continue
            elif state != 4:
                nxt = t & 3
                m_pos = len(out) - 1 - (t >> 2) - (src[ip] << 2)
                ip += 1
                length = 2
            else:
                nxt = t & 3
                m_pos = len(out) - (1 + 0x0800) - (t >> 2) - (src[ip] << 2)
                ip += 1
                length = 3
        elif t >= 64:
            nxt = t & 3
            m_pos = len(out) - 1 - ((t >> 2) & 7) - (src[ip] << 3)
            ip += 1
            length = (t >> 5) + 1
        elif t >= 32:
            length = t & 31
            if length == 0:
                while src[ip] == 0:
                    length += 255
                    ip += 1
                length += 31 + src[ip]
                ip += 1
            length += 2
            v = src[ip] | (src[ip + 1] << 8)
            ip += 2
            m_pos = len(out) - 1 - (v >> 2)
            nxt = v & 3
        else:
            m_pos = len(out) - ((t & 8) << 11)
            length = t & 7
            if length == 0:
                while src[ip] == 0:
                    length += 255
                    ip += 1
                length += 7 + src[ip]
                ip += 1
            length += 2
            v = src[ip] | (src[ip + 1] << 8)
            ip += 2
            m_pos -= v >> 2
            nxt = v & 3
            if m_pos == len(out):
                return bytes(out), ip
            m_pos -= 0x4000
        if m_pos < 0:
            raise ValueError("lookbehind overrun at ip=%d" % ip)
        for i in range(length):
            out.append(out[m_pos + i])
        state = nxt
        out += src[ip:ip + nxt]
        ip += nxt
