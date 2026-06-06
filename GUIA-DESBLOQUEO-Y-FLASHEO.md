# Guía: Desbloqueo, Flasheo y Verificación del Modem — POCO F2 Pro (xiaomi-lmi)

> Checklist paso a paso para el "día del desbloqueo". Todos los comandos indican
> en qué máquina se corren: 💻 = tu laptop Arch · 📱 = el teléfono (vía SSH).

---

## ❓ ¿Necesito recovery personalizado (TWRP)?

**NO.** El método de instalación es `fastboot` (definido en `deviceinfo_flash_method="fastboot"`).
Se flashean las particiones `boot` y `system` directamente desde el modo **fastboot**,
que es parte del **bootloader**, no del recovery.

- ✅ Solo necesitas: **bootloader desbloqueado** + `fastboot` instalado.
- ✅ El recovery **stock se queda como está** — no lo tocas.
- ❌ TWRP NO hace falta (solo serviría para el método "recovery zip", que no usamos).

---

## FASE 0 — Esperar el desbloqueo (EN CURSO)

Xiaomi asignó ~360 horas (~15 días) de espera tras vincular la cuenta Mi.

### Cómo ver cuánto falta
📱 **Ajustes → Opciones de desarrollador → Estado de Mi Unlock**
Muestra la cuenta regresiva. Cuando diga *"ya puedes desbloquear"*, pasa a la Fase 1.

### ⚠️ NO hagas esto durante la espera (reinicia el contador a 0):
- ❌ Factory reset / borrar datos
- ❌ Cerrar sesión de la cuenta Mi o cambiar de cuenta
- ❌ Desactivar Opciones de desarrollador o el toggle de OEM unlock
- ✅ Puedes usar el teléfono normal; mantenlo con internet de vez en cuando.

---

## FASE 1 — Desbloquear el bootloader (cuando el contador llegue a 0)

```bash
# 💻 1. Instalar la herramienta (una vez)
pip install miunlock        # o: pipx install miunlock

# 📱 2. Apagar el teléfono y entrar a FASTBOOT:
#       mantener  Volumen ABAJO + Power  hasta ver el conejo/FASTBOOT
#       conectar por USB

# 💻 3. Confirmar que la laptop ve el teléfono
fastboot devices            # debe listar un número de serie

# 💻 4. Correr el desbloqueo (login con tu cuenta Mi)
miunlock
```

- Si dice **"espera N horas"** → aún no toca, repetir más tarde.
- Si dice **"desbloqueando / success"** → ✅ bootloader desbloqueado.

> ⚠️ El desbloqueo **borra todos los datos del teléfono** (es normal). Haz copia
> de lo que quieras conservar ANTES.

### Verificar que quedó desbloqueado
```bash
# 💻 (teléfono en fastboot)
fastboot getvar unlocked    # debe responder: unlocked: yes
```

---

## FASE 2 — Recompilar imágenes con el modem habilitado

Esto ya incorpora el patch del modem SDX55 (kernel r1).

```bash
# 💻 Regenerar checksums (deberían decir OK)
pmbootstrap checksum linux-postmarketos-qcom-sm8250-lmi
pmbootstrap checksum device-xiaomi-lmi

# 💻 Recompilar el kernel con el patch del modem
pmbootstrap build linux-postmarketos-qcom-sm8250-lmi

# 💻 Construir la imagen del sistema (contraseña dummy para el usuario)
pmbootstrap install --password 147147

# 💻 Exportar los .img a /tmp/postmarketOS-export/
pmbootstrap export
```

---

## FASE 3 — Flashear postmarketOS

```bash
# 📱 Teléfono en FASTBOOT (Vol- + Power), conectado por USB
# 💻 Confirmar conexión
fastboot devices

# 💻 Flashear (desde el directorio de export)
cd /tmp/postmarketOS-export
fastboot flash boot   boot.img
fastboot flash system xiaomi-lmi.img

# 💻 Reiniciar al sistema
fastboot reboot
```

> Si `fastboot flash system` falla por tamaño/partición (UFS + super),
> avisar — puede requerir `fastboot flash super` o mapear particiones dinámicas.
> El deviceinfo ya declara `deviceinfo_super_partitions`, así que debería ir directo.

El primer arranque tarda varios minutos. La pantalla puede quedar negra un rato
o no encender — **eso NO significa que falló**: verifícalo por SSH (Fase 4).

---

## FASE 4 — Entrar al teléfono por SSH (USB networking)

postmarketOS levanta red por USB aunque la pantalla no funcione.

```bash
# 💻 Con el teléfono ya arrancado y conectado por USB:
ssh user@172.16.42.1          # contraseña: 147147
```

Si no conecta:
```bash
# 💻 Ver si aparece la interfaz de red USB
ip addr | grep -A2 usb        # debería haber una IP en la red 172.16.42.x
```

---

## FASE 5 — Verificar el MODEM (¡la prueba clave!)

Ya **dentro de la sesión SSH** (todo esto corre 📱 en el teléfono):

```bash
# 1. ¿El kernel detectó el modem SDX55 en PCIe? (vendor 17cb, device 0306)
lspci | grep -i 17cb
dmesg | grep -iE "mhi|pci.*17cb|qcom-sdx55|pcie1"

# 2. ¿ModemManager lo reconoce?
sudo mmcli -L                 # lista modems detectados
sudo mmcli -m 0               # detalles del modem 0

# 3. Si aparece: intentar habilitarlo
sudo mmcli -m 0 --enable

# 4. Datos móviles (ajustar TU_APN al de tu operador)
sudo nmcli c add type gsm ifname '*' con-name internet apn TU_APN
sudo nmcli c up internet
```

### Cómo interpretar los resultados
| Resultado | Significado |
|---|---|
| `lspci` muestra `17cb:0306` | ✅ El bus PCIe levantó y el modem está presente |
| `dmesg` muestra `mhi` enganchando | ✅ El driver tomó el modem |
| `mmcli -L` lista un modem | ✅ Userspace lo ve — datos móviles al alcance |
| `lspci` NO muestra nada 17cb | ❌ pcie1 no levantó → revisar regulators en el patch |

**Guarda la salida de estos comandos y compártela** para decidir el siguiente paso
(Fase 2 del modem: datos / voz).

---

## Expectativas honestas del modem
- 📶 **Datos móviles:** muy probable que funcione.
- 📞 **Llamadas / SMS:** experimental (requieren VoLTE) — no garantizado aunque el modem se detecte.
- 🔓 Algunos operadores requieren [FCC unlock](https://modemmanager.org/docs/modemmanager/fcc-unlock/).

---

## Recuperación rápida (si algo sale mal)
- El teléfono **no arranca / pantalla negra y sin SSH:** vuelve a fastboot
  (Vol- + Power) — el bootloader desbloqueado siempre permite re-flashear.
- **Volver a Android:** flashear de nuevo la ROM stock MIUI por fastboot
  (descargar el fastboot ROM de lmi y usar su script `flash_all`).
- El bootloader desbloqueado **no se bloquea solo**; puedes reintentar cuantas veces quieras.

---

## Estado actual del proyecto (al 6 jun 2026)
- ✅ Software compilado, modem habilitado en devicetree (kernel r1)
- ✅ Todo respaldado en GitHub: `macosmojave2-alt/postmarket-xiaomi-lmi`
- ⏳ Bloqueado por: espera de desbloqueo de Xiaomi (~360h)
- ▶️ Siguiente acción real: cuando el contador llegue a 0 → Fase 1
