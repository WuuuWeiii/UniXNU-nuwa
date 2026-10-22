# nuwa (Xiaomi 13 Pro, SM8550) — port status

This repository is a fork of [UniXNU-sheng](https://github.com/UniXNU/UniXNU-sheng) retargeted at
the Xiaomi 13 Pro. sheng is the reference device for SM8550, so the SoC-level parts are reused
unchanged; only the board identity and device-specific values differ.

| Item | Value |
| --- | --- |
| Device | Xiaomi 13 Pro (`nuwa`) |
| SoC | SM8550 / kalama, Adreno 740 |
| Stock firmware | Android 17 (GKI), slot A |
| Target image | iPad7,1 / iPadOS 17.7.11 (21H461), same qualified build as sheng |
| UEFI | `Platforms/Xiaomi/nuwaPkg` in [uefi-nuwa](https://github.com/pubglite55/uefi-nuwa) |
| Panel | `samsung,amb673cp01-m2`, 1440x3200, DSI at `0xae94000` |
| Touch | FocalTech (`fts,*`) — **not** the Novatek part sheng uses |
| userdata | `first_lba` 3110976, `last_lba` 61850618 (224.1 GiB, read from the device GPT) |

## Current state

The boot chain reaches the kernel entry on hardware:

```
ABL → BootShim → UEFI → BDS → UniXNU boot manager
  → Fat attaches NUWAESP → \EFI\UniXNU\unixnu.toml
  → DarwinBoot handoff → EL1 → boot services exit → "boot: the kernel entry code"
```

The kernel then stalls without console output. `panic_screen` is off and there is no wired UART, so
the stall is being narrowed by removing sheng-specific kernel arguments one at a time.

## Payload layout

nuwa is a GKI device: the ABL never loads the `boot_a` ramdisk, and `/chosen` `linux,initrd-start`
points into the kernel reservation (0xA8000000 + 256 MB). The payload is therefore a 4 KiB FAT16
volume written bare into the UFS `boot_b` partition (192 MiB), which Fat attaches as `NUWAESP`.

- `payload.py` formats with `mformat -M 4096 -T size_mib*256` and no `-F`: with 4 KiB sectors the
  image has 48,128 clusters, below the 65,525 that FAT32 requires, so the volume is FAT16.
- Boot memory driver: `mBringUpTouchMemory = FALSE`. Every DRAM access during bring-up
  (GCD scan for the OEM tag, initrd remap) faults on this platform.
- `vbmeta_a` must carry flags `0x3`, otherwise the ABL refuses to start `boot_a`.
- `boot_a` is written with `fastboot flash`; the `boot_b` payload is written with `dd`
  (`fastboot flash:raw` wraps the image in a boot header, which Fat cannot parse).

## What is in here

| File | Note |
| --- | --- |
| `board.toml` | Retargeted from sheng; userdata LBA and payload size are nuwa's own; `serial=3` removed |
| `configs/nuwa_defconfig` | Copy of `sheng_defconfig` as the baseline |
| `scripts/make-nuwa-adt.py` | ADT generator; only the root compatible and product strings differ from sheng's |
| `scripts/check-nuwa.py` | Firmware preflight: FD window, stack PCD and memory map must agree |
| `.github/workflows/stage1-firmware.yml` | Firmware volume + boot image on a Linux runner |
| `.github/workflows/kernel.yml` | XNU kernel + prelink on a macOS runner (Xcode iPhoneOS SDK is required) |

## Known gaps

- The kernel stalls after the entry code; the console is not up yet.
- The framebuffer is rotated 90 degrees (legacy display orientation / unit scale).
- `drivers/NativeNovatekTouch` is inherited from sheng and does not apply to nuwa.
- The touch controller needs a FocalTech driver; nothing here provides one yet.
- `panic_screen` is off because `scripts/patch-xnu-entry-probe.py` hardcodes sheng's kernel
  addresses; it needs the symbols of this kernel.

## Upstream relationship

`sheng` remains upstream. Keep the diff to `board.toml`, `configs/`, `scripts/` and `.github/`
so the SoC-level fixes can be pulled from sheng without conflicts.
