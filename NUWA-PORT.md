# nuwa (Xiaomi 13 Pro, SM8550) — port status

This repository is a fork of [UniXNU-sheng](https://github.com/UniXNU/UniXNU-sheng) retargeted at
the Xiaomi 13 Pro. sheng is the reference device for SM8550, so the SoC-level parts are reused
unchanged; only the board identity and device-specific values differ.

| Item | Value |
| --- | --- |
| Device | Xiaomi 13 Pro (`nuwa`) |
| SoC | SM8550 / kalama, Adreno 740 |
| Stock firmware | Android 13, Linux 5.15 (MIUI 14 generation) |
| Target image | iPad7,1 / iPadOS 17.7.11 (21H461), same qualified build as sheng |
| UEFI | `Platforms/Xiaomi/nuwaPkg` in [Mu-Silicium](https://github.com/Project-Silicium/Mu-Silicium) |
| Panel | `samsung,amb673cp01-m2`, 1440x3200, DSI at `0xae94000` |
| Touch | FocalTech (`fts,*`) — **not** the Novatek part sheng uses |

## What is in here

| File | Note |
| --- | --- |
| `board.toml` | Retargeted from sheng; four `TODO(必改)` remain (userdata LBA, dram size, touch, payload size) |
| `configs/nuwa_defconfig` | Copy of `sheng_defconfig` as the baseline |
| `scripts/make-nuwa-adt.py` | ADT generator; only the root compatible and product strings differ from sheng's |
| `scripts/check-nuwa.py` | Firmware preflight: FD window, stack PCD and memory map must agree |
| `.github/workflows/stage1-firmware.yml` | Firmware volume + boot image on a Linux runner |
| `.github/workflows/kernel.yml` | XNU kernel + prelink on a macOS runner (Xcode iPhoneOS SDK is required) |

## Known gaps

- `[userdata] first_lba / last_lba` in `board.toml` are still sheng's placeholder values.
- `[payload] size_mib = 192` does not fit nuwa's 96 MiB `vendor_boot`; decide the layout before flashing.
- `drivers/NativeNovatekTouch` is inherited from sheng and does not apply to nuwa.
- The touch controller needs a FocalTech driver; nothing here provides one yet.

## Upstream relationship

`sheng` remains upstream. Keep the diff to `board.toml`, `configs/`, `scripts/` and `.github/`
so the SoC-level fixes can be pulled from sheng without conflicts.
