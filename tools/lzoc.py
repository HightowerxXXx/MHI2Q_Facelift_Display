"""Simple LZO1X-compatible compressor (greedy + one-step lazy, hash chains).

Emits only well-defined LZO1X constructs: literal runs, M2 (short), M3, M4 matches
and the standard EOF marker 0x11 0x00 0x00.
"""

MAX_M2_DIST = 0x0800
MAX_M3_DIST = 0x4000
MAX_M4_DIST = 0xBFFF


def _ext(n, out):
    # write extension count n (>=1) using zero-bytes for 255 chunks
    while n > 255:
        out.append(0)
        n -= 255
    out.append(n)


def _find(data, i, chains, depth):
    n = len(data)
    if i + 3 > n:
        return 0, 0
    key = data[i:i + 3]
    best_len, best_dist = 0, 0
    cands = chains.get(key)
    if not cands:
        return 0, 0
    cnt = 0
    for j in reversed(cands):
        d = i - j
        if d > MAX_M4_DIST:
            break
        L = 3
        maxl = min(n - i, 2048)
        while L < maxl and data[j + L] == data[i + L]:
            L += 1
        # prefer shorter distance encodings when equal length
        if L > best_len or (L == best_len and d < best_dist):
            best_len, best_dist = L, d
            if L >= maxl:
                break
        cnt += 1
        if cnt >= depth:
            break
    # a 3-byte match at M4 distance costs 3 bytes, no gain
    if best_len == 3 and best_dist > MAX_M2_DIST:
        return 0, 0
    return best_len, best_dist


def _insert(data, i, chains):
    if i + 3 <= len(data):
        chains.setdefault(data[i:i + 3], []).append(i)


def compress(data, depth=48):
    data = bytes(data)
    n = len(data)
    chains = {}
    seq = []  # list of (literal_bytes, match_len, match_dist)
    lit_start = 0
    i = 0
    while i < n:
        L, d = _find(data, i, chains, depth)
        if L >= 3:
            # lazy: check next position
            _insert(data, i, chains)
            L2, d2 = _find(data, i + 1, chains, depth) if i + 1 < n else (0, 0)
            if L2 > L + 1:
                i += 1
                L, d = L2, d2
            else:
                pass
            seq.append((data[lit_start:i], L, d))
            for k in range(i if L2 <= L + 1 else i, i + L):
                _insert(data, k, chains)
            i += L
            lit_start = i
        else:
            _insert(data, i, chains)
            i += 1
    tail = data[lit_start:]
    return _encode(seq, tail)


def _encode(seq, tail):
    out = bytearray()
    first = True
    prev_next_slot = None  # index in out of the byte holding 'next' bits of previous match

    def emit_literals(lits, at_start):
        nonlocal prev_next_slot
        L = len(lits)
        if L == 0:
            return
        if at_start:
            if L <= 238:
                out.append(17 + L)
            else:
                t = L - 3
                if t <= 15:
                    out.append(t)
                else:
                    out.append(0)
                    _ext(t - 15, out)
            out.extend(lits)
            return
        if L <= 3:
            out[prev_next_slot] |= L
            out.extend(lits)
            return
        t = L - 3
        if t <= 15:
            out.append(t)
        else:
            out.append(0)
            _ext(t - 15, out)
        out.extend(lits)

    def emit_match(L, d):
        nonlocal prev_next_slot
        if L <= 8 and d <= MAX_M2_DIST:
            dd = d - 1
            out.append(((L - 1) << 5) | ((dd & 7) << 2))
            out.append(dd >> 3)
            prev_next_slot = len(out) - 2
        elif d <= MAX_M3_DIST:
            L2 = L - 2
            if L2 <= 31:
                out.append(32 | L2)
            else:
                out.append(32)
                _ext(L2 - 31, out)
            v = (d - 1) << 2
            out.append(v & 0xff)
            out.append(v >> 8)
            prev_next_slot = len(out) - 2
        else:
            dd = d - 0x4000
            t8 = 0
            if dd >= 0x4000:
                t8 = 8
                dd -= 0x4000
            assert 0 < dd < 0x4000 or t8
            L2 = L - 2
            if L2 <= 7:
                out.append(16 | t8 | L2)
            else:
                out.append(16 | t8)
                _ext(L2 - 7, out)
            v = dd << 2
            out.append(v & 0xff)
            out.append(v >> 8)
            prev_next_slot = len(out) - 2

    for lits, L, d in seq:
        emit_literals(lits, first)
        first = False
        emit_match(L, d)
    emit_literals(tail, first)
    out += b'\x11\x00\x00'
    return bytes(out)
