#!/usr/bin/env python3
"""nuwaPkg preflight: are the UEFI platform inputs present and mutually consistent?

Runs as board.toml [firmware] preflight, i.e. from the assembled build tree. The UEFI
checkout is located through UNIXNU_UEFI (the driver's own option) or a few sibling paths.

Hard failures (exit 1) mean the platform parameters disagree with each other, so the build
would produce firmware for a different memory layout:
  * the FD window in Resources/Configs/nuwa.toml vs the "UEFI FD" row of MemoryMapLib.c
  * the stack PCD in nuwa.dsc vs the "UEFI Stack" row of MemoryMapLib.c
  * a missing nuwaPkg input (dsc, fdf, dtb, memmap, config)

Warnings (exit 0) are the known map-vs-devicetree gaps; they do not block the build but are
the first suspects if the DXE stage faults.
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fdt  # noqa: E402

EXPECT_FD = (0xA7100000, 0x300000)      # nuwa: same window as sheng, from the device's own config
EXPECT_STACK = 0xA760D000

MAP_ROW = re.compile(r'\{\s*"([^"]+)"\s*,\s*(0x[0-9a-fA-F]+)\s*,\s*(0x[0-9a-fA-F]+)\s*,\s*([^}]+)\}')


def find_uefi():
    candidates = []
    env = os.environ.get('UNIXNU_UEFI')
    if env:
        candidates.append(Path(env))
    here = Path.cwd()
    for base in (here, *here.parents):
        for name in ('Mu-Silicium', 'uefi-nuwa', 'uefi-sheng'):
            candidates.append(base / name)
    for path in candidates:
        if (path / 'Platforms/Xiaomi/nuwaPkg').is_dir():
            return path
    raise SystemExit('check-nuwa: cannot locate a Mu-Silicium checkout; set UNIXNU_UEFI')


def load_map(path):
    rows = []
    for match in MAP_ROW.finditer(path.read_text(encoding='utf-8', errors='replace')):
        fields = [f.strip() for f in match.group(4).split(',')]
        rows.append({'name': match.group(1), 'base': int(match.group(2), 16),
                     'size': int(match.group(3), 16), 'type': fields[3] if len(fields) > 3 else ''})
    return rows


def dtb_reservations(path):
    out = []
    for node, props in fdt.parse(path.read_bytes()):
        if node.startswith('/reserved-memory/') and 'reg' in props:
            for base, size in fdt.reg_pairs(props['reg']):
                if size:
                    out.append((node.rsplit('/', 1)[-1], base, size))
    return out


def main():
    uefi = find_uefi()
    pkg = uefi / 'Platforms/Xiaomi/nuwaPkg'
    print(f'uefi checkout : {uefi}')

    required = {
        'dsc': pkg / 'nuwa.dsc',
        'fdf': pkg / 'nuwa.fdf',
        'dtb': pkg / 'FdtBlob/sm8550-xiaomi-nuwa.dtb',
        'memmap': pkg / 'Library/MemoryMapLib/MemoryMapLib.c',
        'config': uefi / 'Resources/Configs/nuwa.toml',
    }
    missing = [name for name, path in required.items() if not path.is_file()]
    for name, path in required.items():
        print(f'  {name:<8} {"ok" if path.is_file() else "MISSING"}  {path.relative_to(uefi)}')
    if missing:
        print(f'check-nuwa: FAIL, missing inputs: {", ".join(missing)}')
        return 1

    errors = []
    warnings = []

    config = required['config'].read_text(encoding='utf-8')
    fd_base = re.search(r'\[uefi_fd\][^[]*?base\s*=\s*(0x[0-9a-fA-F]+)', config, re.S)
    fd_size = re.search(r'\[uefi_fd\][^[]*?size\s*=\s*(0x[0-9a-fA-F]+)', config, re.S)
    if not fd_base or not fd_size:
        errors.append('Resources/Configs/nuwa.toml has no [uefi_fd] base/size')
        fd_window = None
    else:
        fd_window = (int(fd_base.group(1), 16), int(fd_size.group(1), 16))

    rows = load_map(required['memmap'])
    by_name = {}
    for row in rows:
        by_name.setdefault(row['name'], row)
    if not rows:
        errors.append('MemoryMapLib.c: no descriptor rows parsed')

    map_fd = by_name.get('UEFI FD')
    map_stack = by_name.get('UEFI Stack')

    if fd_window and map_fd and (map_fd['base'], map_fd['size']) != fd_window:
        errors.append(f"FD window disagrees: config {fd_window[0]:#x}+{fd_window[1]:#x} vs "
                      f"memmap {map_fd['base']:#x}+{map_fd['size']:#x}")
    if fd_window and fd_window != EXPECT_FD:
        errors.append(f'FD window {fd_window[0]:#x}+{fd_window[1]:#x} differs from the nuwa expectation '
                      f'{EXPECT_FD[0]:#x}+{EXPECT_FD[1]:#x}')

    dsc = required['dsc'].read_text(encoding='utf-8', errors='replace')
    stack_pcd = re.search(r'PcdCPUCoresStackBase\|(0x[0-9a-fA-F]+)', dsc)
    if not stack_pcd:
        errors.append('nuwa.dsc has no PcdCPUCoresStackBase')
    else:
        stack = int(stack_pcd.group(1), 16)
        if stack != EXPECT_STACK:
            errors.append(f'stack {stack:#x} differs from the nuwa expectation {EXPECT_STACK:#x}')
        if map_stack and map_stack['base'] != stack:
            errors.append(f"stack disagrees: dsc {stack:#x} vs memmap {map_stack['base']:#x}")

    # map vs device tree: known gaps are warnings, not failures
    reserved = [(r['name'], r['base'], r['size']) for r in rows if 'Reserv' in r['type']]
    for name, base, size in dtb_reservations(required['dtb']):
        if not any(b <= base and base + size <= b + s for _, b, s in reserved):
            warnings.append(f'devicetree reservation not declared in the UEFI map: {name} '
                            f'@ {base:#x}+{size:#x}')
    for index, row in enumerate(rows):
        if not row['size'] or row['base'] % 4096 or row['size'] % 4096:
            errors.append(f"unaligned or empty region: {row['name']}")
        for other in rows[index + 1:]:
            if max(row['base'], other['base']) < min(row['base'] + row['size'],
                                                    other['base'] + other['size']):
                errors.append(f"overlap: {row['name']} <-> {other['name']}")

    for key in ('UEFI FD', 'UEFI Stack', 'Display Reserved'):
        row = by_name.get(key)
        if row:
            print(f'  {key:<18} {row["base"]:#010x} + {row["size"]:#x}')
        else:
            warnings.append(f'memmap has no "{key}" row')

    if warnings:
        print(f'\n{len(warnings)} warning(s) -- known and non-blocking:')
        for item in warnings:
            print('  !', item)
    if errors:
        print(f'\ncheck-nuwa: FAIL, {len(errors)} inconsistency(ies):')
        for item in errors:
            print('  -', item)
        return 1
    print('\ncheck-nuwa: OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
