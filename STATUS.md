# Proyecto: Portar postmarketOS a Xiaomi POCO F2 Pro (xiaomi-lmi)

**Última actualización:** 6 de junio de 2026
**Dispositivo:** Xiaomi POCO F2 Pro / Redmi K30 Pro
**SoC:** Qualcomm SM8250 (Snapdragon 865)
**Arquitectura:** aarch64
**UI:** xfce4
**Estrategia:** Kernel mainline v6.19.7

---

## 0. ESTADO ACTUAL / PRÓXIMO PASO

⏳ **BLOQUEADO esperando desbloqueo de bootloader (Xiaomi Mi Unlock).**

- Al 6 jun 2026 el teléfono indica **~217 horas restantes** (~9 días) → habilitado **~15 jun 2026**.
- `fastboot` ya detecta el dispositivo correctamente; `fastboot getvar unlocked` → `unlocked: no` (esperado).
- **Mientras tanto NO tocar la cuenta Mi ni hacer factory reset** (reinicia el contador).

▶️ **Próxima acción real:** cuando el contador llegue a 0, seguir
`GUIA-DESBLOQUEO-Y-FLASHEO.md` (Fase 1 → desbloqueo → Fase 3 → flasheo → Fase 5 → verificar modem).

> Las imágenes ya están recompiladas con el modem habilitado (ver §1). El día del
> flasheo solo hay que correr `pmbootstrap export` de nuevo (regenera symlinks en
> /tmp, que se borra al reiniciar la laptop) — NO hay que recompilar.

---

## 1. Resumen Ejecutivo

**TODO EL SOFTWARE ESTÁ COMPILADO Y VERIFICADO** (última build: 6 jun 2026, 11:03).
Imágenes en `/tmp/postmarketOS-export/` listas para flashear.

> ✅ **Modem SDX55 HABILITADO** (corrige la nota antigua que decía "sin soporte").
> Investigación confirmó que el SDX55 es un modem externo PCIe soportado en mainline
> desde Linux 5.13 (driver `mhi_pci_generic`, autodetección por PCI ID 17cb:0306).
> Faltaba habilitar el bus PCIe en el devicetree → patch aplicado y **verificado en
> el dtb compilado** (`pcie@1c08000` y `phy@1c0e000` = status okay).
>
> **Estado del hardware:**
> - ✅ Funciona: pantalla, GPU, WiFi, BT, audio, táctil, batería, sensores, cámara parcial.
> - 🧪 Por probar en HW: modem (datos probable; voz/VoLTE experimental).
> - ❌ Roto en mainline: GPS, proximidad, haptics.
> - Detalle: `device/testing/device-xiaomi-lmi/README.md`.

---

## 2. Paquetes — Estado Actual

| Paquete | Versión | Tamaño | Estado | Fecha |
|---|---|---|---|---|
| `linux-postmarketos-qcom-sm8250-lmi` | 6.19.7-r0 | 28 MB | ✅ COMPILADO | 31 may 2026 |
| `linux-xiaomi-lmi` (downstream legacy) | 6.16.0-r0 | 61 MB | ✅ COMPILADO | 30 nov 2025 |
| `firmware-xiaomi-lmi` | 1-r0 | 27 MB | ✅ COMPILADO | 31 may 2026 |
| `firmware-xiaomi-lmi-sensors` | 1-r0 | 1.3 KB | ✅ COMPILADO | 31 may 2026 |
| `device-xiaomi-lmi` | 1-r0 | 3.8 KB | ✅ COMPILADO | 31 may 2026 |
| `device-xiaomi-lmi-nonfree-firmware` | 1-r0 | 77 KB | ✅ COMPILADO | 31 may 2026 |
| `device-xiaomi-lmi-nonfree-firmware-openrc` | 1-r0 | 1.4 KB | ✅ COMPILADO | 31 may 2026 |

---

## 3. Imágenes Generadas — Rutas en Disco

| Artefacto | Ruta | Tamaño |
|---|---|---|
| **RootFS image** | `~/.local/var/pmbootstrap/chroot_native/home/pmos/rootfs/xiaomi-lmi.img` | **1.6 GB** |
| **Boot image** | `~/.local/var/pmbootstrap/chroot_rootfs_xiaomi-lmi/boot/boot.img` | **25 MB** |
| **vmlinuz** | `~/.local/var/pmbootstrap/chroot_rootfs_xiaomi-lmi/boot/vmlinuz` | **13 MB** |
| **initramfs** | `~/.local/var/pmbootstrap/chroot_rootfs_xiaomi-lmi/boot/initramfs` | **12 MB** |

### APKs compilados

| APK | Ruta | Tamaño |
|---|---|---|
| Kernel mainline | `~/.local/var/pmbootstrap/packages/edge/aarch64/linux-postmarketos-qcom-sm8250-lmi-6.19.7-r0.apk` | 28 MB |
| Kernel downstream | `~/.local/var/pmbootstrap/packages/edge/aarch64/linux-xiaomi-lmi-6.16.0-r0.apk` | 61 MB |
| Firmware | `~/.local/var/pmbootstrap/packages/edge/aarch64/firmware-xiaomi-lmi-1-r0.apk` | 27 MB |
| Firmware sensors | `~/.local/var/pmbootstrap/packages/edge/aarch64/firmware-xiaomi-lmi-sensors-1-r0.apk` | 1.3 KB |
| Device | `~/.local/var/pmbootstrap/packages/edge/aarch64/device-xiaomi-lmi-1-r0.apk` | 3.8 KB |
| Device nonfree-firmware | `~/.local/var/pmbootstrap/packages/edge/aarch64/device-xiaomi-lmi-nonfree-firmware-1-r0.apk` | 77 KB |
| Device nonfree-firmware-openrc | `~/.local/var/pmbootstrap/packages/edge/aarch64/device-xiaomi-lmi-nonfree-firmware-openrc-1-r0.apk` | 1.4 KB |

---

## 4. Paquetes en pmaports — Código Fuente

### `device/testing/device-xiaomi-lmi/`

| Archivo | Propósito |
|---|---|
| `APKBUILD` | Definición del paquete (depende de `linux-postmarketos-qcom-sm8250-lmi`) |
| `deviceinfo` | Config del dispositivo (DTB `sm8250-xiaomi-lmi`, fastboot, UFS 4096) |
| `modules-initfs` | Módulos del panel para initramfs |
| `81-libssc-xiaomi-lmi.rules` | Udev para acelerómetro vía fastrpc |
| `hexagonrpcd.confd` | Ruta de firmware: `/usr/share/qcom/sm8250/Xiaomi/lmi` |
| `alsa-ucm-conf/lmi.conf` | ALSA UCM principal |
| `alsa-ucm-conf/HiFi.conf` | ALSA UCM HiFi |
| Post-install scripts | Habilita servicios: qbootctl, hexagonrpcd-sdsp, tqftpserv |

### `device/testing/firmware-xiaomi-lmi/`

| Archivo | Propósito |
|---|---|
| `APKBUILD` | Maintainer: Nikroks. Source: `yuweiyuan8/firmware-xiaomi-lmi` commit `dde15638` |
| `firmware.files` | Lista de 11 blobs QCOM a instalar (a650_zap, adsp, cdsp, slpi, venus, ipa_fws) |
| `sensor.files` | Lista de 319 archivos de sensores + DSP + ACDB |
| `30-initramfs-firmware.files` | 3 archivos para initramfs (a650_zap, a650_sqe, a650_gmu) |
| Subpackage | `firmware-xiaomi-lmi-sensors` para datos de sensores |

### `device/testing/linux-postmarketos-qcom-sm8250-lmi/`

| Campo | Valor |
|---|---|
| Versión | 6.19.7 |
| Source | `yuweiyuan8/linux` tag `v6.19`, tag `lmi` |
| Builddir | `linux-6.19` |
| Config | `config-postmarketos-qcom-sm8250-lmi.aarch64` |

---

## 5. Correcciones Aplicadas

| Problema | Estado |
|---|---|
| `hexagonrpcd.confd` tenía `alioth` → corregido a `lmi` | ✅ |
| `deviceinfo_append_dtb` duplicado → línea única | ✅ |
| Firmware package creado con file lists estructurados | ✅ |
| Kernel mainline actualizado de 6.13.4 → 6.19.7 | ✅ |
| Todos los paquetes compilados exitosamente | ✅ |
| Imagen del sistema generada (1.6 GB) | ✅ |

---

## 6. Próximos Pasos

```bash
# Opcional: exportar imágenes a directorio accesible
pmbootstrap export

# Flashear al dispositivo (conectado por USB en modo fastboot)
fastboot flash boot /path/to/boot.img
fastboot flash system /path/to/xiaomi-lmi.img
fastboot reboot
```

---

## 7. Árbol de Directorios Relevante

```
~/.local/var/pmbootstrap/
├── cache_git/pmaports/device/testing/
│   ├── device-xiaomi-lmi/              ← código del device package
│   ├── firmware-xiaomi-lmi/            ← código del firmware package
│   ├── linux-postmarketos-qcom-sm8250-lmi/  ← kernel mainline
│   └── linux-xiaomi-lmi/              ← kernel downstream (legacy)
├── packages/edge/aarch64/
│   ├── device-xiaomi-lmi-1-r0.apk
│   ├── device-xiaomi-lmi-nonfree-firmware-1-r0.apk
│   ├── device-xiaomi-lmi-nonfree-firmware-openrc-1-r0.apk
│   ├── firmware-xiaomi-lmi-1-r0.apk
│   ├── firmware-xiaomi-lmi-sensors-1-r0.apk
│   ├── linux-postmarketos-qcom-sm8250-lmi-6.19.7-r0.apk
│   └── linux-xiaomi-lmi-6.16.0-r0.apk
├── chroot_native/home/pmos/rootfs/
│   └── xiaomi-lmi.img                 ← rootfs (1.6 GB)
└── chroot_rootfs_xiaomi-lmi/boot/
    ├── boot.img                        ← boot image (25 MB)
    ├── vmlinuz                          ← kernel (13 MB)
    └── initramfs                        ← initramfs (12 MB)

~/postmarket/
├── STATUS.md                            ← este documento
├── PostmarkertOS_web/                   ← wikis offline
├── device-xiaomi-lmi/                   ← copia local antigua
├── linux-xiaomi-lmi/                    ← copia local antigua
└── linux-sm8250/                        ← directorio vacío

~/Descargas/
├── firmware-xiaomi-lmi-Tag.zip          ← firmware zip original (28 MB)
└── pmos_xiaomi_lmi-mainline/            ← copias antiguas
```
