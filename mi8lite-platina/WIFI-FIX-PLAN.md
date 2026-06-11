# Plan: WiFi funcional en postmarketOS — Xiaomi Mi 8 Lite (platina)

**Fecha:** 8 junio 2026
**Dispositivo:** Xiaomi Mi 8 Lite (xiaomi-platina, SDM660)
**Kernel:** linux-postmarketos-qcom-sdm660 6.17.4
**Estado:** En progreso

---

## Problema raíz

El firmware WCN3990 (WLAN.HL.3.2) tiene un **bug conocido** que causa crash determinístico:

1. **Quiet mode crash:** El firmware crashea al recibir el comando `quiet mode` WMI durante `ath10k_start()`. El crash ocurre en `PC=0xb0008e20` en `wlanmdsp.mbn`, ~17ms después de `vdev_create`, y cascada a un crash completo del modem MSS.

2. **Active scan bug:** El active scan no tunea la radio en canales 5GHz non-DFS, haciendo las redes 5GHz invisibles.

**Efecto en el dispositivo:**
- MSS crashea en bucle (`Task starvation: diag`, luego `EX:wlan_process`)
- WiFi se desestabiliza (scans fallan con `-108 / socket shutdown`)
- Board file reporta `crc32 00000000` cuando el MSS está caído

**Solución:** Parches upstream de Malte Schababerle (marzo 2026), aún no mergeados en todas las ramas.

---

## Fase 1: Crear tarballs de firmware

### Archivos fuente
- **WiFi:** `Mi8Lite/mi8lite-firmware-dump/firmware_mnt/fwdump/`
  - `bdwlan.*` (27 board files)
  - `wlanmdsp.mbn` (firmware WiFi, 3.4 MB)
  - `mba.mbn` (modem boot, 238 KB)
- **Modem:** `Mi8Lite/mi8lite-modem-fw/`
  - `mba.mbn`
  - `modem.mdt`
  - `modem.b00` - `modem.b28`

### Archivos generados
- `firmware-xiaomi-platina-bdwlan.tar.gz` → para el paquete firmware
- `firmware-xiaomi-platina-modem.tar.gz` → para el paquete firmware

### Comandos
```bash
cd /home/arch/postmarket/Mi8Lite/mi8lite-platina/firmware-xiaomi-platina

# Empaquetar firmware WiFi
tar czf firmware-xiaomi-platina-bdwlan.tar.gz \
  -C ../mi8lite-firmware-dump/firmware_mnt/fwdump/ \
  bdwlan.* wlanmdsp.mbn mba.mbn

# Empaquetar firmware modem
tar czf firmware-xiaomi-platina-modem.tar.gz \
  -C ../mi8lite-modem-fw/ \
  mba.mbn modem.mdt modem.b*
```

---

## Fase 2: Crear patches del kernel

### Patch 1: Skip quiet mode para WCN3990

**Archivo:** `0002-ath10k-skip-quiet-mode-wcn3990.patch`
**Base:** drivers/net/wireless/ath/ath10k/thermal.c
**Problema:** El firmware WCN3990 crashea al recibir el comando quiet mode WMI
**Solución:** Saltar quiet mode incondicionalmente para WCN3990 usando `QCA_REV_WCN3990()`

```diff
--- a/drivers/net/wireless/ath/ath10k/thermal.c
+++ b/drivers/net/wireless/ath/ath10k/thermal.c
@@ -136,6 +136,16 @@ void ath10k_thermal_set_throttling(struct ath10k *ar)
 	if (!ar->wmi.ops->gen_pdev_set_quiet_mode)
 		return;
 
+	/* WCN3990 firmware crashes on quiet mode despite advertising support.
+	 * See also commit 53884577fbcef ("ath10k: skip sending quiet mode
+	 * cmd for WCN3990").
+	 */
+	if (QCA_REV_WCN3990(ar)) {
+		ath10k_dbg(ar, ATH10K_DBG_BOOT,
+			   "skip quiet mode for WCN3990 (known crash trigger)\n");
+		return;
+	}
+
 	if (ar->state != ATH10K_STATE_ON)
 		return;
```

### Patch 2: Force passive scan en 5GHz

**Archivo:** `0003-ath10k-force-passive-scan-5ghz.patch`
**Base:** drivers/net/wireless/ath/ath10k/mac.c
**Problema:** Active scan no tunea la radio en canales 5GHz non-DFS
**Solución:** Forzar passive scan en 5GHz para WCN3990

```diff
--- a/drivers/net/wireless/ath/ath10k/mac.c
+++ b/drivers/net/wireless/ath/ath10k/mac.c
@@ -3441,6 +3441,14 @@ static int ath10k_update_channel_list(struct ath10k *ar)
 			passive = channel->flags & IEEE80211_CHAN_NO_IR;
 			ch->passive = passive;
 
+			/* Force passive scan on 5GHz to work around WCN3990
+			 * firmware bug where active scan doesn't tune the
+			 * radio on 5GHz non-DFS channels.
+			 */
+			if (QCA_REV_WCN3990(ar) &&
+			    band == NL80211_BAND_5GHZ)
+				ch->passive = true;
+
 			/* the firmware is ignoring the "radar" flag of the
 			 * channel and is scanning actively using Probe Requests
 			 * on "Radar detection"/DFS channels which are not
```

---

## Fase 3: Actualizar APKBUILD del kernel

**Archivo:** `linux-postmarketos-qcom-sdm660/APKBUILD`

### Cambios
1. Incrementar `pkgrel=3` → `pkgrel=4`
2. Añadir patches a `source=`
3. Recalcular `sha512sums`

### source= actualizado
```
source="
	linux-$_tag.tar.gz::https://github.com/sdm660-mainline/linux/archive/refs/tags/$_tag.tar.gz
	config-$_flavor.aarch64
	0001-platina-wifi.patch
	0002-ath10k-skip-quiet-mode-wcn3990.patch
	0003-ath10k-force-passive-scan-5ghz.patch
"
```

---

## Fase 4: Compilar e instalar

### Compilación
```bash
pmbootstrap checksum device-xiaomi-platina
pmbootstrap checksum linux-postmarketos-qcom-sdm660
pmbootstrap checksum firmware-xiaomi-platina
pmbootstrap build linux-postmarketos-qcom-sdm660
pmbootstrap build firmware-xiaomi-platina
pmbootstrap build device-xiaomi-platina
pmbootstrap install --password TU_PASSWORD
pmbootstrap export
```

### Flasheo (desde Android)
```bash
fastboot flash boot boot.img
fastboot flash userdata xiaomi-platina-root.img
pmbootstrap flasher flash_kernel
pmbootstrap flasher flash_vbmeta
```

### Verificación
```bash
ssh user@172.16.42.1
dmesg | grep -i ath10k        # Debe mostrar "skip quiet mode for WCN3990"
dmesg | grep -i remoteproc    # Debe mostrar MSS arrancando
iw dev wlan0 scan             # Debe mostrar redes WiFi
mmcli -L                      # Debe mostrar el modem
```

---

## Dependencias del paquete device-xiaomi-platina

```
depends="
	linux-postmarketos-qcom-sdm660
	mkbootimg
	postmarketos-base
	soc-qcom-sdm660
	soc-qcom-sdm660-rproc
	"
```

`soc-qcom-sdm660-rproc` aporta: rmtfs, tqftpserv, diag-router. **Sin rmtfs, el WiFi WCN3990 no funciona.**

---

## Archivos en el repositorio

```
Mi8Lite/
├── mi8lite-bootlogs/          ← Logs del boot anterior
│   ├── dmesg.txt
│   └── ...
├── mi8lite-firmware-dump/     ← Firmware extraído del Android
│   └── firmware_mnt/fwdump/
│       ├── bdwlan.*           ← Board files (27 archivos)
│       ├── wlanmdsp.mbn       ← Firmware WiFi (3.4 MB)
│       └── mba.mbn            ← Modem boot (238 KB)
├── mi8lite-modem-fw/          ← Firmware del modem
│   ├── mba.mbn
│   ├── modem.mdt
│   ├── modem.b00 - modem.b28
│   └── modem_pr/              ← Configs de carriers
└── mi8lite-platina/           ← Paquetes pmos
    ├── device-xiaomi-platina/
    │   ├── APKBUILD
    │   ├── deviceinfo
    │   └── modules-initfs
    ├── firmware-xiaomi-platina/
    │   ├── APKBUILD
    │   └── gen-board-2.py
    └── linux-postmarketos-qcom-sdm660/
        ├── APKBUILD
        └── 0001-platina-wifi.patch
```

---

## Referencias

- **Patch quiet mode:** [lore.kernel.org](https://yhbt.net/lore/linux-wireless/20260322124822.230492-1-m.schababerle@gmail.com/)
- **Patch passive scan:** Mismo thread (patch 2/2)
- **sdm660-mainline:** [github.com/sdm660-mainline/linux](https://github.com/sdm660-mainline/linux)
- **postmarketOS wiki:** [Xiaomi Mi 8 Lite](https://wiki.postmarketos.org/wiki/Xiaomi_Mi_8_Lite)

---

## Notas conocidas

1. **Pantalla NO funciona** en mainline (kernel solo para desarrollo). El kernel downstream (LineageOS) tiene pantalla.
2. **Caveat sdm660-mainline #75:** Salir de rango del AP rompe el WiFi hasta reiniciar.
3. **GPT corrupto:** El boot anterior mostró errores de GPT. Usar `--split` en `pmbootstrap install`.
4. **rmtfs service ordering:** Necesita `Before=NetworkManager.service` para evitar crash al apagar.
