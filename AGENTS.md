# AGENTS.md

Guide (for agents or people) to the automation script
[`scripts/dipc-dynu.py`](scripts/dipc-dynu.py).

## What it solves

In the ZTE F8748 web panel, when you configure the `dipc` DDNS provider you can
edit **username, password and domain name**, but the **"Provider URL" field is
LOCKED** (read-only). And that field is exactly the one you need to change in order
to point `dipc` at **Dynu's GnuDIP** server.

That value lives in the router's internal database (`DDNSService.Server` of the
`dipc` row) and can only be changed from the device **console**.

👉 The script does **only** that console step: it **opens** the factory SSH, changes
the `dipc` provider URL and **closes** SSH again. It does **not** touch Dynu's
username/password/host — you set those later in the web panel.

> Full flow: `run the script` (changes the locked URL) → `go to the web`
> (DDNS → `dipc` → Dynu username + password + host + WAN interface → Apply).

## What it is based on

On the **[DIGI-F8748](https://github.com/686f6c61/DIGI-F8748)** tool by 686f6c61,
which is what **arms/disarms** the router's factory diagnostic SSH. The script
invokes it (`arm` / `disarm`) and, with SSH open, performs the change via `sendcmd`.

## Requirements

- Python 3 with `paramiko`:  `pip install paramiko`
- The DIGI-F8748 tool downloaded (path to `digi-f8748.py`, `.ps1` or `start.sh`).
- The router's **web credentials**, which the tool uses to arm SSH (these are
  **not** the Dynu ones). The **normal web user** is enough (`user`, default
  `user`/`user`); `admin` works too.
- The router's **MAC** (from the label), format `AA-BB-CC-DD-EE-FF`.
- Be connected directly to the router's network (no repeaters/mesh in between; the
  boot-time MAC check compares your real MAC).

## Usage

### All in one (open → change → close) — the usual
```bash
python scripts/dipc-dynu.py aplicar \
    --digi-tool /path/to/digi-f8748.py \
    --router-mac AA-BB-CC-DD-EE-FF \
    --web-user user --web-pass 'YOUR_WEB_PASS'
```
When it finishes, the `dipc` provider already points at Dynu. **Only the web is
left.**

### Open only (arms SSH and prints the temporary user/pass)
```bash
python scripts/dipc-dynu.py abrir \
    --digi-tool /path/to/digi-f8748.py \
    --router-mac AA-BB-CC-DD-EE-FF \
    --web-user user --web-pass 'YOUR_WEB_PASS'
```

### Close only (disarm)
```bash
python scripts/dipc-dynu.py cerrar \
    --digi-tool /path/to/digi-f8748.py \
    --router-mac AA-BB-CC-DD-EE-FF
```

> Note: the subcommands are `aplicar` (apply), `abrir` (open) and `cerrar` (close).

## Useful options

| Option | Purpose | Default |
|---|---|---|
| `--host` | Router IP | `192.168.1.1` |
| `--gnudip-url` | Target GnuDIP URL (only in `aplicar`) | Dynu's URL |
| `--fila` | Row of `dipc` in the `DDNSService` table | `3` |

## How "open" and "close" work (and how to adapt it)

- **Open** = `digi-f8748 arm --host <ip> --router-mac <mac> -keep -y --web-user <u> --web-pass <p>`.
  The script **parses** the `factory SSH armado - user: X pass: Y` line from the
  output and uses those temporary `X`/`Y` for the SSH (paramiko) to the router.
- **Close** = `digi-f8748 disarm --host <ip> --router-mac <mac> -y`.
  The factory SSH is **temporary** and also **auto-disarms** after a while; even so,
  the `aplicar` mode always disarms at the end (even if something fails).
- The factory SSH is **unstable** (drops often): `ejecutar_en_router()` **retries**
  the connection several times.

### Adapting it
- **Another GnuDIP service** (not Dynu): pass `--gnudip-url http://your-server/.../gdipupdt.cgi`.
- **`dipc` is not on row 3** in your firmware: `--fila N` (check with
  `sendcmd 1 DB p DDNSService`).
- **Embedding it in another script/agent**: reuse the module's `abrir_ssh()`,
  `cerrar_ssh()` and `cambiar_server_dipc()` functions.

## Security

- The script does **not** handle Dynu credentials (those go in the web).
- The router **web credentials** are only used to arm SSH; pass them as arguments
  and **do not publish them**.
- Use it only on **your own router** (or with the owner's permission).
