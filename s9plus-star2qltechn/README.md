# Samsung Galaxy S9+ (samsung-star2qltechn) — port en progreso

Port de postmarketOS para el Samsung Galaxy S9+ Snapdragon (SM-G9650, SDM845).

## Estado: EN PROGRESO (Fase 1 — validar boot)

El S9+ (`star2qltechn`) NO tiene port en pmaports; el que existe es el S9
(`starqltechn`). Este device se basa en el del S9 (de dsankouski, community).

## Hallazgos de la investigación (validados en el teléfono físico)

- **Modelo:** SM-G9650, codename `star2qltechn`, SoC Snapdragon 845.
- **WiFi = WCN3990** (integrado del SDM845), NO Broadcom como sugiere la wiki.
  La wiki dice "broadcom chip" pero eso es el **Bluetooth** (BCM4361, archivos
  `bcm4361B2_*.hcd`). El WiFi usa los `bdwlan.*` + `wlanmdsp.mbn` del WCN3990.
- **Pronóstico WiFi bueno:** el WCN3990 en SDM845 es estable (OnePlus6/PocoF1
  mismo chip+SoC tienen WiFi OK). NO sufriría el crash de firmware que afectó
  al Mi 8 Lite (ese era bug específico del SDM660 mainline).
- Firmware extraído del teléfono (root Magisk): WiFi (28 bdwlan + wlanmdsp) y
  modem MSS (mba + modem.mdt + 21 segmentos + adsp), desde `/vendor/firmware_mnt/image/`
  (wifi) y `/vendor/firmware-modem/image/` (modem — ruta Samsung distinta).

## Arquitectura del port (heredada del S9)

- Kernel: `linux-postmarketos-qcom-sdm845` (primera clase).
- Boot: U-Boot FIT image + heimdall (no fastboot) a particiones BOOT/SYSTEM.
- Firmware en runtime vía `msm-firmware-loader` + `hexagonfs-firmware-loader`
  (carga los bdwlan del propio teléfono; por eso el S9 no empaqueta firmware wifi).
- Deps clave: soc-qcom-modem, soc-qcom-pd-mapper, alsa-ucm-conf-sdm845.

## Diferencias S9 vs S9+ (a refinar)

Mismo SoC, misma resolución (2960x1440), mismo WiFi. Difieren: pantalla 6.2"
(vs 5.8"), batería 3500mAh (vs 3000), RAM 6GB (vs 4, auto-detectada), cámara
dual. El dts de dsankouski está pensado como base común S9/S9+.

Para el primer arranque de validación, el S9+ reutiliza la infra del S9
(mismo u-boot, dtb `sdm845-samsung-starqltechn`), por compartir SoC.

## Pendiente

- [ ] Fase 1: validar que pmOS arranca (boot + SSH) en el S9+
- [ ] Crear dts propio del S9+ (panel/batería) compilado en el kernel
- [ ] Habilitar `&wifi` (WCN3990) en el dts — plantilla OnePlus6
- [ ] Empaquetar/verificar firmware WiFi (board-2.bin con board-id hex correcto)
- [ ] U-Boot del S9+ (evaluar si el del S9 sirve o necesita defconfig propio)
