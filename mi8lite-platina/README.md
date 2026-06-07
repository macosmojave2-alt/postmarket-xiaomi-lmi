# Mi 8 Lite (xiaomi-platina) — WiFi en postmarketOS mainline

Paquetes para habilitar el WiFi (Qualcomm WCN3990) y el modem (MSS) en el
Xiaomi Mi 8 Lite (SDM660) con postmarketOS, kernel mainline
`linux-postmarketos-qcom-sdm660` (6.17.4).

## Estado actual

- ✅ **`wlan0` aparece** y el firmware WiFi carga (api 5, htt-ver 3.50, hwcrypto).
- ✅ Devicetree habilita `&wifi` y `&remoteproc_mss`.
- ✅ Firmware del modem (mba.mbn + modem.mdt + segmentos) se carga sin error.
- ✅ El MSS (modem) arranca (`remote processor ... is now up`).
- ⚠️ **Issue conocido:** el MSS crashea en bucle (`Task starvation: diag`,
  luego `EX:wlan_process`), lo que desestabiliza el WiFi (los scans fallan con
  `-108 / socket shutdown`). El board file reporta `crc32 00000000` cuando el
  MSS está caído. Pendiente de estabilizar.

## Componentes

### linux-postmarketos-qcom-sdm660 + 0001-platina-wifi.patch
Patch del devicetree (`sdm660-xiaomi-platina.dts`):
- `&wifi`: status=okay + 4 regulators (vdd-0.8-cx-mx, vdd-1.8-xo, vdd-1.3-rfa, vdd-3.3-ch0).
- `&remoteproc_mss`: status=okay + `firmware-name = "postmarketos/mba.mbn", "postmarketos/modem.mdt"`.

Ambos nodos existen en `sdm630.dtsi` pero vienen `disabled`.

### firmware-xiaomi-platina
- `firmware-5.bin` — genérico, generado con ath10k-fwencoder (no propietario).
- `board-2.bin` — generado de los board files (`bdwlan.*`) del dispositivo vía `gen-board-2.py`.
- `wlanmdsp.mbn` — firmware del subsistema WiFi.
- `mba.mbn` + `modem.mdt` + `modem.b*` — firmware del modem MSS, en `/lib/firmware/postmarketos/`.

#### GOTCHA del board-2.bin (importante)
ath10k construye el nombre del board file con `qmi-board-id=%x` (**hexadecimal**).
El chip del platina reporta `qmi-board-id=ff` (OTP sin programar), así que el
board-2.bin necesita un entry `bus=snoc,qmi-board-id=ff`. Además, en `bdwlan.bXX`
el board-id es **XX** (sin la "b" inicial): `bdwlan.b33` → `qmi-board-id=33`,
`bdwlan.102` → `qmi-board-id=102`. (Verificado contra el board-2.bin de lavender,
mismo WCN3990+SDM660, que usa `33`/`102`/`ff`.)

### device-xiaomi-platina
Dependencias `soc-qcom-sdm660` + `soc-qcom-sdm660-rproc` (rmtfs/tqftpserv/diag-router).
Sin rmtfs (que con `-s` enciende el MSS) + diag-router, el WiFi WCN3990 no funciona.

## Firmware propietario (NO incluido en git)
Los board files y firmware del modem se extraen del **propio dispositivo**:
- WiFi (`bdwlan.*`, `wlanmdsp.mbn`): de `/vendor/firmware_mnt/image/` (con root, vía adb).
- Modem (`mba.mbn`, `modem.*`, `adsp.*`, `cdsp.*`): de la partición `modem`
  (`/dev/disk/by-partlabel/modem`, montada vfat). NOTA: hacer dd de esta
  partición corrompe la FAT; mejor copiar los archivos montándola viva.

Se empaquetan como `firmware-xiaomi-platina-bdwlan.tar.gz` y
`firmware-xiaomi-platina-modem.tar.gz` (gitignored), luego `pmbootstrap checksum`.

## Instalación (GOTCHA de storage)
Instalar con el layout combinado (GPT anidado dentro de userdata de 52GB)
**corrompe el GPT/ext4 en cada boot**. Usar:

    pmbootstrap install --split --password XXXX
    fastboot flash userdata ~/.local/var/pmbootstrap/chroot_native/home/pmos/rootfs/xiaomi-platina-root.img
    pmbootstrap flasher flash_kernel
    pmbootstrap flasher flash_vbmeta

El `flasher fastboot` de pmbootstrap no soporta `--split`, por eso el rootfs
(ext4 plano) se flashea manual a `userdata`.

## Notas
- pantalla NO funciona en mainline (kernel solo para desarrollo); el kernel
  downstream (LineageOS) tiene pantalla.
- Caveat sdm660-mainline #75: salir de rango del AP rompe el WiFi hasta reiniciar.
