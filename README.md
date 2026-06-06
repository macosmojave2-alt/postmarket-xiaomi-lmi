# postmarketOS — Xiaomi POCO F2 Pro / Redmi K30 Pro (xiaomi-lmi)

Paquetes de [pmaports](https://gitlab.com/postmarketOS/pmaports) para portar
**postmarketOS** al Xiaomi POCO F2 Pro / Redmi K30 Pro (`xiaomi-lmi`),
SoC Qualcomm SM8250 (Snapdragon 865), usando **kernel mainline**.

## Paquetes

| Paquete | Descripción |
|---|---|
| [`device-xiaomi-lmi`](device-xiaomi-lmi/) | Device package (deviceinfo, ALSA UCM, udev, firmware nonfree). Ver su [README](device-xiaomi-lmi/README.md). |
| [`firmware-xiaomi-lmi`](firmware-xiaomi-lmi/) | Firmware propietario QCOM (GPU, venus, DSP, sensores). |
| [`linux-postmarketos-qcom-sm8250-lmi`](linux-postmarketos-qcom-sm8250-lmi/) | Kernel mainline 6.19.7 (SM8250). |
| [`linux-xiaomi-lmi`](linux-xiaomi-lmi/) | Kernel downstream 6.16.0 (legacy, fallback). |

## Estado del hardware

✅ Pantalla, GPU (Adreno 650), WiFi, Bluetooth, audio, táctil, batería, USB OTG,
NFC, sensores básicos, cámara parcial.

❌ **Modem (llamadas/SMS/datos), GPS, proximidad y haptics ROTOS** en mainline
(el SDX55m no está soportado upstream). **No usable como teléfono primario.**

Detalle completo en [`device-xiaomi-lmi/README.md`](device-xiaomi-lmi/README.md) y
en el [wiki de postmarketOS](https://wiki.postmarketos.org/wiki/Xiaomi_POCO_F2_Pro_/_Redmi_K30_Pro_(xiaomi-lmi)).

## Firmware propietario

El `firmware-xiaomi-lmi-Tag.zip` (~28 MB) **no está incluido** en este repositorio
por ser firmware propietario. Instrucciones para obtenerlo y colocarlo en el
[README del device package](device-xiaomi-lmi/README.md).

## Build / flasheo

```bash
# Copiar los paquetes a tu pmaports (device/testing/) o usar este como overlay.
pmbootstrap checksum device-xiaomi-lmi
pmbootstrap build device-xiaomi-lmi
pmbootstrap install
pmbootstrap export
fastboot flash boot boot.img
fastboot flash system xiaomi-lmi.img
fastboot reboot
```

## Estado del proyecto

Ver [STATUS.md](STATUS.md).

## Notas de mantenimiento

El kernel se obtiene del fork personal `yuweiyuan8/linux` (tag `v6.19`/`lmi`).
Base mainline de referencia para SM8250: proyecto comunitario
[`sm8250-mainline`](https://github.com/sm8250-mainline).

## Licencia

Recetas de empaquetado: MIT. Firmware: propietario (Xiaomi/Qualcomm), no incluido.
