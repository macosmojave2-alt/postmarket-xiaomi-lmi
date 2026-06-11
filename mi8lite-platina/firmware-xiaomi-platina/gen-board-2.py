#!/usr/bin/env python3
"""
Genera el JSON de entrada para ath10k-bdencoder a partir de los board files
bdwlan.* extraídos de la partición modem del Xiaomi Mi 8 Lite (platina).

Cada bdwlan.bXX codifica un qmi-board-id en su extensión hexadecimal:
  bdwlan.b33  -> qmi-board-id=51  (0x33)
  bdwlan.bin  -> board file por defecto (fallback, "bus=snoc")

El WCN3990 del SDM660 usa el bus 'snoc'. ath10k busca la imagen por el
qmi-board-id reportado por el firmware; el fallback genérico cubre el resto.

Uso:
    python3 gen-board-2.py <dir_con_bdwlan> <salida.json>
"""
import json
import os
import sys


def main():
    if len(sys.argv) != 3:
        print(f"uso: {sys.argv[0]} <dir_bdwlan> <salida.json>", file=sys.stderr)
        sys.exit(1)

    src_dir, out_json = sys.argv[1], sys.argv[2]
    entries = []

    for fname in sorted(os.listdir(src_dir)):
        if not fname.startswith("bdwlan."):
            continue
        ext = fname.split(".", 1)[1]  # p.ej. "b33", "109", "bin"

        # ath10k construye el nombre del board file con el qmi-board-id en
        # HEXADECIMAL sin prefijo (kernel: "bus=%s,qmi-board-id=%x").
        # En las extensiones tipo "bXX" la "b" inicial es un prefijo de tipo,
        # NO parte del board-id: bdwlan.b33 -> qmi-board-id=33 (verificado
        # contra el board-2.bin de lavender, mismo WCN3990+SDM660, que usa
        # 33/34/.../102/ff). Las extensiones tipo "1XX" se usan tal cual.
        if ext == "bin":
            # Board file por defecto. El WCN3990 del platina reporta
            # qmi-board-id=ff cuando su OTP no tiene board-id programado,
            # o qmi-board-id=0 cuando el EFS/calibración no está disponible
            # (modem estable pero sin board-id provisto). El default cubre
            # ambos valores además del genérico.
            names = ["bus=snoc", "bus=snoc,qmi-board-id=ff",
                     "bus=snoc,qmi-board-id=0"]
        else:
            # "bXX" -> board-id "XX"; otras (102, ...) -> tal cual.
            if ext.startswith("b") and len(ext) == 3:
                board_id = ext[1:]
            else:
                board_id = ext
            try:
                int(board_id, 16)
            except ValueError:
                print(f"  ⚠️  ignorado (extensión desconocida): {fname}", file=sys.stderr)
                continue
            names = [f"bus=snoc,qmi-board-id={board_id}"]

        entries.append({"names": names, "data": fname})

    if not entries:
        print("❌ no se encontró ningún bdwlan.* en", src_dir, file=sys.stderr)
        sys.exit(1)

    with open(out_json, "w") as f:
        json.dump(entries, f, indent=2)

    print(f"✅ {len(entries)} board files indexados en {out_json}")
    for e in entries:
        print(f"   {e['data']:14s} -> {e['names'][0]}")


if __name__ == "__main__":
    main()
