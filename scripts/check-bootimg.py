#!/usr/bin/env python3
"""Validate an Android boot image, for header versions 0 through 4.

`unixnu bootimg` verifies its own output, but that check assumes the v0 field
layout: for v3/v4 it reads `reserved` as `second_size` and refuses a correct
image ("boot image header does not match the requested parameters"). nuwa's ABL
only accepts v3+, so the image is good and the check is wrong.

  python3 scripts/check-bootimg.py out/nuwa/boot/boot.img
"""
import struct
import sys
from pathlib import Path

ALIGN = 4096


def align(size, page):
    return ((size + page - 1) // page) * page


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    data = Path(argv[1]).read_bytes()
    if data[:8] != b'ANDROID!':
        raise SystemExit('not an Android boot image')
    version = struct.unpack_from('<I', data, 40)[0]
    kernel_size = struct.unpack_from('<I', data, 8)[0]
    # v0-v2 put kernel_addr between the two sizes; v3+ keep them adjacent.
    ramdisk_size = struct.unpack_from('<I', data, 12 if version >= 3 else 16)[0]
    page = ALIGN

    header_size = 1632
    second_size = struct.unpack_from('<I', data, 24)[0] if version <= 2 else 0
    recovery_dtbo_size = 0
    dtb_size = 0
    if version in (1, 2):
        header_size = struct.unpack_from('<I', data, 1644)[0]
        recovery_dtbo_size = struct.unpack_from('<I', data, 1632)[0]
    elif version in (3, 4):
        header_size = struct.unpack_from('<I', data, 20)[0]
    if version == 2:
        dtb_size = struct.unpack_from('<Q', data, 1648)[0]

    expected = page + align(kernel_size, page) + align(ramdisk_size, page) \
        + align(second_size, page) + align(recovery_dtbo_size, page) + align(dtb_size, page)

    kernel = data[page:page + kernel_size]
    print(f'file            : {len(data)} bytes')
    print(f'header_version  : {version} (header {header_size} bytes)')
    print(f'kernel          : {kernel_size} bytes, first bytes {kernel[:4].hex()}')
    print(f'ramdisk         : {ramdisk_size} bytes')
    print(f'expected total  : {expected}')

    problems = []
    gzipped = kernel[:3] == b'\x1f\x8b\x08'
    flattened = kernel[:4] == b'\xd0\x0d\xfe\xed'          # gzip'd Image + appended DTB
    raw_arm64 = len(kernel) > 60 and kernel[56:60] == b'ARM\x64'
    if not (gzipped or flattened or raw_arm64):
        problems.append(f'kernel is neither gzip, FDT nor a raw ARM64 Image ({kernel[:4].hex()})')
    # Images are padded to the partition, so only an undersized file is wrong.
    if len(data) < expected:
        problems.append(f'truncated: file {len(data)} < expected {expected}')
    if version < 3:
        problems.append(f'header v{version}: nuwa ABL rejected v0/v1 in practice, v3 is what boots')

    if problems:
        print('\nFAIL')
        for item in problems:
            print('  -', item)
        return 1
    print('\nOK: structure is consistent and the header version is usable on nuwa')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
