<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/logo-light.svg">
    <img alt="UniXNU" src="assets/logo-light.svg" width="200">
  </picture>
</p>

<p align="center">
  <a href="https://unixnu.com"><img alt="Documentation" src="https://img.shields.io/badge/docs-unixnu.com-2A5BD7?logo=readthedocs&logoColor=white"></a>
  <a href="https://t.me/unixnu"><img alt="Telegram" src="https://img.shields.io/badge/Telegram-@unixnu-26A5E4?logo=telegram&logoColor=white"></a>
  <a href="https://x.com/unixnu"><img alt="X" src="https://img.shields.io/badge/X-@unixnu-000000?logo=x&logoColor=white"></a>
</p>

# UniXNU-nuwa

Device repository for the Xiaomi 13 Pro (nuwa, SM8550). It holds the board file, kernel defconfig, device scripts, drivers and package.

- [Documentation](https://unixnu.com)
- [Device page](https://unixnu.com/devices/nuwa)
- [Porting guide](https://unixnu.com/porting/)
- [Build](https://unixnu.com/building)

Firmware: [uefi-nuwa](https://github.com/pubglite55/uefi-nuwa).

Build with the `unixnu` driver of [UniXNU](https://github.com/UniXNU/UniXNU). Clone both repositories with `--recurse-submodules`; `unixnu fetch` also updates the module submodules.

## Port status

The boot chain reaches the kernel entry on hardware.

| Stage | State | Notes |
| --- | --- | --- |
| UEFI to BDS | ✅ | SEC keeps ABL's `x0` in a HOB |
| UniXNU boot manager | ✅ | Displayed on the device |
| Payload volume | ✅ | 4 KiB FAT16 volume published from the UFS `boot_b` partition |
| DarwinBoot handoff | ✅ | `Current EL : EL1`, boot services exit, green bar |
| Kernel entry | ✅ | `boot: the kernel entry code` |
| Kernel bring-up | ⚠️ | Stalls after the entry code; no console output yet |

nuwa is a GKI device, so the ABL never loads the `boot_a` ramdisk: `linux,initrd-start` points into the
kernel reservation (0xA8000000 + 256 MB). The payload is therefore published from the UFS `boot_b`
partition, formatted with 4 KiB sectors to match the block device.

## Device support

This table records user-facing device support from the operating system.

| Feature | State | Notes |
| --- | --- | --- |
| Touch | ❌ | FocalTech, no native driver yet |
| Display | ⚠️ | Legacy display runs; the framebuffer is rotated 90 degrees |
| UFS | ⚠️ | Native UFS reads; not the root volume yet |
| Wi-Fi | ❌ | |
| Bluetooth | ❌ | |
| Camera | ❌ | |
| GPU | ❌ | |
| USB | ❌ | |
| Audio | ❌ | |
| Sensors | ❌ | |
| Battery driver | ❌ | |
| Suspend and resume | ❌ | |

✅ available, ⚠️ partial, ❌ not available.

## License

BSD-2-Clause-Patent. See [LICENSE](LICENSE).
