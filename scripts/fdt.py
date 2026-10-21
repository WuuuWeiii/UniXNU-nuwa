"""Minimal flattened-device-tree reader (no dtc / fdtget needed, works on Windows).

Shared by scripts/dump-dtb.py and scripts/check-nuwa-memmap.py.
"""
import struct

FDT_MAGIC = 0xD00DFEED
FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_END = 9


def parse(blob):
    """Return [(path, {prop_name: raw_bytes}), ...] in document order."""
    magic, _totalsize, off_struct, off_strings = struct.unpack('>IIII', blob[:16])
    if magic != FDT_MAGIC:
        raise ValueError('not a flattened device tree (bad magic)')
    size_strings = struct.unpack('>I', blob[32:36])[0]
    strings = blob[off_strings:off_strings + size_strings]

    def cstr(buf, off):
        end = buf.index(b'\0', off)
        return buf[off:end].decode('latin-1')

    pos = off_struct
    stack = []
    nodes = []
    while True:
        token = struct.unpack('>I', blob[pos:pos + 4])[0]
        pos += 4
        if token == FDT_BEGIN_NODE:
            name = cstr(blob, pos)
            pos += (len(name) + 4) & ~3
            stack.append(name)
            nodes.append(('/' + '/'.join(p for p in stack if p), {}))
        elif token == FDT_END_NODE:
            stack.pop()
        elif token == FDT_PROP:
            length, nameoff = struct.unpack('>II', blob[pos:pos + 8])
            pos += 8
            value = blob[pos:pos + length]
            pos += (length + 3) & ~3
            nodes[-1][1][cstr(strings, nameoff)] = value
        elif token == FDT_END:
            break
        else:
            raise ValueError('unsupported FDT token 0x%x' % token)
    return nodes


def cells(value):
    """Decode a property of 32-bit cells into a list of ints."""
    return list(struct.unpack('>%dI' % (len(value) // 4), value[:len(value) // 4 * 4]))


def string(value):
    return value.rstrip(b'\0').decode('latin-1')


def decode(value):
    """Human-readable form used by the dumper."""
    if not value:
        return '<empty>'
    text_ok = all(0x20 <= c < 0x7f or c == 0 for c in value[:-1]) and value.endswith(b'\0')
    if text_ok:
        return repr(string(value))
    if len(value) % 4 == 0 and len(value) <= 64:
        return ' '.join('<0x%x>' % c for c in cells(value))
    return '<%d bytes> %s' % (len(value), value[:16].hex())


def reg_pairs(value):
    """Parse a reg property assuming 2 address cells + 2 size cells."""
    words = cells(value)
    out = []
    for i in range(0, len(words) - 3, 4):
        base = (words[i] << 32) | words[i + 1]
        size = (words[i + 2] << 32) | words[i + 3]
        out.append((base, size))
    return out
