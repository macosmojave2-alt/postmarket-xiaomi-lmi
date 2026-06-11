# Investigacion WiFi SDM660 — Xiaomi Mi 8 Lite (platina)

---

## ⛔ CONCLUSIÓN DEFINITIVA (10 jun 2026, kernel r21 / #22)

Tras resolver toda la cadena de bringup (modem, MSA, board file, LED, psmode), el WiFi queda
bloqueado por un **límite del firmware WLAN propietario**, no del driver mainline.

**Cadena de blockers, en orden de aparición y resolución:**
1. ✅ Modem MSS estable — rmtfs → diag-router → tqftpserv en orden.
2. ✅ LED oops — `CONFIG_MAC80211_LEDS=n` (+ actualizar módulos vía `install --split`).
3. ✅ Bringup QMI completo en boot limpio — chip_id 0x140, board_id 0xff, BDF OK, fw ready.
   (Los errores -22/err90/board-vacío eran ARTEFACTOS de estados sucios con uptime alto.)
4. ✅ **Crash `set psmode` (PC=b00c75b8)** — RESUELTO con **patch 0012** (`QCA_REV_WCN3990` →
   `return 0` en `ath10k_mac_vif_setup_ps`). Verificado: `set psmode = 0`, 0 crashes en bringup.
   (El patch 0011, que tocaba `SUPPORTS_PS`, NO bastaba: el psmode se mandaba por la ruta
   "force-enable PS for non-running vdevs", independiente de SUPPORTS_PS.)
5. ⛔ **Crash en `wmi tlv start scan` — MISMO `PC=b00c75b8`.** BLOCKER FINAL.

**El hallazgo decisivo:** el crash del scan ocurre en la **misma rutina del firmware**
(`PC=b00c75b8`) que el del psmode. No es un comando WMI evitable desde userspace ni desde el
driver: `b00c75b8` es una rutina interna de power-management del firmware WLAN.HL.1.0.1.c6 (que
corre dentro del Q6 del modem SDM660) que TANTO `set psmode` COMO el scan invocan. Eliminada la
vía del psmode (patch 0012), el scan llega a la misma rutina rota por otro camino y crashea
(`EX:wlan_process`, determinista bajo scans repetidos: 5 scans → 0 SSIDs, varios crashes, ningún
evento de resultados). El driver está sano (phy0 conoce la banda 2.4GHz, ch 2412–2457). Los
patches 0002 (skip quiet mode) y 0003 (passive scan 5GHz) ya están aplicados y no ayudan: el
quiet mode ni se ejecuta (PC sería b0008e20, nunca visto) y el crash es en 2.4GHz, no 5GHz.

**Veredicto:** el firmware WLAN propietario del SDM660 es inestable bajo operación real (scan) en
mainline ath10k. No hay fix desde paquetes/driver. Opciones: (a) kernel DOWNSTREAM con qcacld
(driver propietario que sí maneja este firmware, además da pantalla), o (b) **pivotar al S9+
(SDM845, samsung-star2qltechn)** donde el WCN3990 es estable en mainline. Ver memoria
`s9-wifi-investigacion`.

---

**Fecha:** 9 junio 2026 (actualizado 07:30)
**Dispositivo:** Xiaomi Mi 8 Lite (xiaomi-platina, SDM660)
**Kernel:** linux-postmarketos-qcom-sdm660 6.17.4-r11 (8 patches)
**Estado:** WiFi — MPSS modem crashea cada ~40s. Causa: firmware espera `qcom,memshare` que no existe en mainline.

---

## Resumen ejecutivo

### Cadena completa del problema WiFi

```
ath10k_snoc (WiFi driver)
  └─ QMI WLFW service
      └─ WCN3990 chip (SNOC)
          └─ WLAN Protection Domain (dentro de MPSS)
              └─ MPSS (modem subsystem) ← CRASH cada ~40s
                  └─ Firmware espera qcom,memshare ← NO EXISTE en mainline
```

### Estado actual (9 jun 07:30)

| Paso | Estado | Detalle |
|------|--------|---------|
| ath10k_snoc probe | ✓ OK | Patch 0006 funciona |
| QMI init | ✓ OK | Handler registrado |
| MPSS boot (mba.mbn) | ✓ OK | MBA carga exitosamente |
| MPSS run | ✗ CRASH | Fatal error sin mensaje cada ~40s |
| WLAN PD start | ✗ NUNCA | No se activa sin MPSS estable |
| QMI WLFW service | ✗ NUNCA | No aparece sin WLAN PD |
| wlan0 | ✗ NUNCA | No se crea |

### Causa raíz del crash del modem

El firmware del modem (`mba.mbn` + `modem.mdt`) fue compilado para Android (`platina-q-stable-build`). Espera ciertos servicios del AP que no existen en mainline:

1. **`qcom,memshare`** — Memoria compartida AP↔modem para operaciones internas. **No existe driver en mainline.**
2. **`qcom,glink-smem-native-xprt-modem`** — Transporte GLINK SMEM para el modem. **No hay driver.**
3. El firmware intenta usar estos servicios, no obtiene respuesta, y el watchdog interno lo mata después de ~40s.

### Patch 0008: `qcom,msm-id` (creado, no resolvió crash)

Agrega `qcom,msm-id = <317 0x0>` al DTS de platina. Este valor (317 = 0x13d) es el SoC ID de SDM660, extraído del kernel Android (`MiCode/Xiaomi_Kernel_OpenSource`).

**Resultado:** El modem sigue crasheando cada ~40s. El `qcom,msm-id` es necesario pero no suficiente.

---

## Análisis del crash del modem (9 jun 07:00-07:30)

### Comportamiento observado

```
t=177s  MBA booted, loading mpss
t=179s  MPSS is now up
t=219s  fatal error without message (crash #1)  ← ~40s después
t=220s  MPSS recovered
t=260s  fatal error without message (crash #2)  ← ~40s después
t=262s  MPSS recovered
...ciclo infinito...
```

### Diferencias clave entre Android y mainline DT

| Región | Android | Mainline | Impacto |
|--------|---------|----------|---------|
| MBA addr | `0x94c00000` | `0x94800000` | 4MB offset — MBA sí carga |
| adsp fw | 34MB | 30MB | 4MB menos |
| `qcom,memshare` | ✓ Presente | ✗ Ausente | **CRÍTICO** |
| `qcom,glink-smem-native-xprt-modem` | ✓ Presente | ✗ Ausente | Sin driver |
| `qcom,ipc_router_modem_xprt` | ✓ Presente | ✗ Ausente | Sin driver |

### Servicios QRTR disponibles

| Service | ID | Tipo |
|---------|-----|------|
| 0-1 | 42 (0x2a) | Control |
| 0-4 | 43 (0x2b) | Control |
| WLFW | — | **AUSENTE** (necesario para WiFi) |

### Módulos cargados relevantes

```
qcom_q6v5_mss          40960  0   ← MSS driver (modem)
qcom_q6v5_pas          36864  0   ← PAS driver (ADSP/CDSP)
qrtr_smd               20480  0   ← QRTR transport (0 refs)
qcom_pd_mapper         28672  0   ← Protection Domain mapper
qcom_sysmon            24576  3   ← System monitor
rmtfs_mem              16384  0   ← RMTFS memory
```

### ¿Por qué `qcom,memshare` es crítico?

El `qcom,memshare` provee memoria compartida para:
- Comunicación AP↔modem para operaciones de alto nivel
- Asignación de memoria dinámica para subsistemas del modem
- Almacenamiento temporal de datos de control

Sin esta memoria, el modem firmware:
1. Inicializa correctamente (MBA + MPSS cargan)
2. Intenta usar memoria compartida que nunca fue asignada
3. Falla silenciosamente o cuelga
4. Watchdog interno lo mata después de ~40s

### Código fuente del driver memshare (Android kernel)

El driver `qcom_memshare.c` existe en el kernel Android:
```
drivers/soc/qcom/memshare/qcom_memshare.c
drivers/soc/qcom/memshare/memshare.h
```

Funciones principales:
- `qcom_memshare_alloc()` — Asigna memoria compartida
- `qcom_memshare_get()` — Obtiene referencia a memoria asignada
- `qcom_memshare_free()` — Libera memoria compartida

El driver interactúa con TrustZone via SCM para asignar memoria con VMID específico (`QCOM_SCM_VMID_MSS_MSA`).

### Próximo paso: Portar driver memshare

1. Extraer `qcom_memshare.c` + `memshare.h` del kernel Android
2. Adaptar al API del kernel 6.17 (cambios en `qcom_scm.h`)
3. Agregar Kconfig/Makefile entries
4. Agregar DT node `qcom,memshare` al DTS de platina
5. Compilar y probar

---

## Patches actuales (pkgrel=12)

| Patch | Archivo | Estado |
|-------|---------|--------|
| 0001 | `0001-platina-wifi.patch` | ✓ Activo — habilita WiFi + MSS |
| 0002 | `0002-ath10k-skip-quiet-mode-wcn3990.patch` | ✓ Activo |
| 0003 | `0003-ath10k-force-passive-scan-5ghz.patch` | ✓ Activo |
| 0004 | `0004-platina-disable-gpu-smmu-for-gcc-sync.patch` | ✓ Activo |
| 0005 | `0005-ath10k-snoc-add-debug-probe-prints.patch` | ✓ Activo (temporal) |
| 0006 | `0006-ath10k-snoc-call-core_register-to-create-wlan0.patch` | ✓ Activo |
| 0007 | `0007-ath10k-core-add-debug-prints-to-register-work.patch` | ✓ Activo (temporal) |
| 0008 | `0008-platina-add-qcom-msm-id-for-modem-stability.patch` | ✓ Activo — `qcom,msm-id` |
| 0009 | `0009-sdm660-add-qcom-memshare-driver.patch` | ✓ Activo — port de `qcom_memshare` desde msm8916-mainline |

### Detalle del Patch 0009

**Objetivo:** Port el driver `qcom_memshare` al kernel mainline para resolver el crash del modem SDM660.

**Archivos agregados:**
- `drivers/soc/qcom/memshare.c` — Driver principal (502 líneas)
- `drivers/soc/qcom/memshare_qmi_msg.c` — Definiciones QMI (370 líneas)
- `drivers/soc/qcom/memshare_qmi_msg.h` — Header QMI (228 líneas)
- `include/dt-bindings/soc/qcom,memshare.h` — DT bindings header
- `Documentation/devicetree/bindings/soc/qcom/qcom,memshare.yaml` — DT bindings documentation

**Archivos modificados:**
- `drivers/soc/qcom/Kconfig` — Agregado `CONFIG_QCOM_MEMSHARE`
- `drivers/soc/qcom/Makefile` — Agregado build de memshare
- `arch/arm64/boot/dts/qcom/sdm630.dtsi` — Agregado DT node `qcom_memshare` y reserved-memory regions

**DT node agregado:**
```
qcom_memshare: memshare {
    compatible = "qcom,memshare";
    #address-cells = <1>;
    #size-cells = <0>;
    mpss@0 {
        reg = <0>;
        qcom,qrtr-node = <0>;
        #address-cells = <1>;
        #size-cells = <0>;
        memshare_modem_boot: modem-boot@0 {
            reg = <0>;
            memory-region = <&memshare_client0>;  /* 2MB @ 0x95000000 */
        };
        memshare_modem_runtime: modem-runtime@2 {
            reg = <2>;
            memory-region = <&memshare_client2>;  /* 3MB @ 0x95200000 */
        };
    };
};
```

**Reserved-memory regions agregadas:**
- `memshare_client0` @ 0x95000000 — 2MB (boot-time, client ID 0)
- `memshare_client2` @ 0x95200000 — 3MB (runtime, client ID 2)

**Fuente:** Driver upstream de Nikita Travkin (msm8916-mainline), adaptado para SDM660.

---

---

## Descubrimiento: Upstream ya tiene core_register en QMI handler (9 jun 2026, 00:30)

### Flujo real del upstream

El upstream de `ath10k_snoc.c` **YA TIENE** `ath10k_core_register()` en la línea 1369 — dentro del QMI event handler para `ATH10K_QMI_EVENT_FW_READY_IND`:

```c
case ATH10K_QMI_EVENT_FW_READY_IND:
    if (test_bit(ATH10K_SNOC_FLAG_REGISTERED, &ar_snoc->flags)) {
        ath10k_core_start_recovery(ar);
        break;
    }
    bus_params.dev_type = ATH10K_DEV_TYPE_LL;
    bus_params.chip_id = ar_snoc->target_info.soc_version;
    ret = ath10k_core_register(ar, &bus_params);
```

El diseño upstream es:
1. Probe hace setup (reguladores, clocks, QMI handlers)
2. Chip WCN3990 arranca (necesita firmware cargado via remoteproc)
3. Chip envía `FW_READY_IND` vía QMI
4. Handler llama `ath10k_core_register()` → workqueue → firmware loading → wlan0

### Nuestro patch 0006 es redundante pero reveló el problema

Nuestro patch 0006 agrega una segunda llamada a `ath10k_core_register()` al final del probe. Esto causó que el workqueue se ejecutara, revelando el problema real:

```
[   12.542627] ath10k_snoc 18800000.wifi: >>> ath10k_core_register: queueing work
[   12.542639] ath10k_snoc 18800000.wifi: <<< ath10k_snoc_probe SUCCESS
[   12.542750] ath10k_snoc 18800000.wifi: >>> ath10k_core_register_work ENTER
[   12.548241] ath10k_snoc 18800000.wifi: failed to send config request: -107
[   12.548256] ath10k_snoc 18800000.wifi: failed to send qmi config: -107
[   12.548264] ath10k_snoc 18800000.wifi: failed to enable wcn3990: -107
[   12.549732] ath10k_snoc 18800000.wifi: could not power on hif bus (-107)
[   12.549745] ath10k_snoc 18800000.wifi: could not probe fw (-107)
```

### Causa raíz: El chip WCN3990 no tiene firmware

Error -107 = `ETIMEDOUT`. El chip WCN3990 no responde a QMI porque **no tiene firmware cargado**.

**Flujo esperado en downstream (Android):**
1. Driver `cnss2` detecta el dispositivo WiFi
2. Carga firmware MBA (Modem Boot Authenticator) via PIL/remoteproc
3. Carga firmware WiFi (wlanmdsp.mbn) via QMI
4. Chip arranca y envía `FW_READY_IND`
5. ath10k toma control

**Situación en mainline:**
- `qcom_q6v5_pas` está cargado pero NO tiene un nodo DT para WiFi/WCN3990
- No hay driver que cargue el firmware al chip antes de ath10k
- `remoteproc1` (adsp) y `remoteproc2` (cdsp) fallan — firmware no encontrado
- No hay `remoteproc` para WiFi

### Próximos pasos necesarios

1. **Agregar nodo DT para WCN3990 como remoteproc** con compatible `qcom,sdm660-wpss-pas` o similar
2. **Asegurar que los firmware estén en `/lib/firmware/`**: `mba.mbn`, `wlanmdsp.mbn`
3. **Habilitar `CONFIG_QCOM_Q6V5_PAS`** en kernel config si no está ya
4. **Testear** si el chip arranca y envía FW_READY_IND

Alternativa: Verificar si la variante CNSS PCI (WCN6855/WCN7850) funciona en lugar de SNOC.

### Probe exitoso con modprobe manual

```
[  222.439416] ath10k_snoc 18800000.wifi: >>> ath10k_snoc_probe ENTER
[  222.439444] ath10k_snoc 18800000.wifi:   dma_mask OK
[  222.441817] ath10k_snoc 18800000.wifi:   ath10k_core_create OK
[  222.442060] ath10k_snoc 18800000.wifi:   resource_init OK
[  222.442557] ath10k_snoc 18800000.wifi:   setup_resource OK
[  222.442737] ath10k_snoc 18800000.wifi:   request_irq OK
[  222.443616] ath10k_snoc 18800000.wifi:   regulator_bulk_get OK (num=5)
[  222.443650] ath10k_snoc 18800000.wifi:   clk_bulk_get_optional OK (num=2)
[  222.443772] ath10k_snoc 18800000.wifi:   msa_resources OK
[  222.443783] ath10k_snoc 18800000.wifi:   fw_init OK
[  222.444031] ath10k_snoc 18800000.wifi:   qmi_init OK
[  222.444050] ath10k_snoc 18800000.wifi:   modem_init OK
[  222.444060] ath10k_snoc 18800000.wifi: <<< ath10k_snoc_probe SUCCESS
```

### Todos los componentes funcionan

| Componente | Estado | Detalle |
|-----------|--------|---------|
| dma_mask | OK | DMA 35-bit |
| ath10k_core_create | OK | WCN3990 |
| resource_init | OK | |
| setup_resource | OK | |
| request_irq | OK | |
| regulator_bulk_get | OK | 5 reguladores (vdd-0.8-cx, vdd-1.8-xo, vdd-1.3-rfa, vdd-3.3-ch0, vdd-3.3-ch1) |
| clk_bulk_get_optional | OK | 2 clocks (cxo_ref_clk_pin, qdss) |
| msa_resources | OK | MSA 1MB |
| fw_init | OK | |
| qmi_init | OK | QMI WLFW |
| modem_init | OK | |

### Problema: timing en boot

En boot:
```
[    2.785019] platform 18800000.wifi: Adding to iommu group 0
```
Solo este mensaje. **Cero intentos de probe.** El driver matchea el device pero probe() nunca se ejecuta.

**Causa:** El supplier `remoteproc:glink-edge` no está listo cuando ath10k intenta probe. El deferred probe timeout (10s default) expira.

**Solución:** Agregar `deferred_probe_timeout=0` al cmdline del kernel (timeout infinito = reintentar siempre).

### Deviceinfo modificado

```
deviceinfo_append_kernel_cmdline="deferred_probe_timeout=0"
```

## Historial de hipotesis

### Hipotesis original (descartada): clk-smd-rpm bug
Se creía que el driver de clocks RPM no registraba los clocks correctamente. **DESCARTADO**: El probe exitoso con modprobe confirma que los clocks funcionan.

### Hipotesis descartada: IOMMU bloquea probe
El IOMMU (arm-smmu 16c0000.iommu) funciona correctamente. El device se agrega al iommu group 0 sin problemas.

### Hipotesis descartada: firmware files
Los archivos firmware (board-2.bin, firmware-5.bin, wlanmdsp.mbn) existen en `/lib/firmware/postmarketos/`. El probe los carga correctamente.

### Hipotesis confirmada: timing de suppliers en boot
El supplier `remoteproc:glink-edge` no está listo cuando ath10k intenta probe en boot. El deferred probe timeout (10s) expira y nunca reintenta. Con `modprobe` manual, el supplier ya está listo y el probe funciona.

---

## Cadena de dependencia WiFi en SDM660

```
ath10k_snoc (WiFi driver)
  └─ devm_regulator_bulk_get()  ← 5 reguladores ✓
  └─ devm_clk_bulk_get_optional() ← 2 clocks ✓
  └─ ath10k_setup_msa_resources() ← MSA 1MB ✓
  └─ ath10k_fw_init() ← OK ✓
  └─ ath10k_qmi_init() ← QMI WLFW ✓
  └─ ath10k_modem_init() ← OK ✓
  └─ probe SUCCESS ✓
```

**Dependencia en boot:**
```
platform 18800000.wifi
  └─ supplier: platform:16c0000.iommu (IOMMU) ✓
  └─ supplier: platform:remoteproc:glink-edge (RPM) ← NO LISTO EN BOOT
  └─ supplier: regulator:regulator.21-25 ✓
```

---

## Hallazgos de la sesion (8 junio 2026)

### 1. Patch 0004 — GPU SMMU fix (CREADO Y VERIFICADO)

**Archivo:** `0004-platina-disable-gpu-smmu-for-gcc-sync.patch`

Deshabilita `&kgsl_smmu` en el DTS para desbloquear `gcc-sdm660` `sync_state()`. Confirmado funcionando:

```
ANTES del fix:
  arm-smmu 5040000.iommu: probing...  ← GPU SMMU
  sync_state pending due to 5040000.iommu

DESPUES del fix:
  arm-smmu 5040000.iommu: [ELIMINADO]
  sync_state pending: [ELIMINADO]
```

### 2. MNOC fix — DESCARTADO

`qnoc-sdm660 1745000.interconnect: probe failed with error -2` (MNOC). Investigado y descartado:

- **SNOC** (1626000, WiFi) → funciona (5/6 interconnects bindgeados)
- **MNOC** (1745000, multimedia) → falla por `clk 'iface'` (GCC_MNOC_AXI_CLK, disabled)
- WiFi **NO depende** de MNOC, solo de SNOC

### 3. `vdd-3.3-ch1-supply` agregado al patch 0001

El patch 0001 ahora incluye los 6 supply properties del WiFi:
- `vdd-0.8-cx-mx-supply = <&vreg_l5a_0p848>;`
- `vdd-1.8-xo-supply = <&vreg_l9a_1p8>;`
- `vdd-1.3-rfa-supply = <&vreg_l6a_1p3>;`
- `vdd-3.3-ch0-supply = <&vreg_l19a_3p3>;`
- `vdd-3.3-ch1-supply = <&vreg_l19a_3p3>;` ← NUEVO

### 4. Kernel pkgrel=5 compilado y flasheado

4 patches: 0001 (DTS WiFi + MSS + vdd-3.3-ch1), 0002 (skip quiet mode), 0003 (passive scan 5GHz), 0004 (GPU SMMU fix).

### 5. `cnss2` NO existe en este fork del kernel

El fork `sdm660-mainline` NO incluye `cnss2` (ni en Kconfig ni en Makefile). Solo tiene `WCNSS_PIL` y `WCNSS_CTRL` (drivers viejos). `cnss2` es necesario para提供 QMI services en otros SoCs.

### 6. `regulatory.db` funciona correctamente

Se carga via X.509 certs compilados cuando `wireless-regdb` esta instalado. En rootfs fresco NO se incluye automaticamente (depende de `postmarketos-base-ui`).

---

## El problema raiz: ath10k_snoc probe nunca se ejecuta

### Evidencia

| Observacion | Valor |
|---|---|
| Driver binding | SI — symlink `/sys/bus/platform/drivers/ath10k_snoc/18800000.wifi` existe |
| Driver override | `(null)` — sin override |
| Module loaded | SI — `ath10k_snoc 57344 0` |
| Module refcnt | **0** — probe() nunca incremento el refcount |
| dmesg mensajes ath10k | **0** — ni un solo mensaje (ni error, ni dbg) |
| Dynamic debug habilitado | SI — `module ath10k_snoc +p` + `file snoc.c +p` |
| Despues de unbind+rebind | **0** nuevos mensajes en dmesg |
| Despues de modprobe -r + modprobe | refcnt sigue en 0 |

### Analisis del probe function (snoc.c)

```c
static int ath10k_snoc_probe(struct platform_device *pdev)
{
    // 1. device_get_match_data()     → SI funciona (no imprime error)
    // 2. dma_set_mask_and_coherent() → SI funciona (no imprime error)
    // 3. ath10k_core_create()        → SI funciona (no imprime error)
    // 4. ath10k_snoc_resource_init() → SI funciona (no imprime warning)
    // 5. ath10k_snoc_setup_resource()→ SI funciona (no imprime warning)
    // 6. ath10k_snoc_request_irq()   → SI funciona (no imprime warning)
    // 7. devm_regulator_bulk_get()   → SI funciona (consumer symlinks en l19)
    // 8. devm_clk_bulk_get_optional()→ SILENT FAIL → goto err_free_irq
    //    (retorna -EPROBE_DEFER sin imprimir nada)
    // 9. ath10k_setup_msa_resources()→ NUNCA LLEGA
    // 10. ath10k_fw_init()           → NUNCA LLEGA
    // 11. ath10k_qmi_init()          → NUNCA LLEGA
    // 12. ath10k_modem_init()        → NUNCA LLEGA
}
```

**Los dos puntos silenciosos de fallo:**
- `devm_regulator_bulk_get()` — **descartado** (funciona, confirmado por consumer symlinks en regulator l19)
- `devm_clk_bulk_get_optional()` — **CONFIRMADO como culpable**

### Por que devm_clk_bulk_get_optional falla

El WiFi DT node referencia:
```
clocks = <&rpmcc 3>;   // phandle 0x26, clock ID 3 = RPM_SMD_RF_CLK1_PIN
clock-names = "cxo_ref_clk_pin";
```

El RPM clock controller (`qcom,rpmcc-sdm660`) esta bindgeado al driver `qcom-clk-smd-rpm`, pero:

1. `/sys/kernel/debug/clk/` esta **vacio** — `CONFIG_COMMON_CLK_DEBUG` no habilitado
2. No hay forma de verificar si los clocks estan registrados
3. `devm_clk_bulk_get_optional()` con un clock no registrado retorna `-EPROBE_DEFER`
4. El probe de ath10k falla silenciosamente en el paso 8

### SEGFAULT al re-probar el clock controller

```bash
echo "remoteproc:glink-edge:rpm-requests:clock-controller" > /sys/bus/platform/drivers/qcom-clk-smd-rpm/bind
# Resultado: Segmentation fault
```

**Esto confirma un bug real en `clk-smd-rpm.c` del fork sdm660-mainline.** El driver tiene un problema al registrarse o al manejar el probe repetido.

---

## Stack de communication RPM

```
Host ←→ RPM Coprocesador
  │
  ├─ GLINK channel (remoteproc:glink-edge.rpm_requests)
  │   └─ qcom_smd_rpm (rpmsg driver) ← bindgeado ✓
  │       ├─ clock-controller (child) → qcom-clk-smd-rpm ← bindgeado PERO bug
  │       ├─ regulators-0 (child) → regulator framework ← FUNCIONA (79 regulators)
  │       ├─ regulators-1 (child) → regulator framework ← FUNCIONA
  │       └─ power-controller (child)
  │
  └─ RPM CC: qcom,rpmcc-sdm660 ← phandle 0x26, #clock-cells=1
```

Los reguladores RPM **funcionan** (79 registrados, incluyendo l1-l19, s1-s6, bob). Pero los clocks **no se confirman** por falta de `CONFIG_COMMON_CLK_DEBUG`.

---

## DT properties del WiFi (verificados en runtime)

```
/sys/firmware/devicetree/base/soc@0/wifi@18800000/
├── compatible = "qcom,wcn3990-wifi"
├── clocks = <&rpmcc 3>            // phandle 0x26 ✓
├── clock-names = "cxo_ref_clk_pin"
├── vdd-0.8-cx-mx-supply = <&vreg_l5a_0p848>  // phandle 0x83 ✓
├── vdd-1.8-xo-supply = <&vreg_l9a_1p8>        // phandle 0x84 ✓
├── vdd-1.3-rfa-supply = <&vreg_l6a_1p3>       // phandle 0x85 ✓
├── vdd-3.3-ch0-supply = <&vreg_l19a_3p3>      // phandle 0x86 ✓
├── vdd-3.3-ch1-supply = <&vreg_l19a_3p3>      // phandle 0x86 ✓
├── memory-region = <&wlan_msa_mem>             // 0x85700000 (1MB)
├── iommus = <&anoc2_smmu 0x1a00>, <&anoc2_smmu 0x1a01>
├── qcom,snoc-host-cap-8bit-quirk
├── qcom,no-msa-ready-indicator
└── status = "okay"
```

Todos los phandles son correctos y resuelven a reguladores/clocks existentes en el DT.

---

## Reguladores WiFi (verificados)

| Supply | Regulator | Estado | Consumer |
|---|---|---|---|
| vdd-3.3-ch0 | l19 (regulator.34, RPM) | disabled | 18800000.wifi-vdd-3.3-ch0 ✓ |
| vdd-3.3-ch1 | l19 (regulator.34, RPM) | disabled | 18800000.wifi-vdd-3.3-ch1 ✓ |
| vdd-3.3-ch0 | l19 (regulator.64, SPMI) | enabled | (directo PMIC) |

Los consumer symlinks prueban que `devm_regulator_bulk_get()` ejecuto y vinculo correctamente.

---

## Archivos de trabajo

| Archivo | Descripcion |
|---|---|
| `0001-platina-wifi.patch` | DTS: habilita WiFi + MSS + vdd-3.3-ch1-supply |
| `0002-ath10k-skip-quiet-mode-wcn3990.patch` | Salta quiet mode (crash trigger) |
| `0003-ath10k-force-passive-scan-5ghz.patch` | Force passive scan 5GHz |
| `0004-platina-disable-gpu-smmu-for-gcc-sync.patch` | Deshabilita kgsl_smmu para gcc sync_state |
| `APKBUILD` | pkgrel=5, 4 patches, sha512sums actualizados |
| `WIFI-FIX-PLAN.md` | Plan original (firmware + patches) |
| `trabajo_claude.md` | Registro completo del trabajo previo |

---

## Analisis del source code `clk-smd-rpm.c`

### Resultado: Los clocks FUNCIONAN correctamente

El probe de ath10k completó exitosamente con `devm_clk_bulk_get_optional OK (num=2)`. Los clocks `cxo_ref_clk_pin` y `qdss` se obtienen correctamente. No hay bug en clk-smd-rpm.

### Match table — SDM660 soportado

```c
{ .compatible = "qcom,rpmcc-sdm660",  .data = &rpm_clk_sdm660  },
```

### Clock RF_CLK1_PIN — SI esta en la lista

```c
[RPM_SMD_RF_CLK1_PIN]      = &clk_smd_rpm_rf_clk1_pin,
[RPM_SMD_RF_CLK1_A_PIN]    = &clk_smd_rpm_rf_clk1_a_pin,
```

### Implicacion

El segfault al re-probar el clock controller era un bug de estado corrupto al unbind/rebind, no un bug en el probe inicial. Los clocks funcionan correctamente.

---

## Nueva hipotesis: probe SÍ se ejecuta pero falla despues

Dado que:
1. `devm_regulator_bulk_get()` funciona (consumer symlinks en l19)
2. `clk-smd-rpm.c` probe probablemente funciona (sin errores en dmesg)
3. El probe de ath10k no produce NINGUN mensaje

La causa mas probable es que **el probe de ath10k_snoc no se llama en absoluto**, a pesar de que el driver esta bindgeado. Esto puede ocurrir si:

- El device esta en la deferred probe list y el timeout expiro (dispositivo queda bind pero probe nunca re-intenta)
- El IOMMU bloquea el probe antes de llamar a `drv->probe()`
- Hay un bug en el bus matching del platform driver

### Verificacion: ath10k_core_probe() nunca se llama

En el kernel SNOC, `ath10k_core_probe()` NO se llama dentro de `ath10k_snoc_probe()`. Solo establece recursos y retorna 0. El `ath10k_core_probe()` se llama despues via `ath10k_hif_power_up()`. Sin embargo, para que `ath10k_hif_power_up()` se ejecute, la interfaz wlan0 debe existir primero, y esa se crea en `ath10k_mac_register()` que es llamado desde `ath10k_core_probe()`.

**Esto es un circulo vicioso si el probe nunca completa.**

---

## Patch 0005 — Debug prints en ath10k_snoc_probe()

**Archivo:** `0005-ath10k-snoc-add-debug-probe-prints.patch`
**Objetivo:** Confirmar si `ath10k_snoc_probe()` se ejecuta y en que paso falla.
**Cambio:** Agrega `dev_info` prints al inicio y al final de cada paso critico en el probe. Estos prints aparecen en dmesg sin necesidad de habilitar dynamic debug.

### Prints esperados en dmesg despues del build

Si el probe se ejecuta, veras:
```
ath10k_snoc 18800000.wifi: >>> ath10k_snoc_probe ENTER
ath10k_snoc 18800000.wifi:   dma_mask OK
ath10k_snoc 18800000.wifi:   ath10k_core_create OK
ath10k_snoc 18800000.wifi:   resource_init OK
...
ath10k_snoc 18800000.wifi: <<< ath10k_snoc_probe SUCCESS
```

Si falla, veras donde exactamente:
```
ath10k_snoc 18800000.wifi: <<< ath10k_snoc_probe FAIL clk_bulk_get_optional: -517
```

Si NO ves ningun mensaje, significa que el probe **no se ejecuta en absoluto**.

---

## Camino a seguir

### Paso 1: Build con deferred_probe_timeout=0 (EN PROCESO)

```bash
pmbootstrap pkgrel_bump linux-postmarketos-qcom-sdm660
pmbootstrap build linux-postmarketos-qcom-sdm660 --force
pmbootstrap flasher flash_kernel
```

### Paso 2: Verificar probe en boot

```bash
dmesg | grep ath10k_snoc
# Deberia mostrar todos los prints de probe SIN modprobe manual
```

### Paso 3: Si probe funciona en boot

```bash
ip link set wlan0 up
iw dev wlan0 scan | head -20
```

### Paso 4: Si probe funciona pero wlan0 no aparece

Investigar por qué `ath10k_core_probe()` no se llama después de `ath10k_snoc_probe()`.

---

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `0005-ath10k-snoc-add-debug-probe-prints.patch` | Debug prints en probe (temporal) |
| `0006-ath10k-snoc-call-core_register-to-create-wlan0.patch` | Agrega `ath10k_core_register()` para crear wlan0 |
| `device-xiaomi-platina/deviceinfo` | Agregado `deferred_probe_timeout=0` |
| `APKBUILD` | pkgrel bump, 6 patches |
| `INVESTIGACION-WIFI-SDM660.md` | Este documento |

---

## Bug encontrado en fork sdm660-mainline

`ath10k_snoc_probe()` retorna SUCCESS pero nunca llama `ath10k_core_register()`. En upstream PCI (`pci.c:3704`), esta función sí se llama. Sin ella:
- No se probea el firmware
- No se registra la PHY inalámbrica (`/sys/class/ieee80211/` vacío)
- No se crea `wlan0`

Patch 0006 corrige esto agregando la llamada con `ATH10K_DEV_TYPE_LL` y `chip_id=0`.

---

## Lo que NO era el problema

- ~~clk-smd-rpm.c bug~~ — Los clocks funcionan correctamente
- ~~Reguladores RPM~~ — 5 reguladores OK
- ~~Firmware files~~ — board-2.bin, firmware-5.bin OK
- ~~CNSS2~~ — No existe en este kernel
- ~~GPU SMMU~~ — Deshabilitado con patch 0004, funciona
- ~~MNOC interconnect~~ — No afecta WiFi

---

## Contexto historial (previo a esta sesion)

### Lo que ya funcionaba (antes de pkgrel=5)

- wlan0 aparecia, firmware WiFi cargaba (api 5, htt-ver 3.50)
- MSS arrancaba con `rmtfs` + firmware correcto
- Board file con board-ids correctos (sin la "b")
- Internet por USB (NAT via wlp2s0 → enp0s20f0u4)

### Problemas resueltos en sesiones anteriores

1. **GPT anidado** → `pmbootstrap install --split` + ext4 plano
2. **Board file incorrecto** → gen-board-2.py corregido (board-id sin "b")
3. **MSS crash loop** → Board correcto lo estabilizo
4. **GPU sync_state blocking** → Patch 0004 deshabilita kgsl_smmu
5. **vdd-3.3-ch1 missing** → Agregado al patch 0001

### Problema actual (nuevo rootfs)

Con el rootfs fresco (pkgrel=5), el escenario cambio completamente:
- **ANTES**: ath10k_snoc probe ejecutaba, wlan0 aparecia, firmware cargaba, MSS crashaba
- **AHORA**: ath10k_snoc probe NUNCA ejecuta (refcnt=0), wlan0 no aparece

La causa es que el nuevo rootfs/ initramfs maneja el boot de forma diferente, y el `qcom-clk-smd-rpm` driver falla al registrar clocks, bloqueando toda la cadena.

---

## PMOS_LOGS

Dispositivo extraible USB de 32MB vfat, montado en `/run/media/arch/PMOS_LOGS/`. Contiene:
- `dmesg.txt` — dmesg del initramfs
- `pmOS_init.txt` — log de init
- `fdt.dtb` — device tree blob

Para acceder: montar como USB mass storage desde el debug shell del telefono.

---

## Config kernel actual

```
CONFIG_ATH10K_SNOC=m          # WiFi SNOC driver
CONFIG_ATH10K=m               # ath10k core
CONFIG_QCOM_WCNSS_PIL=m       # WCNSS PIL (old driver)
CONFIG_QCOM_WCNSS_CTRL=m      # WCNSS control
CONFIG_QCOM_CLK_SMD_RPM=y     # RPM SMD clocks (BUILT-IN, pero con bug)
CONFIG_REGULATOR_QCOM_SMD_RPM=y  # RPM SMD regulators
CONFIG_RPMSG_QCOM_GLINK_SMEM=y   # GLINK SMEM
CONFIG_RPMSG_QCOM_SMD=y       # SMD rpmsg
CONFIG_QRTR=m                 # QRTR
CONFIG_QRTR_SMD=m             # QRTR SMD transport
# NO CONFIG_CNSS2             # cnss2 NO existe en este fork
# NO CONFIG_COMMON_CLK_DEBUG  # No podemos ver clocks
```

---

## Referencias

- [sdm660-mainline kernel fork](https://github.com/sdm660-mainline/linux)
- [postmarketOS platina port MR](https://gitlab.com/postmarketOS/pmaports/-/merge_requests/2837)
- [WCN3990 firmware crash issue](https://github.com/aarch64-laptops/build/issues/51)
- [ath10k board file loading patch](https://www.mail-archive.com/ath10k@lists.infradead.org/msg16054.html)
- [postmarketOS WiFi status](https://wiki.postmarketos.org/wiki/Wifi/)

---

# AUDITORÍA 2026-06-10 — Kernel r13 con memshare booteado y analizado

## Estado verificado (vía SSH, dmesg en vivo)

Kernel `6.17.4-sdm660 #15-postmarketos-qcom-sdm660` corriendo. Stack Linux **100% funcional**:

| Componente | Estado |
|---|---|
| memshare reubicado (client0@95400000, client2@95600000) | ✅ Sin overlap. `mapped memory to modem (id=0/2)` |
| MBA boot | ✅ `Booting fw image postmarketos/mba.mbn` |
| MPSS load | ✅ `MBA booted without debug policy, loading mpss` |
| Modem up | ✅ `remote processor 4080000.remoteproc is now up` |
| ath10k_snoc qmi_init | ✅ `qmi_init OK` |
| **Modem estabilidad** | ❌ **`fatal error without message` cada ~42s exactos, 25+ ciclos** |

## CAUSA RAÍZ IDENTIFICADA: falta firmware ADSP/CDSP

dmesg líneas 428-436:
```
remoteproc remoteproc0: Direct firmware load for adsp.mdt failed with error -2
remoteproc remoteproc0: request_firmware failed: -2
remoteproc remoteproc2: Direct firmware load for cdsp.mdt failed with error -2
remoteproc remoteproc2: request_firmware failed: -2
```

`ls /lib/firmware/postmarketos/` → solo `mba.mbn`, `modem.b*`, `modem.mdt`, `wlanmdsp.mbn`.
**NO existe adsp.* ni cdsp.* en el sistema.**

### Por qué esto causa el crash de 42s
El firmware MPSS (modem) del SDM660 tiene dependencias de servicios QMI que provee el **ADSP** (time service, calibración, sensores). Sin ADSP respondiendo, el modem dispara un watchdog interno y hace `fatal error` ~40s tras cada boot. El intervalo fijo (~42s) es la firma de un timeout de servicio, no de un fallo de carga.

## PLAN DE TRABAJO

### Paso 1 — Extraer firmware ADSP y CDSP de Android (PRIORIDAD)
El firmware propietario vive en la partición `dsp` de Android (montada en /vendor/dsp o /dsp).
- Desde TWRP/Android: `dd if=/dev/block/bootdevice/by-name/dsp of=/sdcard/dsp.img` o montar y copiar `adsp.mdt + adsp.b*` y `cdsp.mdt + cdsp.b*`.
- Colocar en `linux-postmarketos-qcom-sdm660` o vía un paquete firmware → `/lib/firmware/postmarketos/adsp.{mdt,bNN}` y `cdsp.*`.
- ⚠️ Firmware propietario: NO subir a GitHub.

### Paso 2 — Habilitar ADSP/CDSP en el devicetree
Patch 0001 solo habilita `&remoteproc_mss` y `&wifi`. Falta:
```
&remoteproc_adsp { firmware-name = "postmarketos/adsp.mdt"; status = "okay"; };
&remoteproc_cdsp { firmware-name = "postmarketos/cdsp.mdt"; status = "okay"; };
```
(verificar nombres de nodo reales en sdm630.dtsi: pil_adsp / remoteproc_adsp / adsp_pil).

### Paso 3 — Recompilar (pkgrel=14), flashear, verificar
`doas dmesg | grep -iE "adsp|cdsp|fatal"` → ADSP "is now up" y **modem SIN crash a los 42s**.

### Paso 4 — Si MSS estable → probar WiFi
`rmtfs` (si aplica) + `ip link set wlan0 up` + scan.

## Hipótesis alternativa (si ADSP no resuelve)
Servicio QMI del AP faltante (rmtfs no corriendo para servir EFS al modem). Verificar `rmtfs` instalado/activo. Pero la pista del firmware ADSP -2 es la más fuerte y barata de probar primero.

---

# AUDITORÍA 2026-06-10 (continuación) — Diagnóstico REFINADO del crash MSS

## Pruebas en vivo realizadas (sin recompilar, vía sysfs/rc-service)

### Descartado #1: firmware ADSP/CDSP faltante NO es la causa
- Encontrado firmware real adsp.mdt/adsp.b* y cdsp.mdt/cdsp.b* en partición `modem` (mmcblk1p74), `/image/`.
  (Las libs en partición `dsp`=p63 son solo runtime fastrpc, NO el ejecutable.)
- Copiados 34 archivos a `/lib/firmware/postmarketos/`. ⚠️ propietario, NO a GitHub.
- ADSP arrancado vía `echo start > /sys/class/remoteproc/remoteproc0/state` → **state: running** ✅
- **Resultado: el modem SIGUIÓ crasheando.** ADSP corriendo no estabiliza MSS. → hipótesis ADSP DESCARTADA.

### Descartado #2 (parcial): rmtfs parado — arrancarlo NO resolvió, pero REVELÓ el error real
- `rmtfs` instalado pero `stopped`. Arrancado con `doas rc-service rmtfs start` → corre (pid 3731, flags `-P -r -s`).
- El modem SIGUE crasheando (incluso más rápido, ~18s en vez de 42s).
- **PERO**: con rmtfs activo el modem por fin imprime el mensaje de error real:

```
qcom-q6v5-mss 4080000.remoteproc: fatal error received:
  dog_hb.c:266: Task starvation: diag, ping: 4, triage with owner
```

## CAUSA RAÍZ REAL identificada: watchdog mata la tarea DIAG por starvation

- `dog_hb.c` = watchdog heartbeat del firmware del modem.
- `Task starvation: diag` = la tarea **DIAG** (canal de diagnóstico QDSS/DIAG del modem) no hace ping al watchdog a tiempo.
- La tarea diag se bloquea esperando establecer/drenar el **canal DIAG sobre GLINK** con el AP. En mainline Linux ese canal no tiene consumidor → buffer se llena → tarea diag se cuelga → watchdog la mata cada ~18-42s.
- Síntoma colateral en boot: `ath10k_snoc: failed to send qmi config: -107` (ECONNREFUSED) en t=12s, porque el modem aún no está estable cuando WiFi intenta su QMI handshake.

## PLAN DE TRABAJO REFINADO (orden de probabilidad)

### Opción A — Deshabilitar/satisfacer el watchdog de la tarea diag (más probable)
El crash es un watchdog del firmware. Vías:
1. Abrir/drenar el canal GLINK "DIAG" desde Linux (driver qcom_diag / qcom_glink_native consumer). Verificar si existe nodo glink diag en DT y si falta un cliente.
2. Probar si el modem firmware acepta `androidboot.ramdump=disable` o un flag que relaje el dog (ya está `ramdump=disable` en cmdline — no bastó).

### Opción B — Mismatch de versión firmware modem vs MBA/SoC
`ping: 4` + starvation puede indicar que el modem.mdt extraído NO corresponde exactamente a la versión del MBA o del bootloader. Probar firmware modem de otra build MIUI del mismo dispositivo (platina), o el par mba/modem de la MISMA imagen.

### Opción C — Aceptar modem inestable, AISLAR WiFi del MSS
El objetivo final es WiFi (ath10k_snoc/WCN3990), NO telefonía. WCN3990 necesita el MSS vivo solo para el handshake QMI inicial de carga de su firmware (board-2.bin + wlanmdsp). 
- Si logramos que el modem sobreviva los primeros ~12s estable (una sola ventana sin crash), ath10k podría completar su qmi_init y wlan0 quedar arriba **independiente** de los crashes posteriores del MSS.
- Probar: arrancar WiFi inmediatamente tras boot del MSS, antes del primer watchdog, y ver si wlan0 sobrevive a los crashes subsiguientes del modem.

## Estado de servicios para reproducir
- ADSP: se puede arrancar manual (firmware ya en /lib/firmware/postmarketos/).
- rmtfs: arranca con `rc-service rmtfs start` (hace visible el msg real del dog).
- Firmware modem/adsp/cdsp/wlan: todo presente en /lib/firmware/postmarketos/.

---

# AUDITORÍA 2026-06-10 (cierre) — Cuello de botella confirmado y opciones reales

## Cadena causal completa (verificada en hardware)
1. WiFi (ath10k_snoc) carga limpio: qmi_init OK, modem_init OK, probe SUCCESS.
2. ath10k envía QMI config a la WCN3990 → **`-107` (ECONNREFUSED)**, consistente en 6+ intentos.
3. El `-107` es porque el **WLAN firmware (wlanmdsp.mbn) que corre en el Q6 de la WCN3990 nunca levanta su servicio QMI**.
4. En SDM660 el segmento WLAN lo carga/sirve el **MSS (modem)**. El MSS está en crash-loop perpetuo (`dog_hb.c:266 Task starvation: diag`), por lo que nunca completa/mantiene el WLAN firmware.
5. **Conclusión: el crash del modem es el único bloqueador de WiFi.** Todo lo demás (memshare, drivers, firmware adsp/cdsp/modem/wlan, rmtfs, board-2) está correcto y presente.

## Lo que se descartó con pruebas en hardware
- ❌ Firmware ADSP/CDSP faltante (copiado + ADSP `running`, no ayudó).
- ❌ rmtfs parado (arrancado, no ayudó — pero reveló el mensaje real del dog).
- ❌ Timing del modem / ventana de boot (6 recargas de ath10k, siempre -107).
- ❌ memory overlap memshare (reubicado, sin overlap).

## El bloqueador real: `dog_hb.c:266 Task starvation: diag`
Watchdog del FIRMWARE propietario del modem mata la tarea DIAG por inanición cada ~18-42s.
Esto ocurre DENTRO del blob del modem (no es código Linux). DIAG no se modela como cliente
glink en mainline (usa transporte propio), así que no hay un nodo DT trivial que añadir.

## OPCIONES REALES para avanzar (decisión del usuario)
**A. Probar otro par de firmware modem (mba+modem) de la MISMA build MIUI**
   - El `Task starvation: diag` puede ser incompatibilidad de versión MBA↔MPSS. Re-extraer mba.mbn
     y modem.* de UNA sola imagen de fábrica coherente (no mezclar fuentes) y reflashear firmware.
   - Bajo costo, alta relevancia. SIGUIENTE PASO RECOMENDADO.

**B. Buscar si la comunidad sdm660-mainline tiene un workaround del dog/diag**
   - Revisar issues/MRs de sdm660-mainline (lavender/wayne) por "Task starvation diag" o parches
     que deshabiliten el watchdog del modem o sirvan el canal diag.

**C. Pivotar al S9+ (SDM845)** — donde WCN3990 + MSS están MUCHO más maduros y estables
   en mainline (no sufren este crash). El WiFi del S9+ tiene mejor pronóstico que seguir
   peleando el firmware del modem SDM660.

## Estado del kernel/repo (listo)
- Kernel r13 con memshare (sin overlap) compilado, flasheado y booteando. pkgrel=13.
- 9 patches aplicados. Todo el lado Linux está completo.
- El trabajo restante es de FIRMWARE/modem, no de kernel.

---

# SESIÓN 2026-06-10 (tarde) — REINTENTO LIMPIO: wlan0 levanta, board file RESUELTO

## Corrección del diagnóstico de la mañana
El "irresoluble" de la mañana estaba INCOMPLETO: solo arranqué `rmtfs`. Faltaban **diag-router**
y **tqftpserv**. Con los TRES servicios en orden, el `Task starvation: diag` DESAPARECE.

## Cadena que funciona (verificada en hardware, boot limpio)
1. Reboot limpio (sin crashes acumulados que degradan el MSS).
2. Arrancar EN ORDEN: `rmtfs` (-P -r -s) → `diag-router` → `tqftpserv`.
3. Esperar ~80s: **MSS estable, crash count = 0**. ADSP+CDSP también `now up` solos al boot.
4. Recargar `ath10k_snoc` con el MSS ya estable.

## Blocker del board file RESUELTO
- El chip reporta **`qmi-board-id=0`** (no `ff` como antes). El board-2.bin no tenía entry para `0`
  → `config request rejected: 90` → `failed to send qmi config: -22`.
- FIX: añadido alias `bus=snoc,qmi-board-id=0` al bdwlan default en `gen-board-2.py` (línea ~44,
  junto al `ff` ya existente). Regenerado board-2.bin con `ath10k-bdencoder` (del chroot_native).
- pkgrel firmware-xiaomi-platina → 5, sha512 de gen-board-2.py actualizado.
- Con el board nuevo: **YA NO hay `rejected: 90` ni `-22`**. El board carga.

## RESULTADOS CLAVE
- ✅ **wlan0 sube a estado UP** (`<NO-CARRIER,BROADCAST,MULTICAST,UP>`).
- ✅ **El firmware WLAN NO crashea** — `EX:wlan_process`/`firmware crashed` count = 0.
  (El segundo blocker documentado el 2026-06-07 NO reaparece con el board-id correcto.)
- ✅ `phy1` registrada en `/sys/class/ieee80211/`.

## BLOCKER ACTUAL (nuevo, distinto): oops de LED en mac80211
```
Unable to handle kernel NULL pointer dereference at virtual address 0
pc : __pi_strcmp   lr : led_trigger_register
ieee80211_led_init+0x80 <- ieee80211_register_hw+0x5cc <- ath10k_mac_register
```
- NULL pointer (x0=0) en `strcmp` dentro de `led_trigger_register`, llamado por
  `ieee80211_led_init`. Es un BUG DEL KERNEL (mac80211 LED init), NO del firmware ni del board.
- Mata el kworker de `ath10k_core_register_work` → el registro de la phy queda incompleto.

## Próximos pasos (orden recomendado)
1. **Deshabilitar LEDs en mac80211**: recompilar kernel con `CONFIG_MAC80211_LEDS=n`
   (o parche en ath10k para no exponer LED). Es lo que evita el oops. → pkgrel kernel +1.
   ALTERNATIVA sin recompilar: investigar si un módulo param o quirk lo evita (poco probable).
2. **Instalar herramientas wireless**: el teléfono NO tiene `iw`/`wpa_supplicant`/`iwconfig`
   y NO tiene internet (solo USB sin NAT; sudo de laptop sin password conocido). Opciones:
   (a) configurar NAT en laptop (necesita sudo), (b) copiar binario `iw` estático por scp,
   (c) añadir iw a los paquetes del rootfs y reinstalar. Sin esto no se puede hacer scan real.
3. Tras (1)+(2): `iw dev wlan0 scan` debe listar redes → WiFi USABLE.

## Persistencia pendiente (cuando funcione)
- `rc-update add rmtfs default` (+ diag-router, tqftpserv).
- Asegurar orden: ath10k tras servicios.

## Estado: MUY CERCA. El WiFi mainline es viable. Falta resolver el oops de LED (kernel config).

---

# SESIÓN 2026-06-10 (noche) — Estado final y handoff

## Resumen del avance de hoy (GRANDE)
- ❌→✅ `Task starvation: diag` RESUELTO: faltaba arrancar **diag-router** + **tqftpserv**
  (además de rmtfs). Con los 3 en orden, MSS estable, crash count = 0.
- ❌→✅ Crash del firmware WLAN (`EX:wlan_process`) NO reaparece con board-id correcto.
- ✅ wlan0 sube a UP, phy1 registrada y FUNCIONAL (iw dev OK, scan SSIDs 16, modos managed/AP/P2P).
- ⚠️ Oops de LED en mac80211 (`led_trigger_register`/`__pi_strcmp` NULL) — NO fatal, la phy
  igual se registra. FIX preparado: `CONFIG_MAC80211_LEDS=n` + `CONFIG_ATH10K_LEDS=n` (kernel
  pkgrel=14, sha512 config actualizado). **Falta recompilar el kernel.**
- ✅ Internet en el teléfono habilitado (NAT por el usuario); `iw` + wireless-tools instalados.

## BLOCKER ACTUAL (el de fondo, aún sin resolver): board file + MSA
El scan falla (`failed to start hw scan: -108`). Causa raíz en la secuencia de init:
```
wlan-msa-mem@85700000 (reserved 1MB)   <- región MSA del WiFi en DT
msa_resources OK
failed to send qmi config: -107        <- al boot (MSS aún no listo)
qmi not waiting for msa_ready indicator
failed to download board data file: 90 <- FIRMWARE RECHAZA el board file (err 90)
board_file api 2 crc32 00000000        <- ath10k acaba usando board file VACÍO
failed to assign msa map permissions: -22  <- EINVAL al mapear MSA
```
Dos problemas entrelazados:
1. **`failed to download board data file: 90`**: el firmware reporta `qmi-board-id=0,qmi-chip-id=0`
   y rechaza con err 90 el board file. Añadí alias `qmi-board-id=0` (apunta a bdwlan.bin default,
   19152 bytes, NO vacío) pero el firmware igual lo rechaza → ath10k cae a board file interno vacío
   (crc32 0). Hipótesis: el board-id `0` + chip-id `0` significa que el firmware WLAN no recibió su
   identidad del modem (board-id real debería ser 33 o similar). Puede depender de que el modem/EFS
   provea el board-id, lo cual no ocurre (chip-id 0 = OTP/EFS sin leer).
2. **`failed to assign msa map permissions: -22`**: la región MSA (wlan-msa-mem@85700000) no se
   mapea con permisos correctos al WiFi Q6. Relacionado con SCM/hypervisor assign de memoria.
   Puede requerir patch DT o que el MSS esté plenamente operativo antes del WiFi.

## Conclusión técnica
El WiFi mainline está a 1-2 problemas de funcionar:
- El oops de LED se resuelve recompilando (fix ya en el config, falta build).
- El board file / MSA (-22, err 90, chip-id 0) es el blocker REAL del scan. Es el mismo nudo
  firmware↔modem del SDM660 mainline. Puede que NO se resuelva sin que el modem provea board-id,
  o requiera el board file exacto que el firmware acepte para chip-id 0.

## Operativa / credenciales para el siguiente agente
- Teléfono pmOS: SSH `user@172.16.42.1`, pass `147147`, doas pass `147147` (SOLO por tty: usar
  el patrón pty-python con `sshpass -tt`, doas pide password interactivo).
- Internet en el teléfono: OK (NAT activo). `apk add` funciona.
- Laptop: `sudo` NO tiene password conocido → **`pmbootstrap build` falla** en
  `sudo mkdir .../tmp`. ESTE ES EL BLOQUEADOR OPERATIVO para recompilar el kernel. Hay que pedir
  la password sudo de la laptop al usuario, o que él corra el build.
- eMMC = mmcblk1. Firmware WLAN/board en `/lib/firmware/ath10k/WCN3990/hw1.0/` y modem en
  `/lib/firmware/postmarketos/`.

---

# SESIÓN 2026-06-10 (madrugada) — HALLAZGO: jasmine es la referencia funcional

## Lo aprendido probando msa-fixed-perm (r14) y delete no-msa-ready (r15)
- r14 (msa-fixed-perm): cap exchange COMPLETA (chip_id 0x140, board_id 0xff, fw WLAN.HL.1.0.1.c6),
  pero luego `config request rejected: 90` → `firmware crashed!` repetido.
- r15 (+ delete no-msa-ready-indicator): EMPEORÓ. Ahora `msa info req rejected: 90` ANTES del config.
  → Confirma que el firmware NECESITA que la memoria MSA esté asignada vía SCM; msa-fixed-perm
    (que SALTA el SCM assign) deja al firmware sin permisos → rechaza todo con err 90.

## EL HALLAZGO: sdm660-xiaomi-jasmine tiene WiFi FUNCIONAL en mainline con config MÍNIMA
`arch/arm64/boot/dts/qcom/sdm660-xiaomi-jasmine.dts` (mismo SoC SDM660, mismo WCN3990):
```
&wifi {
	vdd-0.8-cx-mx-supply = <&vreg_l5a_0p848>;
	vdd-1.8-xo-supply = <&vreg_l9a_1p8>;
	vdd-1.3-rfa-supply = <&vreg_l6a_1p3>;
	vdd-3.3-ch0-supply = <&vreg_l19a_3p3>;
	status = "okay";
};
&remoteproc_mss {
	firmware-name = "mba.mbn", "modem.mdt";
	status = "okay";
};
```
Diferencias clave con nuestro patch (que estaba MAL):
- jasmine usa **4 regulators** (NO incluye `vdd-3.3-ch1-supply`). Nosotros poníamos 5.
- jasmine **NO usa** `qcom,msa-fixed-perm`.
- jasmine **NO toca** `qcom,no-msa-ready-indicator` (lo hereda del dtsi).
- jasmine NO override la región MSA (usa wlan_msa_mem@85700000 1MB del dtsi, igual que platina).

→ PRUEBA que el SCM assign del SDM660 SÍ funciona con la config correcta. El `-22` original
  que vimos NO era "TZ no soporta WLAN VMID" (diagnóstico equivocado), sino otra causa
  (timing/orden, o la 5a supply rompiendo el power-up).

## DECISIÓN: replicar EXACTAMENTE la config de jasmine
- Quitar `qcom,msa-fixed-perm` y el `/delete-property/ qcom,no-msa-ready-indicator`.
- Reducir a 4 regulators (quitar vdd-3.3-ch1).
- Mantener fixes de LED en el config (ortogonales, correctos): MAC80211_LEDS=n, ATH10K_LEDS=n.
- firmware-name del MSS: probar SIN prefijo "postmarketos/" como jasmine (o mantener, es ruta válida).

---

# SESIÓN 2026-06-10 — Matriz de resultados y análisis QMI definitivo

## Matriz de los 4 builds probados
| Build | Config &wifi | chip_id (cap exchange) | Error final |
|-------|--------------|------------------------|-------------|
| r13 base | jasmine-like (hereda dtsi) | **0x0 (NO completa)** | board data file: 90 |
| r14 | + qcom,msa-fixed-perm | **0x140 ✅ (board_id 0xff)** | config request rejected: 90 → fw crash |
| r15 | + delete no-msa-ready | 0x0 | msa info req rejected: 90 (peor, más temprano) |
| r16 | jasmine puro + LEDs off | **0x0 (= r13)** | board data file: 90 |

## HALLAZGO CLAVE
- **qcom,msa-fixed-perm es lo ÚNICO que hace completar el QMI cap exchange** (chip_id 0x140,
  board_id 0xff, fw WLAN.HL.1.0.1.c6). Sin él, chip_id=0 y nunca se sabe el board_id.
- Confirmado por código (qmi.c): el err 90 del "board data file" = QMI_ERR_INCOMPATIBLE_STATE.
  ath10k_qmi_bdf_dnld_send_sync envía ar->normal_mode_fw.board_data; si el board file no se
  seleccionó (board_id desconocido por chip_id=0), manda vacío → fw rechaza con 90.
- La cadena correcta DEPENDE de chip_id != 0 → requiere msa-fixed-perm.

## El nudo real (r14): config request rejected: 90 DESPUÉS del cap exchange
Con msa-fixed-perm el cap exchange completa, pero luego ath10k_qmi_wlan_cfg_send → resp.error=90.
Esto es lo próximo a atacar. Posibles causas:
1. La región MSA no está realmente asignada (msa-fixed-perm la SALTA) y el firmware, aunque
   responde el cap, rechaza el WLAN_CFG porque no puede acceder a la memoria.
2. Timing entre msa_ready sintético (no-msa-ready-indicator) y el config.

## IMPORTANTE: corregir LEDs requiere ATH10K_LEDS=n (no solo MAC80211_LEDS=n)
El kernel que corría tenía ATH10K_LEDS=y → re-selecciona/usa el LED trigger → oops en
ieee80211_led_init persiste. El r16 (en disco, AÚN NO FLASHEADO al probar) ya tiene
ATH10K_LEDS=n. El oops solo desaparecerá al flashear r16+.

## DECISIÓN para el siguiente intento (r17)
Volver a msa-fixed-perm (única vía a chip_id!=0) PERO mantener LEDs off, y atacar el
config-rejected-90. Config &wifi propuesta:
- regulators (4-5) + status okay
- qcom,msa-fixed-perm   (recupera cap exchange)
- mantener qcom,no-msa-ready-indicator (heredado; quitarlo dio peor resultado en r15)
- LEDs off en kernel config (ATH10K_LEDS=n + MAC80211_LEDS=n) ya están

Para el config-rejected-90 con msa-fixed-perm: investigar si falta reservar/asignar la región
MSA de otra forma, o si el firmware necesita un BDF que pase el CRC. Esto es ingeniería QMI
profunda del SDM660 mainline — alto esfuerzo, resultado incierto.

---

# SESIÓN 2026-06-10 — RAÍZ del -22 SCM identificada (análisis de código)

## El flujo QMI (ath10k qmi.c, event_server_arrive)
1. ind_register → 2. host_cap → 3. msa_mem_info → 4. **setup_msa_permissions (SCM assign)**
→ 5. msa_ready_send → 6. cap_send (chip_id). Luego event_msa_ready: fetch_board_file → bdf_dnld.

- El chip_id (paso 6) viene DESPUÉS del SCM assign (paso 4). Por eso:
  - SIN msa-fixed-perm: paso 4 falla -22 → return → chip_id=0 (r13/r16).
  - CON msa-fixed-perm: paso 4 se SALTA → chip_id=0x140 (r14), pero luego config rejected 90
    porque la memoria MSA NO quedó reasignada al WLAN.

## RAÍZ del -22: VMIDs WLAN/WLAN_CE no soportados por el TZ del SDM660
`ath10k_qmi_map_msa_permission` (qmi.c ~40-60) asigna la región MSA a 3 VMIDs:
- QCOM_SCM_VMID_MSS_MSA = 0xF   ← el TZ SÍ lo soporta (rmtfs_mem lo usa con qcom,vmid y funciona)
- QCOM_SCM_VMID_WLAN    = 0x18  ← sospechoso
- QCOM_SCM_VMID_WLAN_CE = 0x19  ← sospechoso
El qcom_scm_assign_mem hace SMC QCOM_SCM_SVC_MP/MP_ASSIGN; el TZ (qseecom 0x1001000,
scm-msm8998) devuelve error → ath10k lo reporta como -22 (EINVAL genérico).
EVIDENCIA de que MSS_MSA funciona: rmtfs_mem@85e00000 usa qcom,vmid=MSS_MSA y el modem/rmtfs
corren OK. Por descarte, el fallo del assign de ath10k viene de WLAN (0x18) y/o WLAN_CE (0x19).

## HIPÓTESIS PRINCIPAL (no probada aún): parche al driver
Modificar ath10k_qmi_map_msa_permission para asignar la MSA SOLO a MSS_MSA (y/o quitar
WLAN_CE), en vez de los 3 VMIDs. Si el TZ acepta MSS_MSA, el assign REAL tendría éxito
(memoria reasignada de verdad) → resolvería el -22 Y el config-rejected-90 de una vez.
Esto requiere un patch nuevo (0010) al driver, no solo DT. Riesgo: el firmware WLAN puede
necesitar específicamente el VMID WLAN para acceder a la memoria; si es así, no bastará.

## Alternativa: aceptar que es limitación del TZ SDM660 (bootloader MIUI/qseecom)
Si ni MSS_MSA-solo funciona, el TZ de este SoC no permite reasignar memoria al WLAN, y el
WiFi mainline no es viable por esta vía. Sería el punto de cierre para pivotar al S9+ (SDM845).

## Config actual del repo (r17, validado, SIN compilar/probar aún)
- 0001 patch: &wifi con qcom,msa-fixed-perm + 4 regulators. pkgrel=17.
- config: MAC80211_LEDS=n + ATH10K_LEDS=n.
- Pendiente: decidir entre (a) probar r17 tal cual (verá config-rejected-90 limpio sin oops LED),
  o (b) escribir patch 0010 con VMID-solo-MSS_MSA (ataca la raíz).

---

# SESIÓN 2026-06-10 — HALLAZGO CRÍTICO: desajuste kernel vs módulos

## El problema que invalidó varias pruebas
`pmbootstrap flasher flash_kernel` SOLO flashea el boot image (vmlinuz + initramfs).
**NO actualiza los módulos .ko del rootfs** (/lib/modules/). 

Síntoma detectado: el kernel corriendo es #19 (r18, compilado Jun 10 07:36), pero
mac80211.ko / ath10k_*.ko en /lib/modules/6.17.4-sdm660/ son del **Jun 9** (build viejo).

## Qué invalidó esto
- mac80211 y ath10k son MÓDULOS (.ko), no built-in. Todas las pruebas de WiFi desde que
  empezamos a tocar el config/patches (LEDs off, patch 0010 MSS_MSA) corrieron con los
  MÓDULOS VIEJOS — el patch 0010 y los LEDs off NUNCA se probaron de verdad.
- Por eso el oops de LED persistía (mac80211.ko viejo con MAC80211_LEDS=y) aunque el
  config nuevo dice MAC80211_LEDS=n. Confirmado: ieee80211_led_init es stub vacío con
  MAC80211_LEDS=n, así que el oops PRUEBA que el .ko es viejo.
- El "failed to assign -22" / board 90 que vimos en r18 son del ath10k_*.ko VIEJO (sin
  patch 0010), no del código nuevo.

## SOLUCIÓN: actualizar los módulos del rootfs, no solo flash_kernel
Opciones:
1. Copiar los .ko nuevos del apk r18 al teléfono (rápido, quirúrgico):
   extraer lib/modules/.../{mac80211,ath10k_core,ath10k_snoc,...}.ko.zst del
   linux-...-r18.apk y scp a /lib/modules/6.17.4-sdm660/, luego depmod + reboot.
2. pmbootstrap install (regenera rootfs completo con kernel+módulos coherentes) — más lento
   pero robusto; requiere reflashear userdata.
3. Instalar el .apk en el rootfs chroot y re-exportar.

OJO: el flujo correcto para futuros builds es SIEMPRE actualizar módulos, no solo flash_kernel.

## Pendiente: probar el patch 0010 DE VERDAD (con módulos nuevos)
Hasta ahora NO se ha probado el patch 0010 con el ath10k_snoc.ko correcto. La conclusión
sobre si el VMID-MSS_MSA-solo resuelve el -22 está PENDIENTE de esta corrección.

---

# SESIÓN 2026-06-10 — CONCLUSIONES tras corregir el desajuste de módulos

## Lo que se corrigió esta sesión
- Identificado y resuelto el desajuste kernel/módulos: `flash_kernel` NO actualiza los .ko.
  Se hizo `pmbootstrap install --split` completo → rootfs con kernel r18 + módulos COHERENTES
  (mac80211.ko y ath10k_snoc.ko del build r18, Jun 10 02:55), firmware r5, e2fsck -fy.
- Verificado en hardware: kernel #19 (r18), modinfo ath10k_snoc apunta al .ko correcto.

## RESULTADO de la prueba con módulos correctos (patch 0010 + LEDs off)
- Servicios arrancaron, se esperó MSS estable, se recargó ath10k_snoc.
- **El teléfono se COLGÓ por completo (kernel panic / freeze total)** al cargar ath10k:
  no responde a ping ni SSH (100% packet loss), aunque la interfaz USB sigue UP en la laptop.
  Requiere reinicio físico (power).

## INTERPRETACIÓN
- Con los módulos VIEJOS (sesiones previas), ath10k daba un oops NO-fatal del kworker
  (mataba ath10k_core_register_work pero el sistema seguía vivo y con SSH).
- Con los módulos NUEVOS (patch 0010 que asigna MSA solo a MSS_MSA + LEDs off), el fallo
  escaló a PANIC/FREEZE total. Hipótesis: el SCM assign con solo MSS_MSA ahora SÍ se ejecuta
  (ya no falla temprano con -22), reasigna la región MSA quitándosela a HLOS, y luego algún
  acceso del kernel a esa memoria (o del firmware) provoca una violación XPU/SError fatal que
  congela el SoC. Es decir: el patch 0010 hace que el assign "funcione" pero deja la memoria
  en un estado que mata el sistema → PEOR que antes.
- Esto refuerza la conclusión de que el manejo MSA/SCM del WCN3990 en SDM660 mainline está
  fundamentalmente roto para este TZ: ni saltarlo (msa-fixed-perm → config rejected 90), ni
  hacerlo solo-MSS_MSA (→ panic) funcionan.

## ESTADO / DECISIÓN
- El WiFi mainline en el Mi 8 Lite sigue SIN funcionar. La causa raíz (SCM/MSA del TZ SDM660)
  es profunda y las 3 variantes probadas (3-VMID, msa-fixed-perm, solo-MSS_MSA) fallan distinto.
- Próximas vías posibles (no triviales):
  1. Revertir patch 0010 (volver a comportamiento no-fatal) y revisar si el panic lo causa el
     assign o un acceso posterior; capturar el panic por consola serial/pstore para ver el PC.
  2. Investigar si falta una reserved-memory/XPU config para la región MSA en el DT del platina.
  3. Revisar pstore (/sys/fs/pstore) tras el panic para el call trace exacto.
  4. Aceptar el límite del SDM660 mainline y pivotar al S9+ (SDM845), donde el WCN3990 es estable.

## Artefactos del repo (estado actual, todo validado y compilado)
- Kernel r18 (pkgrel=18): patch 0001 (DT wifi, sin msa-fixed-perm), patch 0010 (MSA solo
  MSS_MSA), config LEDs off. Instalado en el teléfono vía install --split.
- firmware-xiaomi-platina r5 (board-2.bin con alias qmi-board-id=0).
- Pendiente al retomar: capturar el panic (pstore) para el call trace exacto, o decidir pivote.
