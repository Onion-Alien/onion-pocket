"""Onion Pocket's QR encoder (onion_pocket/qr.py): sizes, the
fixed patterns, the format bits, and, when zxing-cpp happens to be installed, that a
real decoder reads it back."""
import numpy as np
import pytest

from onion_pocket import qr


def _bits(m, cells):
    return sum(int(m[y][x]) << i for i, (x, y) in enumerate(cells))


def _format_copies(m):
    """The 15 format bits, read from both places they're written (x, y order)."""
    s = len(m)
    first = [(8, i) for i in range(6)] + [(8, 7), (8, 8), (7, 8)] + \
        [(14 - i, 8) for i in range(9, 15)]
    second = [(s - 1 - i, 8) for i in range(8)] + [(8, s - 15 + i) for i in range(8, 15)]
    return _bits(m, first), _bits(m, second)


@pytest.mark.parametrize("n, ver", [(1, 1), (14, 1), (15, 2), (26, 2), (106, 6), (107, 7),
                                    (213, 10)])
def test_smallest_version_that_fits(n, ver):
    assert qr.version_for(n) == ver
    m = qr.encode("x" * n)
    assert len(m) == ver * 4 + 17 and all(len(r) == len(m) for r in m)


def test_too_long_is_refused():
    with pytest.raises(ValueError):
        qr.encode("x" * 214)


def test_finders_timing_and_format_bits():
    m = qr.encode("http://pc.example:7475/#k=" + "A" * 32)
    s = len(m)
    ring = [[max(abs(x - 3), abs(y - 3)) != 2 for x in range(7)] for y in range(7)]
    for ox, oy in ((0, 0), (s - 7, 0), (0, s - 7)):
        assert [[m[oy + y][ox + x] for x in range(7)] for y in range(7)] == ring
    assert [m[6][x] for x in range(8, s - 8)] == [x % 2 == 0 for x in range(8, s - 8)]
    assert m[s - 8][8]                                   # the dark module
    a, b = _format_copies(m)
    assert a == b
    raw = a ^ 0x5412
    data, rem = raw >> 10, raw
    for i in range(14, 9, -1):                           # BCH: divides cleanly by 0x537
        if rem >> i & 1:
            rem ^= 0x537 << (i - 10)
    assert rem == 0 and data >> 3 == 0                   # level M, any of the 8 masks


@pytest.mark.parametrize("text", ["A", "http://pc.example:7475/#k=abc-DEF_123",
                                  "héllo 🐰", "x" * 100, "y" * 213])
def test_a_real_decoder_reads_it(text):
    zxingcpp = pytest.importorskip("zxingcpp")
    m = np.array(qr.encode(text))
    img = np.pad(np.where(m, 0, 255).astype(np.uint8), 4, constant_values=255)
    img = np.kron(img, np.ones((4, 4), np.uint8))        # 4 px a module
    found = zxingcpp.read_barcodes(img)
    assert found and found[0].text == text
