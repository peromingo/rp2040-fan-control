from pathlib import Path
import re,tarfile,io,base64,gzip,hashlib,argparse
parser=argparse.ArgumentParser(description="Build the boot-support review candidate from auditfix22.")
parser.add_argument("input",type=Path)
parser.add_argument("output",type=Path)
args=parser.parse_args()
root=args.output.resolve()
if root.exists() and any(root.iterdir()):
 raise SystemExit("Output directory must be empty")
root.mkdir(parents=True,exist_ok=True)
s=args.input.read_text()
blocks=re.findall(r'<FILE Run="/bin/bash"(?: Method="remove")?><INLINE><!\[CDATA\[(.*?)\]\]></INLINE></FILE>',s,re.S)
icon='usr/local/emhttp/plugins/rp2040-fan-control/images/fan.png'
event='usr/local/emhttp/plugins/rp2040-fan-control/event/startup/rp2040-autostart'
payload=root/'payload'
m=re.search(r"cat > \"\$TMP/payload.b64\" <<'__PAYLOAD_EOF__'\n(.*?)__PAYLOAD_EOF__",s,re.S)
if not m: raise SystemExit("Payload not found")
with tarfile.open(fileobj=io.BytesIO(base64.b64decode(m.group(1))),mode='r:gz') as archive:
 for item in archive.getmembers():
  if item.name.startswith('/') or '..' in Path(item.name).parts or not (item.isfile() or item.isdir()):
   raise SystemExit("Unsafe payload member")
 archive.extractall(payload)
hook='''#!/bin/sh
# Unraid startup runs after plugin installation, before array status is valid.
# Start fan control independently of whether the array is started.
set -eu
BASE=/boot/config/plugins/rp2040-fan-control
WRAPPER=/usr/local/sbin/rp2040-fan-control
[ -f "$BASE/ENABLE" ] && [ ! -L "$BASE/ENABLE" ] || exit 0
[ -x "$WRAPPER" ] || { logger -t rp2040-fan-control "Autostart: falta el wrapper"; exit 0; }
if ! pending=$(find "$BASE/backup" -name recovery-pending -print -quit); then
    logger -t rp2040-fan-control "Autostart: no se pudo comprobar la recuperación"
    exit 0
fi
if [ -n "$pending" ]; then
    logger -t rp2040-fan-control "Autostart: recuperación pendiente; daemon no iniciado"
    exit 0
fi
mkdir -p "$BASE/logs"
# Bound the hook so a startup error cannot hold emhttp indefinitely.
if ! timeout 30 "$WRAPPER" start >> "$BASE/logs/boot.log" 2>&1; then
    logger -t rp2040-fan-control "Autostart fallido; revise logs/boot.log"
fi
exit 0
'''
hp=payload/event;hp.parent.mkdir(parents=True,exist_ok=True);hp.write_text(hook);hp.chmod(0o755)
# Reproducible archive including permissions needed by the installer.
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w',format=tarfile.GNU_FORMAT) as t:
 for p in sorted(payload.rglob('*')):
  if not p.is_file(): continue
  info=t.gettarinfo(str(p),arcname=p.relative_to(payload).as_posix());info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
  info.mode=0o755 if info.name in ('usr/local/sbin/rp2040-fan-control','usr/local/sbin/rp2040-fan-control-webui',event) else 0o644
  with p.open('rb') as f:t.addfile(info,f)
packed=gzip.compress(buf.getvalue(),mtime=0)
newhash=hashlib.sha256(packed).hexdigest()
for i,original in enumerate(blocks):
 b=original
 # Add the startup hook everywhere icon destinations are guarded, backed up or restored.
 out=[]
 for line in b.splitlines(keepends=True):
  if icon in line and ('EXISTING:' in line and '|EXISTING:' in line or 'NEW:' in line and '|NEW:' in line):
   kind='EXISTING' if 'EXISTING:' in line else 'NEW'
   line=line.replace(kind+':'+icon+'|',kind+':'+icon+'|'+kind+':'+event+'|')
   out.append(line)
  elif icon in line:
   out.append(line)
   clone=line.replace(icon,event).replace('PAGE_ICON','STARTUP_EVENT')
   if line.lstrip().startswith('install -m 0644'): clone=clone.replace('-m 0644','-m 0755')
   out.append(clone)
  elif line.strip() == 'install -m 0644 "$SRC_PAGE_ICON" "$PAGE_ICON"':
   out.append(line)
   out.append('mkdir -p "$(dirname "$STARTUP_EVENT")"\ninstall -m 0755 "$SRC_STARTUP_EVENT" "$STARTUP_EVENT"\n')
  else:
   line=line.replace('"$PAGE_ICON" "$SUDOERS"','"$PAGE_ICON" "$STARTUP_EVENT" "$SUDOERS"')
   line=line.replace('[ -f "$SRC_PAGE_ICON" ] ||','[ -f "$SRC_PAGE_ICON" ] && [ -f "$SRC_STARTUP_EVENT" ] ||')
   out.append(line)
 b=''.join(out).replace('webui-integration-serial-port-conf-auditfix21','webui-integration-serial-port-conf-auditfix23')
 if i==0:
  old='# Refuse to change a running or explicitly enabled service.\n[ ! -e "$P/ENABLE" ] || { echo "ERROR: existe ENABLE; no se actualiza mientras el servicio está habilitado" >&2; exit 1; }'
  new='''# A missing RAM wrapper and IPC directory permit bootstrap after reboot.
# Enabled manual upgrades on an already installed runtime remain prohibited.
assert_no_symlink_path "$P/ENABLE"
assert_no_symlink_path "$ROOT_PREFIX/var/run/rp2040-fan-control"
if pgrep -f -- "$APP/rp2040_fan_control_webui_dev.py" >/dev/null 2>&1; then
  echo "ERROR: hay un daemon activo; deténgalo antes de instalar" >&2
  exit 1
fi
if [ -e "$P/ENABLE" ]; then
  [ -f "$P/ENABLE" ] || { echo "ERROR: ENABLE no es un archivo regular" >&2; exit 1; }
  if [ -e "$WRAPPER" ] || [ -e "$ROOT_PREFIX/var/run/rp2040-fan-control" ]; then
    echo "ERROR: existe ENABLE y hay runtime instalado; detenga el servicio antes de actualizar" >&2
    exit 1
  fi
  echo "Restauración de runtime con ENABLE conservado; el evento startup iniciará el daemon."
fi'''
  assert old in b;b=b.replace(old,new)
  # Add directory creation for the new hook before installing its source.
  b=b.replace('install -m 0755 "$SRC_STARTUP_EVENT" "$STARTUP_EVENT"','mkdir -p "$(dirname "$STARTUP_EVENT")"\ninstall -m 0755 "$SRC_STARTUP_EVENT" "$STARTUP_EVENT"')
  b=re.sub(r"(<<'__PAYLOAD_EOF__'\n).*?(\n__PAYLOAD_EOF__)",lambda m:m[1]+base64.b64encode(packed).decode()+m[2],b,flags=re.S)
  b=b.replace('f38ee479b2f19594f6abb25e80ba98e945d074b0e30a3af75f70e061f10a5be1',newhash)
  b=b.replace('Daemon NO iniciado; ENABLE NO creado; firmware NO modificado; config.json y logs locales conservados.','Daemon NO iniciado por instalación; ENABLE conservado si existe; inicio automático mediante startup. Firmware, config.json y logs locales conservados.')
 Path(root/f'candidate-block{i}.sh').write_text(b)
 s=s.replace(original,b)
s=s.replace('0.7.14-final-ui-auditfix22-uninstall-verify','0.7.15-boot-auditfix23')
s=s.replace('### Auditfix22:', '### Auditfix23: restauración de runtime y arranque automático\n    - Restaura archivos RAM durante el arranque conservando ENABLE.\n    - Inicia el daemon en startup solo si ENABLE existe y no hay recuperación pendiente.\n    - Incluye el gancho startup en la copia de reversión.\n    ### Auditfix22:',1)
p=root/'rp2040-fan-control-webui-integration-serial-v2-auditfix19.plg';p.write_text(s)
(p.with_suffix('.plg.sha256')).write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n')
print(p)
print(newhash)
