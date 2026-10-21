#!/usr/bin/env python3
"""Materialise the IOKit storage headers the arm-driver archives compile against.

NativeUfs / NativeVirtioBlock / NativeRamBlock subclass IOBlockStorageDevice. That class
no longer ships in the source-kernel SDK: it lives in Apple's separate IOStorageFamily
project (the header was removed from xnu's iokit/IOKit/storage/ at some Darwin 23 point,
leaving only an IOKitUser forwarding header that points at DriverKit). The arm-driver
scripts therefore add -I build/storage-abi/include, and this script produces that tree:

  * the IOStorageFamily root headers, pinned to the Darwin 23 revision the storage ABI was
    qualified against (scripts/audit-storage-interface.py pins the same commit), fetched from
    raw.githubusercontent.com (a CDN, not the rate-limited api.github.com), and
  * TargetConditionals.h from the macOS SDK, the platform-selection header those headers
    include but the kernel fakeroot does not ship.

The output only needs the headers; it is a compile-only shim, never linked or executed.
"""
import shutil
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'e45fbe30a7879e0b16e26dddb78538f1b00e0bff'
BASE = f'https://raw.githubusercontent.com/apple-oss-distributions/IOStorageFamily/{REVISION}'

# Every root header of IOStorageFamily at the pinned revision, minus the kext shim
# (IOUserBlockStorageDevice_kext.h) which drags in the DriverKit IOUserBlockStorageDevice
# interface that the kernel build does not have. NativeUfs only reaches
# IOBlockStorageDevice.h -> IOMedia.h/IOStorage.h -> IOStorage*Characteristics.h.
HEADERS = [
    'IOAppleLabelScheme.h',
    'IOApplePartitionScheme.h',
    'IOBlockStorageDevice.h',
    'IOBlockStorageDriver.h',
    'IOBlockStoragePerfControlExports.h',
    'IOFDiskPartitionScheme.h',
    'IOFilterScheme.h',
    'IOGUIDPartitionScheme.h',
    'IOMedia.h',
    'IOMediaBSDClient.h',
    'IOPartitionScheme.h',
    'IORequest.h',
    'IORequestsPool.h',
    'IOStorage.h',
    'IOStorageCardCharacteristics.h',
    'IOStorageControllerCharacteristics.h',
    'IOStorageDeviceCharacteristics.h',
    'IOStorageProtocolCharacteristics.h',
]

out = ROOT / 'build/storage-abi'
dest = out / 'include/IOKit/storage'
dest.mkdir(parents=True, exist_ok=True)

for name in HEADERS:
    target = dest / name
    url = f'{BASE}/{name}'
    with urllib.request.urlopen(url, timeout=60) as response:
        target.write_bytes(response.read())

sdk = Path(subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], text=True).strip())
shutil.copyfile(sdk / 'usr/include/TargetConditionals.h', out / 'include/TargetConditionals.h')

print(f'storage-abi: {len(HEADERS)} IOStorageFamily headers + TargetConditionals.h -> {dest.parent}')
