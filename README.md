# MHI2Q Facelift Display – 10,1" ohne Decoder

Software-Patch für die **Audi MMI MHI2Q** (Q5 FY, A4/A5 B9 – getestet: Q5 FY 2019, Firmware **P5092 / SW 1329**),
damit das **10,1"-Facelift-Display** (80A919620, LG LPM101G235A, 1540×720) **direkt, ohne Decoder** läuft.

*English summary below.*

## Was funktioniert
- HMI in nativer Auflösung 1540×720, formatfüllend und scharf
- Apple CarPlay im Vollbild (1536×720), auch Wireless CarPlay
- Rückfahrkamera / Top View korrekt skaliert
- Startanimation im Vollbild
- Kein Zittern, keine Bildfehler (siehe [docs/TECHNICAL.md](docs/TECHNICAL.md))

## ⚠️ Wichtig – bitte lesen
- **Auf eigenes Risiko.** Du schreibst in Boot-Partitionen. Ein Fehler kann die Unit unbrauchbar machen.
- Du brauchst **Root-Zugang per SSH** auf die Unit.
- **Kein Firmware-Download hier.** Dieses Repo enthält nur Skripte. Sie patchen **deinen eigenen Dump**.
- Die Skripte prüfen die Eingabe per Prüfsumme und **brechen ab**, wenn deine Firmware nicht exakt der getesteten entspricht.
- Erst am Prüfstand testen, dann ins Auto.

## Voraussetzungen
- MHI2Q mit Firmware P5092 / SW 1329 (andere Stände: Prüfsummen weichen ab → Skript bricht ab)
- Root-SSH (z. B. per USB-LAN-Adapter, Unit unter `172.16.250.248`)
- PC mit Python 3
- Optional: Wireless CarPlay + AltScreen (der CarPlay-Patch liegt dann im AltScreen-Overlay)

## Ablauf

### 1. Backup auf der Unit
```sh
mkdir -p /mnt/ota/backup
dd if=/dev/emmc/mifs of=/mnt/ota/backup/mifs.img bs=1048576
dd if=/dev/emmc/ifs2 of=/mnt/ota/backup/ifs2.img bs=1048576
cp /mnt/app/eso/bin/apps/dio_manager /mnt/ota/backup/dio_manager.orig   # bzw. .../stock/dio_manager bei AltScreen
cksum /mnt/ota/backup/*
```
Erwartet: `mifs.img 4082701332 10485760`, `ifs2.img 2802035159 104857600`, `dio_manager.orig 1446556070 691203`.
**Weicht etwas ab: nicht weitermachen.**

### 2. Backups auf den PC holen und Images bauen
```sh
scp ... root@172.16.250.248:/mnt/ota/backup/{mifs.img,ifs2.img,dio_manager.orig} .
python3 tools/build_mifs.py mifs.img mifs_facelift.img
python3 tools/build_ifs2.py ifs2.img ifs2_facelift_head.img
python3 tools/patch_dio_manager.py dio_manager.orig dio_manager_facelift
```
Jedes Skript gibt am Ende `OK` mit Prüfsumme aus. Ergebnis:
`mifs_facelift.img 1799675391`, `ifs2_facelift_head.img 277332389`, `dio_manager_facelift 2811786567`.

> Alte OpenSSH-Optionen für die Unit (Windows PowerShell):
> `-O -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa -o MACs=+hmac-sha1 -o KexAlgorithms=+diffie-hellman-group14-sha1,diffie-hellman-group1-sha1 -o Ciphers=+aes128-cbc,aes256-cbc`

### 3. Hochladen und flashen
Dateien nach `/mnt/ota/backup/` kopieren, dann auf der Unit (Zündung/Strom an lassen!):
```sh
cd /mnt/ota/backup
dd if=mifs_facelift.img of=/dev/emmc/mifs bs=1048576
dd if=/dev/emmc/mifs bs=1048576 count=10 | cksum          # 1799675391 10485760
dd if=ifs2_facelift_head.img of=/dev/emmc/ifs2 bs=1048576
dd if=/dev/emmc/ifs2 bs=1048576 count=39 | cksum          # 277332389 40894464
```
Stimmt eine Prüfsumme nicht: **nicht neu starten**, sondern das Original zurückschreiben.

### 4. CarPlay-Patch
Ohne AltScreen: `dio_manager_facelift` als `/mnt/app/eso/bin/apps/dio_manager` einsetzen.
Mit AltScreen (Overlay), Zeitstempel des Wrappers übernehmen, sonst überschreibt AltScreen den Patch beim Start:
```sh
S=/mnt/ota/altscreen/root/mnt/app/eso/bin/apps/stock
cp /mnt/ota/backup/dio_manager_facelift $S/dio_manager.new
chmod 755 $S/dio_manager.new
touch -r /mnt/ota/altscreen/root/mnt/app/eso/bin/apps/dio_manager $S/dio_manager.new
mv -f $S/dio_manager.new $S/dio_manager
```

### 5. Startanimation (falls schwarz)
Liegt in `/mnt/persist/var/splash.canim` nur der 40-Byte-Platzhalter, die passende Animation zurückkopieren:
```sh
ls /mnt/app/eso/hmi/splashscreen/
cp /mnt/app/eso/hmi/splashscreen/Q5_quattro_NavigationPlus.canim /mnt/persist/var/splash.canim
```

### 6. Neustart
Zündung aus/an oder Affengriff.

## Zurück zum Original
```sh
dd if=/mnt/ota/backup/mifs.img of=/dev/emmc/mifs bs=1048576
dd if=/mnt/ota/backup/ifs2.img of=/dev/emmc/ifs2 bs=1048576
```
plus den Original-`dio_manager` zurückkopieren.

---

## English summary
Software-only patch for the Audi **MHI2Q** head unit (tested: Q5 FY 2019, firmware P5092 / SW 1329) to drive the
**10.1" facelift display** (80A919620, LG LPM101G235A, 1540×720) **without a decoder box**: native-resolution HMI,
full-screen CarPlay (1536×720), scaled rear-view camera and full-screen startup animation.

The repo contains **only scripts**. They patch **your own** firmware dumps (`mifs`, `ifs2`, `dio_manager`) and refuse
to run if the input checksum does not match the tested firmware. No Audi/Harman/Qualcomm binaries are distributed.
Use at your own risk; always keep backups. Technical details: [docs/TECHNICAL.md](docs/TECHNICAL.md).
