# DDNS gratis (Dynu) en routers ZTE F8748 de DIGI — vía GnuDIP / `dipc`

Guía para configurar **Dynu** (DDNS dinámico **gratis y sin renovaciones**) en el
router **ZTE F8748** de DIGI, de forma **persistente** (se relanza solo en cada
reinicio) y **sin mantenimiento**, reutilizando el proveedor de fábrica `dipc`
(protocolo **GnuDIP**) apuntándolo al servidor GnuDIP de Dynu.

> Probado en un ZTE F8748 de DIGI (firmware `V3.0.10...`, XGS-PON). Debería valer
> para otros modelos ZTE/FiberHome con el mismo panel DDNS y el proveedor `dipc`.

---

## El problema

El F8748 solo trae **5 proveedores DDNS de fábrica**: `DynDNS`, `DtDNS`, `No-IP`,
`dipc` y `easyDNS`.

- Si intentas **añadir otro** (Dynu, FreeDNS, No-IP alternativo…) por la web, al
  pulsar *Aplicar* salta **"La operación actual es inválida"** (error cmapi `-257`).
  El demonio de configuración `cspd` valida el proveedor contra una **lista cerrada
  compilada en el binario**, que vive en un **rootfs de solo lectura** → no se puede
  ampliar ni parcheando el binario.
- De los 5 de fábrica, **el único gratis es No-IP**… que te obliga a **confirmar el
  host cada 30 días** por correo. Un incordio.

## La idea clave

El proveedor de fábrica **`dipc`** usa el protocolo **GnuDIP** (su servidor por
defecto es `ns.eagleeyes.com.cn`, pero el **servidor es configurable**: el router
parsea la URL del campo *Server*).

Y resulta que **Dynu ofrece GnuDIP gratis** (`gnudip.dynu.com`).

👉 **Reutilizamos `dipc` apuntándolo al servidor GnuDIP de Dynu.** Como `dipc` SÍ
está en la lista aceptada por `cspd`, el router **lo acepta** por la web (sin el
`-257`), lo **lanza al arrancar** y lo **mantiene** en cada cambio de IP.

Resultado: **Dynu gratis, sin nag, persistente y cero mantenimiento.**

---

## Requisitos

- Una cuenta **gratuita en [Dynu](https://www.dynu.com/)** con un hostname
  (p. ej. `tucasa.freeddns.org`).
- Acceso **admin** a la web del router.
- Acceso a la **consola del router** (SSH/telnet) **una sola vez**, para cambiar la
  URL del proveedor `dipc` — el campo *URL del proveedor* es de **solo lectura** en
  la web, así que hay que tocarlo en la base de datos interna.
  - En los **F8748 de DIGI** el SSH de fábrica está capado; se "arma" temporalmente
    con una herramienta de recuperación (ver [Créditos](#créditos)).

## Datos GnuDIP de Dynu

| Dato | Valor |
|---|---|
| Servidor | `gnudip.dynu.com` |
| URL (HTTP) | `http://gnudip.dynu.com/gnudip/cgi-bin/gdipupdt.cgi` |
| Puerto HTTP | `80` (también `8245`) |
| Puerto TCP | `3495` |
| Usuario / contraseña | los de tu cuenta Dynu *(recomendado: la "IP Update Password" de Dynu, revocable)* |
| Dominio | tu hostname completo (`tucasa.freeddns.org`) |

---

## Pasos

### 1. Crea el hostname en Dynu
Regístrate en Dynu (gratis) y crea un hostname bajo cualquiera de sus dominios
gratuitos (p. ej. `tucasa.freeddns.org`). En *Preferences → IP Update Password*
puedes fijar una contraseña dedicada para actualizaciones (recomendado).

### 2. Apunta el proveedor `dipc` a Dynu (consola del router)
Entra por SSH a la consola del router (BusyBox `ash`) y cambia el **Server** del
proveedor `dipc` en la base de datos de configuración:

```sh
# Verifica primero en qué fila está "dipc" (en firmware de stock suele ser la 3):
sendcmd 1 DB p DDNSService | grep -n -E 'Row No|Name'

# Apunta el proveedor dipc al servidor GnuDIP de Dynu:
sendcmd 1 DB set DDNSService 3 Server http://gnudip.dynu.com/gnudip/cgi-bin/gdipupdt.cgi

# Persiste a flash:
sendcmd 1 DB unreject
sendcmd 1 DB save
```

> `DDNSService` fila `3` = `dipc`. Si en tu equipo está en otra fila, usa ese índice.

> 💡 **¿Prefieres no hacerlo a mano?** El script [`scripts/dipc-dynu.py`](scripts/dipc-dynu.py)
> automatiza este paso: **abre** el SSH de fábrica, **cambia** la URL del proveedor
> `dipc` y **cierra** el SSH, de una sola ejecución. No toca usuario/clave/host de
> Dynu (eso va en la web). Ver [`AGENTS.md`](AGENTS.md).
> ```bash
> python scripts/dipc-dynu.py aplicar \
>     --digi-tool /ruta/a/digi-f8748.py \
>     --router-mac AA-BB-CC-DD-EE-FF \
>     --web-user admin --web-pass 'TU_PASS_ADMIN'
> ```

*(Opcional, para comprobar el cliente GnuDIP a mano antes de la web):*
```sh
dipc -s gnudip.dynu.com -t HTTP -o 80 -l /gnudip/cgi-bin/gdipupdt.cgi \
     -d tucasa.freeddns.org -u TU_USUARIO_DYNU -p TU_CONTRASEÑA_DYNU -r 1
```

### 3. Configúralo en la web
Panel del router → **DDNS**:

- **Proveedor:** `dipc`
- **URL del proveedor:** debe mostrar `http://gnudip.dynu.com/gnudip/cgi-bin/gdipupdt.cgi`
- **Usuario:** tu usuario de Dynu
- **Contraseña:** tu contraseña (o *IP Update Password*) de Dynu
- **Nombre de dominio:** `tucasa.freeddns.org`
- **Interfaz / Conexión WAN:** tu WAN de internet (la PPPoE)
- **Habilitar:** Sí → **Aplicar**

Debe responder **"Tus datos han sido guardados"** (sin el "operación inválida").

### 4. Verifica
- En la web: **Estado = Connected** y la IP mostrada = tu IP pública.
- Resuelve el hostname desde fuera y comprueba que apunta a tu IP:
  ```sh
  nslookup tucasa.freeddns.org 1.1.1.1
  ```
- **Reinicia el router**: tras arrancar, `cspd` relanza `dipc` solo y actualiza la
  IP. Si cambia de `127.0.0.1` (puesto a mano para probar) a tu IP real → ✅
  **persistencia confirmada**.

---

## Por qué funciona (técnico)

- `cspd` mapea cada proveedor DDNS a un cliente: `inadyn` (DynDNS/No-IP/easyDNS/…),
  `dtdns`, o **`dipc` (GnuDIP)**.
- La lista de proveedores **aceptados** está **compilada** en `cspd`, que está en
  un **rootfs de solo lectura** (no se puede remontar en escritura). Por eso añadir
  un proveedor nuevo falla con **cmapi `-257`** tanto por la web como al arrancar.
- Pero **`dipc` ya está en esa lista** y, al ser **GnuDIP**, su **servidor es
  configurable**: `cspd` parsea la URL del campo *Server* (`ddnsParseDipcUrl`) y
  lanza `dipc` con `-s/-o/-l` hacia ese servidor. Dynu habla **GnuDIP estándar**, así
  que encajan.
- **GnuDIP** (resumen): el cliente pide un *salt* al CGI, calcula
  `md5( md5(password) + "." + salt )` y envía la actualización; el servidor detecta
  la IP por el **origen de la petición** (IPv4). Todo por **HTTP :80** → **sin líos
  de certificado**.

## Notas

- Vale para **cualquier DDNS que ofrezca GnuDIP**, no solo Dynu.
- El paso de consola (cambiar el *Server* de `dipc`) es **imprescindible**: el campo
  *URL del proveedor* es de solo lectura en la web y no se puede editar desde ahí.
- **No publiques credenciales reales** ni tu hostname en sitios públicos.
- Si prefieres no tocar la consola, la alternativa es No-IP por la web (gratis pero
  con confirmación cada 30 días).

## Créditos

- Acceso SSH de fábrica en el F8748 de DIGI: herramienta de recuperación
  **DIGI-F8748** de [686f6c61](https://github.com/686f6c61/DIGI-F8748).
- Protocolo **GnuDIP** de **Dynu**: <https://www.dynu.com/>.

---

> Documentación hecha a partir de ingeniería inversa del propio router (uso en
> equipo propio). Úsala bajo tu responsabilidad.
