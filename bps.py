# Minimaler BPS-Patch-Ersteller und -Pruefer (Format von byuu/near, wie Flips/ROM Patcher JS).
import sys, zlib
def num(n):
    out = bytearray()
    while True:
        x = n & 0x7F; n >>= 7
        if n == 0: out.append(0x80 | x); break
        out.append(x); n -= 1
    return bytes(out)
def erstelle(src, tgt):
    p = bytearray(b'BPS1') + num(len(src)) + num(len(tgt)) + num(0)
    i = 0; n = len(tgt); tpos = [0]; tcur = [0]
    while i < n:
        if i < len(src) and src[i] == tgt[i]:
            j = i
            while j < n and j < len(src) and src[j] == tgt[j]: j += 1
            p += num(((j - i - 1) << 2) | 0)          # SourceRead
        else:
            # Lauf gleicher Bytes (z. B. FF im Erweiterungsbereich): 1 Byte lesen, Rest per TargetCopy
            r = i
            while r < n and tgt[r] == tgt[i] and not (r < len(src) and src[r] == tgt[r]): r += 1
            if r - i >= 16:
                p += num((0 << 2) | 1) + tgt[i:i+1]
                ziel = i - tpos[0]; tpos[0] = r - 1 + 1 - 1   # TargetCopy-Zeiger relativ
                rel = i - tcur[0]
                p += num(((r - i - 2) << 2) | 3) + num((abs(rel) << 1) | (1 if rel < 0 else 0))
                tcur[0] = i + (r - i - 1)
                j = r
            else:
                j = i
                while j < n and not (j < len(src) and src[j] == tgt[j] and j + 8 <= min(n, len(src)) and src[j:j+8] == tgt[j:j+8]):
                    j += 1
                    if j - i > 32 and tgt[j:j+16] == bytes([tgt[j]])*16: break
                p += num(((j - i - 1) << 2) | 1) + tgt[i:j]   # TargetRead
        i = j
    p += zlib.crc32(src).to_bytes(4, 'little') + zlib.crc32(tgt).to_bytes(4, 'little')
    p += zlib.crc32(bytes(p)).to_bytes(4, 'little')
    return bytes(p)
def lies(p, i):
    n = 0; s = 1
    while True:
        x = p[i]; i += 1; n += (x & 0x7F) * s
        if x & 0x80: return n, i
        s <<= 7; n += s
def anwenden(src, p):
    assert p[:4] == b'BPS1'; i = 4
    ss, i = lies(p, i); ts, i = lies(p, i); ms, i = lies(p, i); i += ms
    out = bytearray(); sr = tr = 0
    while i < len(p) - 12:
        d, i = lies(p, i); k = (d >> 2) + 1; a = d & 3
        if a == 0: out += src[len(out):len(out)+k]
        elif a == 1: out += p[i:i+k]; i += k
        else:
            o, i = lies(p, i); o = (-1 if o & 1 else 1) * (o >> 1)
            if a == 2: sr += o; out += src[sr:sr+k]; sr += k
            else:
                tr += o
                for _ in range(k): out.append(out[tr]); tr += 1
    assert zlib.crc32(src) == int.from_bytes(p[-12:-8], 'little'), "falsche Quell-ROM"
    assert zlib.crc32(bytes(out)) == int.from_bytes(p[-8:-4], 'little')
    return bytes(out)
if __name__ == '__main__':
    def ohne_kopf(x): return x[len(x) % 1024:]
    src = ohne_kopf(open(sys.argv[1], 'rb').read()); tgt = ohne_kopf(open(sys.argv[2], 'rb').read())
    p = erstelle(src, tgt); open(sys.argv[3], 'wb').write(p)
    assert anwenden(src, p) == tgt
    print("BPS ok: %d Bytes, Quelle CRC32 %08X, Ziel CRC32 %08X" % (len(p), zlib.crc32(src), zlib.crc32(tgt)))
