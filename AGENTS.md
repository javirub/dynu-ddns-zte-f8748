# AGENTS.md

Guía para (agentes o personas) sobre el script de automatización
[`scripts/dipc-dynu.py`](scripts/dipc-dynu.py).

## Qué resuelve

En el panel web del ZTE F8748, al configurar el proveedor DDNS `dipc` puedes
editar **usuario, contraseña y nombre de dominio**, pero el campo
**"URL del proveedor" está BLOQUEADO** (solo lectura). Y justo ese campo es el que
hay que cambiar para apuntar `dipc` al servidor **GnuDIP de Dynu**.

Ese valor vive en la base de datos interna del router (`DDNSService.Server` de la
fila `dipc`) y solo se puede cambiar desde la **consola** del equipo.

👉 El script hace **solo** ese paso de consola: **abre** el SSH de fábrica, cambia
la URL del proveedor `dipc` y **cierra** el SSH. **No toca usuario/contraseña/host
de Dynu** — eso lo pones tú luego en la web.

> Flujo completo: `ejecutar el script` (cambia la URL bloqueada) → `ir a la web`
> (DDNS → `dipc` → usuario + contraseña + host de Dynu + interfaz WAN → Aplicar).

## En qué se basa

En la herramienta **[DIGI-F8748](https://github.com/686f6c61/DIGI-F8748)** de
686f6c61, que es la que **arma/desarma** el SSH de diagnóstico de fábrica del
router. El script la invoca (`arm` / `disarm`) y, con el SSH abierto, ejecuta el
cambio por `sendcmd`.

## Requisitos

- Python 3 con `paramiko`:  `pip install paramiko`
- La herramienta DIGI-F8748 descargada (ruta a `digi-f8748.py`, `.ps1` o `start.sh`).
- Credenciales **admin de la web** del router (las necesita la herramienta para
  armar el SSH; **no** son las de Dynu).
- La **MAC del router** (pegatina), formato `AA-BB-CC-DD-EE-FF`.
- Estar conectado a la red del router directamente (sin repetidores/mesh por medio;
  la comprobación de MAC del arranque compara tu MAC real).

## Uso

### Todo de una (abrir → cambiar → cerrar) — lo normal
```bash
python scripts/dipc-dynu.py aplicar \
    --digi-tool /ruta/a/digi-f8748.py \
    --router-mac AA-BB-CC-DD-EE-FF \
    --web-user admin --web-pass 'TU_PASS_ADMIN'
```
Al terminar, el proveedor `dipc` ya apunta a Dynu. **Falta solo la web.**

### Solo abrir (arma y te da el usuario/clave SSH temporales)
```bash
python scripts/dipc-dynu.py abrir \
    --digi-tool /ruta/a/digi-f8748.py \
    --router-mac AA-BB-CC-DD-EE-FF \
    --web-user admin --web-pass 'TU_PASS_ADMIN'
```

### Solo cerrar (desarmar)
```bash
python scripts/dipc-dynu.py cerrar \
    --digi-tool /ruta/a/digi-f8748.py \
    --router-mac AA-BB-CC-DD-EE-FF
```

## Opciones útiles

| Opción | Para qué | Por defecto |
|---|---|---|
| `--host` | IP del router | `192.168.1.1` |
| `--gnudip-url` | URL GnuDIP destino (solo en `aplicar`) | URL de Dynu |
| `--fila` | Fila de `dipc` en la tabla `DDNSService` | `3` |

## Cómo "abrir" y "cerrar" (cómo lo hace y cómo adaptarlo)

- **Abrir** = `digi-f8748 arm --host <ip> --router-mac <mac> -keep -y --web-user <u> --web-pass <p>`.
  El script **parsea** de la salida la línea `factory SSH armado - user: X pass: Y`
  y usa esos `X`/`Y` temporales para el SSH (paramiko) al router.
- **Cerrar** = `digi-f8748 disarm --host <ip> --router-mac <mac> -y`.
  El SSH de fábrica es **temporal** y además se **auto-desarma** solo tras un rato;
  aun así, el modo `aplicar` siempre desarma al final (incluso si algo falla).
- El SSH de fábrica es **inestable** (se corta a menudo): `ejecutar_en_router()`
  **reintenta** la conexión varias veces.

### Adaptarlo
- **Otro servicio GnuDIP** (no Dynu): pasa `--gnudip-url http://tu-servidor/.../gdipupdt.cgi`.
- **La fila de `dipc` no es la 3** en tu firmware: `--fila N` (compruébalo con
  `sendcmd 1 DB p DDNSService`).
- **Integrarlo en otro script/agente**: reutiliza las funciones `abrir_ssh()`,
  `cerrar_ssh()` y `cambiar_server_dipc()` del módulo.

## Seguridad

- El script **no** maneja credenciales de Dynu (van en la web).
- Las credenciales **admin de la web** solo se usan para armar el SSH; pásalas por
  argumento y **no las publiques**.
- Úsalo solo en **tu propio router** (o con permiso del propietario).
