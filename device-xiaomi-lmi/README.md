# device-xiaomi-lmi — Xiaomi POCO F2 Pro / Redmi K30 Pro

Mainline port (kernel `linux-postmarketos-qcom-sm8250-lmi`, SoC Qualcomm SM8250 / Snapdragon 865).

## Estado del hardware

Fuente: [wiki postmarketOS](https://wiki.postmarketos.org/wiki/Xiaomi_POCO_F2_Pro_/_Redmi_K30_Pro_(xiaomi-lmi))

### Funciona
- Pantalla (60 Hz, brillo), táctil
- Aceleración 3D (Adreno 650, requiere firmware a650 + a650-zap)
- WiFi (qca6391, requiere ath11k), Bluetooth (requiere qca)
- Audio (codec wcd9380 + altavoces tfa9874)
- Batería y carga, almacenamiento interno UFS
- USB OTG, NFC, flash LED, IR TX
- Sensores: acelerómetro, magnetómetro, luz ambiental (vía hexagonrpcd/SDSP)
- Cámara: **parcial**

### NO funciona (limitaciones de mainline, no del empaquetado)
- **Modem: llamadas, SMS y datos móviles ROTOS.** El SDX55m no tiene soporte en mainline.
- **GPS: roto.**
- **Proximidad: roto.**
- **Haptics (vibración): roto.**

> ⚠️ Aunque todos los paquetes compilan y la imagen bootea, este dispositivo **no sirve como teléfono primario**: sin modem no hay red móvil. Es un port funcional para escritorio/WiFi.

## Firmware

- Blobs QCOM (adsp, cdsp, slpi, venus, a650_zap, ipa_fws) + sensores: paquete `firmware-xiaomi-lmi`.
- Cirrus Logic (audio) y Focaltech (táctil): extraídos de `firmware-xiaomi-lmi-Tag.zip`.

> ⚠️ **`firmware-xiaomi-lmi-Tag.zip` NO está versionado en este repositorio** (es
> firmware propietario de Xiaomi, ~28 MB; excluido vía `.gitignore`). Para compilar
> el paquete debes colocarlo manualmente en este directorio como
> `device-xiaomi-lmi/firmware-xiaomi-lmi-Tag.zip`.
>
> sha512 esperado:
> `159939d72d5ac22b9e81e3d1dba8bfb937eb563622feaf961b5cea5a23bb4eb96923a0d395c17f87643ea8fd15041046e6bf229f5265206d767d4fd1653486bf`
>
> Tras colocarlo: `pmbootstrap checksum device-xiaomi-lmi`. (Para el MR a pmaports,
> este zip se convertirá en un `source` remoto con URL fija en vez de archivo local.)

## Flasheo

```bash
pmbootstrap install
pmbootstrap export
fastboot flash boot boot.img
fastboot flash system xiaomi-lmi.img
fastboot reboot
```

## Debug primer boot

USB networking funciona desde el initramfs. Tras conectar por USB:
- initramfs: `telnet 172.16.42.1`
- sistema arrancado: `ssh user@172.16.42.1`

Revisar `dmesg` por el panel Samsung ams667 y el GPU Adreno 650 (a650-zap es el punto típico de fallo gráfico).

## Riesgo de mantenimiento

El kernel se obtiene de un fork personal (`yuweiyuan8/linux` tag `v6.19`/`lmi`).
El tarball fuente está cacheado, pero si el fork desaparece, recompilar requerirá
re-localizar los parches. Base upstream de referencia: proyecto `sm8250-mainline`.
