# Contexto del proyecto — para retomar desde cualquier dispositivo

> Lee este archivo primero para ponerte al día. Resume todo el trabajo y decisiones.

## Quién y qué
Usuario portando **postmarketOS** a varios teléfonos. Trabaja en laptop Arch Linux
con `pmbootstrap`. Repo de respaldo: este mismo (GitHub).

## Proyecto 1: Xiaomi POCO F2 Pro (xiaomi-lmi, SM8250) — PRINCIPAL
- Estado: software compilado y verificado, **bloqueado esperando desbloqueo de
  bootloader Xiaomi** (~217h al 6 jun 2026 → habilitado ~15 jun 2026).
- Modem SDX55: HABILITADO vía patch de devicetree (pcie1 + pcie1_phy). Ver
  `linux-postmarketos-qcom-sm8250-lmi/0001-...modem.patch`.
- Guía completa de desbloqueo/flasheo: `GUIA-DESBLOQUEO-Y-FLASHEO.md`.
- Próximo paso real: cuando desbloquee → flashear → verificar modem (lspci/mmcli).

## Proyecto 2: Galaxy S9+ Snapdragon (SM-G9650, star2qltechn, SDM845) — 2 unidades
- EXCELENTE candidato. Kernel `linux-postmarketos-qcom-sdm845` (top soporte).
- dts del S9 (starqltechn) SÍ está en mainline; el del S9+ (star2qltechn) NO →
  hay que ADAPTARLO. Diferencias: panel s6e3ha8 (más grande), batería 3500mAh, cámara dual.
- **Llamadas funcionan** en SDM845 mainline (caveat: sin DTMF).
- Boot: U-Boot + Heimdall (SIN espera de bootloader). Se puede flashear cuando sea.
- Próximo paso: adaptar devicetree del S9 → S9+.

## Proyecto 3: Xiaomi Mi 8 Lite (xiaomi-platina, SDM660)
- **Bootloader YA desbloqueado** → flasheable de inmediato.
- WiFi = WCN3990 via ath10k_snoc. Según wiki SDM660: WiFi "Works".
- DIAGNÓSTICO del WiFi: el device package NO depende de `soc-qcom-sdm660-rproc`
  (que aporta rmtfs/tqftpserv). Sin rmtfs el modem no levanta, y "si el modem
  crashea el WiFi muere". Además necesita firmware `wlanmdsp.mbn` (firmado por
  dispositivo, hay que extraerlo del propio teléfono).
- Caveat conocido: desconectarse del WiFi o salir de rango lo rompe hasta reboot
  (issue sdm660-mainline #75).
- PRÓXIMO PASO PENDIENTE: añadir dep `soc-qcom-sdm660-rproc` al device-xiaomi-platina,
  empaquetar wlanmdsp.mbn, compilar y flashear.

## Descartados
- Galaxy Note 8 (greatlte, Exynos 8895): sin port. No recomendado.
- Galaxy S21 Ultra (Exynos 2100): sin port, boot hostil. Dejar en Android.

## Regla aprendida
Snapdragon >> Exynos para mainline. Siempre confirmar modelo exacto (Exynos vs
Snapdragon tienen codenames distintos).

---
Última actualización del contexto: 6 jun 2026.
