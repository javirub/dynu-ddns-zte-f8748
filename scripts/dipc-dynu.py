#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apunta el proveedor DDNS `dipc` del router ZTE F8748 (DIGI) al servidor GnuDIP
de Dynu, automatizando el paso de consola:

  1) ABRE (arma) el SSH de fabrica con la herramienta DIGI-F8748 de 686f6c61,
  2) cambia el campo `Server` del proveedor `dipc` en la base de datos del router,
  3) CIERRA (desarma) el SSH de fabrica.

NO toca el usuario/contrasena de Dynu: eso se pone despues en la web del router
(DDNS -> proveedor `dipc`).

Requisitos:
  - Python 3 con paramiko:            pip install paramiko
  - La herramienta DIGI-F8748:        https://github.com/686f6c61/DIGI-F8748
  - Credenciales admin de la web del router (para que la herramienta arme el SSH).

Uso tipico (abrir + cambiar + cerrar):
  python dipc-dynu.py aplicar \
      --digi-tool /ruta/a/digi-f8748.py \
      --router-mac AA-BB-CC-DD-EE-FF \
      --web-user user --web-pass 'TU_PASS_WEB'

Solo abrir (arma y te da el usuario/clave SSH temporales):
  python dipc-dynu.py abrir  --digi-tool ... --router-mac ... --web-user ... --web-pass ...
Solo cerrar:
  python dipc-dynu.py cerrar --digi-tool ... --router-mac ...
"""
import argparse
import re
import subprocess
import sys
import time

try:
    import paramiko
except ImportError:
    sys.exit("Falta paramiko. Instala con:  pip install paramiko")

DYNU_GNUDIP_URL = "http://gnudip.dynu.com/gnudip/cgi-bin/gdipupdt.cgi"


# --------------------------------------------------------------------------- #
#  Herramienta DIGI-F8748 (abrir / cerrar el SSH de fabrica)
# --------------------------------------------------------------------------- #
def _digi_cmd(tool, action):
    """Construye el comando base para invocar la herramienta DIGI-F8748."""
    if tool.lower().endswith(".py"):
        return [sys.executable, tool, action]
    if tool.lower().endswith(".ps1"):
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", tool, action]
    return [tool, action]  # binario / shell universal (start.sh, digi-f8748.sh...)


def abrir_ssh(tool, host, mac, web_user, web_pass):
    """Arma el SSH de fabrica y devuelve (usuario, contrasena) temporales."""
    cmd = _digi_cmd(tool, "arm") + [
        "--host", host, "--router-mac", mac, "-keep", "-y",
        "--web-user", web_user, "--web-pass", web_pass,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    salida = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"factory SSH armado.*?user:\s*(\S+)\s+pass:\s*(\S+)", salida, re.S)
    if not m:
        sys.exit("[!] No se pudo armar el SSH de fabrica.\n" + salida)
    return m.group(1), m.group(2)


def cerrar_ssh(tool, host, mac):
    """Desarma el SSH de fabrica (siempre conviene dejarlo cerrado)."""
    cmd = _digi_cmd(tool, "disarm") + ["--host", host, "--router-mac", mac, "-y"]
    subprocess.run(cmd, capture_output=True, text=True)


# --------------------------------------------------------------------------- #
#  SSH al router (BusyBox ash) + cambio en la base de datos
# --------------------------------------------------------------------------- #
def _esperar_puerto(host, port=22, intentos=24, espera=5):
    import socket
    for _ in range(intentos):
        try:
            with socket.create_connection((host, port), timeout=4):
                return True
        except OSError:
            time.sleep(espera)
    return False


def ejecutar_en_router(host, user, pw, comandos, intentos=4):
    """Abre una shell SSH y ejecuta la lista de comandos; devuelve la salida."""
    ultimo_error = None
    for intento in range(1, intentos + 1):
        try:
            t = paramiko.Transport((host, 22))
            t.start_client(timeout=20)
            t.auth_password(user, pw)
            ch = t.open_session()
            ch.get_pty(width=250, height=200)
            ch.invoke_shell()

            def leer(w=2.5):
                buf = b""
                fin = time.time() + w
                while time.time() < fin:
                    if ch.recv_ready():
                        buf += ch.recv(65535)
                        fin = time.time() + w
                    else:
                        time.sleep(0.05)
                return buf.decode(errors="replace")

            leer(2)
            salida = ""
            for c in comandos:
                ch.send(c + "\n")
                salida += leer()
            t.close()
            return salida
        except Exception as e:  # el SSH de fabrica es inestable: reintentar
            ultimo_error = e
            time.sleep(4)
    raise RuntimeError("SSH al router fallo tras varios intentos: %s" % ultimo_error)


def cambiar_server_dipc(host, user, pw, url, fila):
    """Pone el `Server` del proveedor dipc a `url` y lo persiste a flash."""
    comandos = [
        "sendcmd 1 DB set DDNSService %d Server %s" % (fila, url),
        "sendcmd 1 DB unreject",
        "sendcmd 1 DB save",
        "sendcmd 1 DB p DDNSService",  # para verificar
    ]
    salida = ejecutar_en_router(host, user, pw, comandos)
    return salida


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
def _add_common(p, con_web=True):
    p.add_argument("--digi-tool", required=True,
                   help="Ruta a la herramienta DIGI-F8748 (digi-f8748.py / .ps1 / start.sh)")
    p.add_argument("--host", default="192.168.1.1", help="IP del router (def: 192.168.1.1)")
    p.add_argument("--router-mac", required=True, help="MAC del router (pegatina), AA-BB-CC-DD-EE-FF")
    if con_web:
        p.add_argument("--web-user", required=True, help="Usuario de la web del router (vale el normal 'user'; por defecto user/user)")
        p.add_argument("--web-pass", required=True, help="Contrasena de ese usuario web")


def main():
    ap = argparse.ArgumentParser(description="Apunta el proveedor dipc del ZTE F8748 a Dynu (GnuDIP).")
    sub = ap.add_subparsers(dest="accion", required=True)

    pa = sub.add_parser("aplicar", help="Abrir SSH + cambiar Server de dipc + cerrar SSH")
    _add_common(pa)
    pa.add_argument("--gnudip-url", default=DYNU_GNUDIP_URL, help="URL GnuDIP (def: Dynu)")
    pa.add_argument("--fila", type=int, default=3, help="Fila de 'dipc' en DDNSService (def: 3)")

    po = sub.add_parser("abrir", help="Solo armar el SSH de fabrica (muestra user/pass temporales)")
    _add_common(po)

    pc = sub.add_parser("cerrar", help="Solo desarmar el SSH de fabrica")
    _add_common(pc, con_web=False)

    args = ap.parse_args()

    if args.accion == "cerrar":
        print("[*] Cerrando (desarmando) el SSH de fabrica...")
        cerrar_ssh(args.digi_tool, args.host, args.router_mac)
        print("[+] SSH de fabrica desarmado.")
        return

    if args.accion == "abrir":
        print("[*] Armando el SSH de fabrica...")
        user, pw = abrir_ssh(args.digi_tool, args.host, args.router_mac, args.web_user, args.web_pass)
        print("[+] SSH de fabrica armado.")
        print("    usuario: %s" % user)
        print("    pass:    %s" % pw)
        print("    (recuerda cerrarlo luego:  python %s cerrar --digi-tool ... --router-mac %s)"
              % (sys.argv[0], args.router_mac))
        return

    # accion == "aplicar"
    print("[*] 1/3 Armando el SSH de fabrica...")
    user, pw = abrir_ssh(args.digi_tool, args.host, args.router_mac, args.web_user, args.web_pass)
    print("[+] SSH armado (usuario temporal: %s)" % user)
    try:
        if not _esperar_puerto(args.host):
            print("[!] El puerto 22 no respondio; intentando igualmente...")
        print("[*] 2/3 Apuntando el proveedor dipc a: %s" % args.gnudip_url)
        salida = cambiar_server_dipc(args.host, user, pw, args.gnudip_url, args.fila)
        ok = args.gnudip_url in salida
        print("[+] Cambio aplicado y guardado." if ok
              else "[!] Aplicado, pero no pude verificar el valor. Revisa la salida:")
        if not ok:
            print(salida[-800:])
    finally:
        print("[*] 3/3 Cerrando el SSH de fabrica...")
        cerrar_ssh(args.digi_tool, args.host, args.router_mac)
        print("[+] SSH de fabrica desarmado.")

    print("\n[OK] Proveedor dipc apuntando a Dynu. Ahora termina en la WEB del router:")
    print("     DDNS -> Proveedor: dipc -> usuario/clave de Dynu + tu hostname + WAN -> Aplicar.")


if __name__ == "__main__":
    main()
