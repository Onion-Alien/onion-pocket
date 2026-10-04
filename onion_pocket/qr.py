"""QR codes, drawn in code: Onion Pocket's pairing link (Settings → Remote) is
shown as one so a phone can scan it instead of typing a key.

Byte mode, error correction level M, versions 1 to 10 (up to 213 bytes: a link with
a key is under 100). Built from the QR spec (ISO/IEC 18004): data and Reed-Solomon
codewords in interleaved blocks, the function patterns, the zigzag placement, and the
mask with the lowest penalty.

    m = encode("http://example.com/")   # list of rows, True = dark
"""
from __future__ import annotations

# level M, per version 1..10 (index 0 unused): error-correction codewords per block,
# and how many blocks
_ECC_PER_BLOCK = (0, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26)
_BLOCKS = (0, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5)
_FORMAT_M = 0          # level M's two format bits
MAX_VERSION = 10

# GF(256) with the QR polynomial x^8 + x^4 + x^3 + x^2 + 1
_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _mul(a: int, b: int) -> int:
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def _rs_divisor(degree: int) -> list[int]:
    """The generator polynomial's coefficients, highest first, leading 1 left out."""
    out = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for j in range(degree):
            out[j] = _mul(out[j], root)
            if j + 1 < degree:
                out[j] ^= out[j + 1]
        root = _mul(root, 2)
    return out


def _rs_remainder(data: list[int], divisor: list[int]) -> list[int]:
    out = [0] * len(divisor)
    for b in data:
        factor = b ^ out.pop(0)
        out.append(0)
        for i, c in enumerate(divisor):
            out[i] ^= _mul(c, factor)
    return out


def _raw_modules(ver: int) -> int:
    """Modules left for data and error correction once the function patterns are in."""
    n = (16 * ver + 128) * ver + 64
    if ver >= 2:
        align = ver // 7 + 2
        n -= (25 * align - 10) * align - 55
        if ver >= 7:
            n -= 36
    return n


def _data_capacity(ver: int) -> int:
    """Data codewords at level M."""
    return _raw_modules(ver) // 8 - _ECC_PER_BLOCK[ver] * _BLOCKS[ver]


def _codewords(data: bytes, ver: int) -> list[int]:
    """Mode, length, data, padding; split into blocks, error correction added,
    interleaved."""
    bits: list[int] = []

    def put(value: int, n: int):
        bits.extend((value >> i) & 1 for i in reversed(range(n)))

    put(0b0100, 4)                                   # byte mode
    put(len(data), 8 if ver <= 9 else 16)
    for b in data:
        put(b, 8)
    cap = _data_capacity(ver) * 8
    put(0, min(4, cap - len(bits)))                  # terminator
    put(0, -len(bits) % 8)
    pad = 0xEC
    while len(bits) < cap:
        put(pad, 8)
        pad ^= 0xEC ^ 0x11
    words = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]

    blocks, ecc = _BLOCKS[ver], _ECC_PER_BLOCK[ver]
    raw = _raw_modules(ver) // 8
    short = blocks - raw % blocks                    # these blocks hold one byte less
    short_len = raw // blocks - ecc
    divisor = _rs_divisor(ecc)
    data_blocks, ecc_blocks, k = [], [], 0
    for i in range(blocks):
        n = short_len + (0 if i < short else 1)
        block = words[k:k + n]
        k += n
        data_blocks.append(block)
        ecc_blocks.append(_rs_remainder(block, divisor))
    out = []
    for i in range(short_len + 1):
        out.extend(b[i] for b in data_blocks if i < len(b))
    for i in range(ecc):
        out.extend(b[i] for b in ecc_blocks)
    return out


def _alignment_positions(ver: int) -> list[int]:
    if ver == 1:
        return []
    n = ver // 7 + 2
    size = ver * 4 + 17
    step = (ver * 4 + n * 2 + 1) // (n * 2 - 2) * 2
    return [6] + sorted(size - 7 - i * step for i in range(n - 1))


class _Grid:
    def __init__(self, ver: int):
        self.ver = ver
        self.size = ver * 4 + 17
        self.dark = [[False] * self.size for _ in range(self.size)]
        self.fixed = [[False] * self.size for _ in range(self.size)]

    def set(self, x: int, y: int, dark: bool):
        self.dark[y][x] = dark
        self.fixed[y][x] = True

    def function_patterns(self):
        s = self.size
        for i in range(s):                           # timing
            self.set(6, i, i % 2 == 0)
            self.set(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (s - 4, 3), (3, s - 4)):   # finders, with separators
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < s and 0 <= y < s:
                        self.set(x, y, max(abs(dx), abs(dy)) not in (2, 4))
        pos = _alignment_positions(self.ver)
        last = len(pos) - 1
        for i, ax in enumerate(pos):
            for j, ay in enumerate(pos):
                if (i, j) in ((0, 0), (0, last), (last, 0)):
                    continue                         # under a finder
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self.set(ax + dx, ay + dy, max(abs(dx), abs(dy)) != 1)
        self.format_bits(0)                          # reserve; the real mask comes later
        if self.ver >= 7:
            rem = self.ver
            for _ in range(12):
                rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
            bits = self.ver << 12 | rem
            for i in range(18):
                bit = (bits >> i) & 1 == 1
                a, b = s - 11 + i % 3, i // 3
                self.set(a, b, bit)
                self.set(b, a, bit)

    def format_bits(self, mask: int):
        data = _FORMAT_M << 3 | mask
        rem = data
        for _ in range(10):
            rem = (rem << 1) ^ ((rem >> 9) * 0x537)
        bits = (data << 10 | rem) ^ 0x5412
        s = self.size

        def bit(i):
            return (bits >> i) & 1 == 1
        for i in range(6):
            self.set(8, i, bit(i))
        self.set(8, 7, bit(6))
        self.set(8, 8, bit(7))
        self.set(7, 8, bit(8))
        for i in range(9, 15):
            self.set(14 - i, 8, bit(i))
        for i in range(8):
            self.set(s - 1 - i, 8, bit(i))
        for i in range(8, 15):
            self.set(8, s - 15 + i, bit(i))
        self.set(8, s - 8, True)                     # the dark module

    def place(self, words: list[int]):
        s, i, n = self.size, 0, len(words) * 8
        right = s - 1
        while right >= 1:
            if right == 6:                           # skip the vertical timing line
                right = 5
            upward = (right + 1) & 2 == 0
            for vert in range(s):
                y = s - 1 - vert if upward else vert
                for x in (right, right - 1):
                    if not self.fixed[y][x] and i < n:
                        self.dark[y][x] = (words[i >> 3] >> (7 - (i & 7))) & 1 == 1
                        i += 1
            right -= 2

    def apply_mask(self, mask: int):
        test = _MASKS[mask]
        for y in range(self.size):
            row, fixed = self.dark[y], self.fixed[y]
            for x in range(self.size):
                if not fixed[x] and test(x, y):
                    row[x] = not row[x]

    def penalty(self) -> int:
        s, m, score = self.size, self.dark, 0
        lines = m + [[m[y][x] for y in range(s)] for x in range(s)]
        for line in lines:
            run, prev = 0, None
            for v in line:                           # rule 1: runs of five or more
                if v == prev:
                    run += 1
                    if run == 5:
                        score += 3
                    elif run > 5:
                        score += 1
                else:
                    run, prev = 1, v
            text = "".join("1" if v else "0" for v in line)
            for pat in ("00001011101", "10111010000"):   # rule 3: finder look-alikes
                score += 40 * _count(text, pat)
        for y in range(s - 1):                       # rule 2: 2x2 blocks
            for x in range(s - 1):
                v = m[y][x]
                if v == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                    score += 3
        dark = sum(map(sum, m))                      # rule 4: balance
        total = s * s
        k = (abs(dark * 20 - total * 10) + total - 1) // total - 1
        return score + max(k, 0) * 10


def _count(text: str, pat: str) -> int:
    n, i = 0, text.find(pat)
    while i >= 0:
        n += 1
        i = text.find(pat, i + 1)
    return n


_MASKS = (
    lambda x, y: (x + y) % 2 == 0,
    lambda x, y: y % 2 == 0,
    lambda x, y: x % 3 == 0,
    lambda x, y: (x + y) % 3 == 0,
    lambda x, y: (x // 3 + y // 2) % 2 == 0,
    lambda x, y: x * y % 2 + x * y % 3 == 0,
    lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
    lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0,
)


def version_for(n: int) -> int:
    """The smallest version that holds n bytes; ValueError if none does."""
    for ver in range(1, MAX_VERSION + 1):
        if 4 + (8 if ver <= 9 else 16) + n * 8 <= _data_capacity(ver) * 8:
            return ver
    raise ValueError(f"too long for a QR code here ({n} bytes)")


def encode(text: str) -> list[list[bool]]:
    """The QR code for `text` (UTF-8), as rows of modules, True = dark. No quiet zone:
    leave four modules of light around it when drawing."""
    data = text.encode("utf-8")
    ver = version_for(len(data))
    grid = _Grid(ver)
    grid.function_patterns()
    grid.place(_codewords(data, ver))
    best, best_score = 0, None
    for mask in range(8):
        grid.apply_mask(mask)
        grid.format_bits(mask)
        score = grid.penalty()
        if best_score is None or score < best_score:
            best, best_score = mask, score
        grid.apply_mask(mask)                        # undo (a mask is its own inverse)
    grid.apply_mask(best)
    grid.format_bits(best)
    return grid.dark
