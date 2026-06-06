# Mi 8 Lite (xiaomi-platina) — WiFi habilitado

Paquetes para habilitar el WiFi (WCN3990) en el Xiaomi Mi 8 Lite con postmarketOS.

## firmware-xiaomi-platina
Genera el firmware WiFi para ath10k_snoc:
- `firmware-5.bin` — generado con ath10k-fwencoder (genérico, no propietario)
- `board-2.bin` — generado de los board files del dispositivo vía gen-board-2.py
- `wlanmdsp.mbn` — firmware del subsistema WiFi

### Firmware propietario (NO incluido en git)
El `firmware-xiaomi-platina-bdwlan.tar.gz` (board files + wlanmdsp.mbn) se extrae
del propio dispositivo desde `/vendor/firmware_mnt/image/` (requiere root):

    adb shell 'su -c "cp /vendor/firmware_mnt/image/bdwlan* /vendor/firmware_mnt/image/wlanmdsp.mbn /sdcard/fwdump/"'

Luego empaquetar en `bdwlan/` dentro del tarball y `pmbootstrap checksum`.

## device-xiaomi-platina
Añadidas dependencias `soc-qcom-sdm660` + `soc-qcom-sdm660-rproc` (rmtfs/tqftpserv,
necesarios para que el modem levante — sin modem vivo el WiFi WCN3990 no funciona).

## Caveat conocido
Desconectarse del WiFi o salir del rango del AP lo rompe hasta reiniciar
(issue sdm660-mainline #75).
