# Technical notes

## Hardware path
MHI2Q (Qualcomm APQ8064, QNX 6.5) → HDMI → **DS90UH929Q** serializer (`/dev/i2c4`, 0x1a) → FPD-Link III →
display deserializer/TCON → LG LPM101G235A panel (1540×720).
Display config: `qcdisplaycfg_MMX2.xml` (ifs2 → `ifs_display.img`), Screen config: `graphics.conf` (mifs).

## Panel timing (display ID 4)
| | value |
|---|---|
| H active / FP / sync / BP | 1540 / 52 / 8 / 104 → **H total 1704** |
| V active / FP / sync / BP | 720 / 36 / 4 / 6 → **V total 766** |
| pixel clock | 78.316 MHz @ 60 Hz |

Findings:
- The panel positions the image from the sync pulses: **HPW+HBP must be 112**, otherwise the picture shifts
  horizontally (garbage stripe at the right edge). **VPW+VBP = 10** puts the bottom status bar fully on screen.
- The panel TCON expects an **H total of ~1703** (value found in the MIB3 display firmware, variant B:
  H total 1703, V total 766). Any other H total makes the TCON drop/duplicate a few lines once per frame →
  a fixed horizontal "cut" line whose position depends on H total (e.g. 1692 → row ~285, 1668 → row ~66).
  1703 (odd) causes jitter on the HDMI path; **1704 is clean**.
- Pixel clock and V total do not affect the line position; H total does.

## displaymanager.json (ifs2 → `ifs_coreservices3.img`)
- Main display `LVDS1`: `"width" : 2316, "height" : 1080, "scale_mode" : "free"` → HMI full screen.
- RVC target `0, 56, 720×384` → `0, 84, 1083×576`; TopView (zfas) target `1024×480` → `1540×720`
  (camera/TopView are hardware overlays and are not affected by the HMI scaling).

## Startup animation (`libdm_modAnim.so`)
- Plays `/var/splash.canim` (= `/mnt/persist/var/splash.canim`, zlib, header `ANIM1`, 1024×480).
- If the unit ran on a bench without vehicle data, the HMI may leave the 40-byte placeholder
  `animated_black_800_480.canim` there → animation ends immediately.
- `CStartupAnimModule::initWindow(w,h)` creates the window/buffer/viewport at the animation size.
  Patch: `0x258c movw r9,#1540`, `0x2594 movw r11,#720` → window, buffer and GL viewport are 1540×720,
  the animation keeps rendering in its own 1024×480 coordinates and is scaled by the viewport.

## CarPlay (`dio_manager`)
START_CARPLAY resolution setup at vaddr `0x1676cc` (file offset `0x676cc`), object at `[r7+0xe8]`:
`+0x224/+0x228` resolution sent to the iPhone, `+0x22c/+0x230` window size. Patched to 1536×720 for both.
1540 is not a multiple of 16 and makes video artefacts worse.

## IFS tooling
- `ifs2` is loaded by `ifsloader -i ifs2 -m /` without signature check; nested images are LZO-compressed QNX IFS.
- `tools/lzo.py` / `tools/lzoc.py`: LZO1X decompressor / compressor; `tools/ifstool.py`: imagefs parsing.
- Only changed 64 KiB blocks are recompressed; all imagefs/startup checksums are recomputed.
- `mifs` (graphics.conf) is patched in place on literal bytes so the compressed size stays identical.
