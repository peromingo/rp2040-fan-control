from pathlib import Path
import tempfile,subprocess,os,shutil,json,sys
work=Path(sys.argv[1]).resolve();shim=work/'test-shim';shim.mkdir(exist_ok=True)
tmpdir=str(Path(tempfile.gettempdir()).resolve())
for name,body in {'sudo':'exit 0','visudo':'exit 0','sync':'exit 0','pgrep':'[ "${SIM_ACTIVE:-0}" = 1 ] && exit 0\nexit 1','logger':'exit 0'}.items():
 p=shim/name;p.write_text('#!/bin/sh\n'+body+'\n');p.chmod(0o755)
# Linux-style CLI adapters are needed only when exercising the Linux installer on macOS.
if sys.platform == 'darwin':
 for name,body in {'base64':'#!/bin/sh\n[ "$1" = -d ] && shift\nexec /usr/bin/base64 -D -i "$1"\n','timeout':'#!/bin/sh\nshift\nexec "$@"\n'}.items():
  f=shim/name;f.write_text(body);f.chmod(0o755)
env=dict(os.environ,PATH=str(shim)+':'+os.environ['PATH'],TMPDIR=tmpdir)

def run(block,root,ok=True,extra=None):
 e=dict(env,RP2040_PLG_TEST_ROOT=str(root));e.update(extra or {})
 r=subprocess.run(['bash',str(work/f'candidate-block{block}.sh')],env=e,text=True,capture_output=True)
 if (r.returncode==0)!=ok: raise AssertionError(r.stdout[-1000:]+r.stderr[-1500:])
 return r

def setup(root):
 (root/'etc/sudoers.d').mkdir(parents=True)
 (root/'usr/local/sbin').mkdir(parents=True)
 (root/'etc/sudoers').write_text('#includedir /etc/sudoers.d\n')
 base=root/'boot/config/plugins/rp2040-fan-control';base.mkdir(parents=True)
 (base/'config.json').write_text('{"test":"preserve"}')
 return base
for existed in [False,True]:
 with tempfile.TemporaryDirectory(prefix='rpboot-',dir=tmpdir) as td:
  root=Path(td);base=setup(root);hook=root/'usr/local/emhttp/plugins/rp2040-fan-control/event/startup/rp2040-autostart'
  if existed:hook.parent.mkdir(parents=True);hook.write_text('old-event\n');hook.chmod(0o755)
  run(0,root)
  assert hook.is_file() and os.access(hook,os.X_OK)
  assert not (base/'ENABLE').exists()
  (base/'ENABLE').touch()
  run(0,root,ok=False) # refuses enabled live-runtime update
  shutil.rmtree(root/'usr/local');(root/'usr/local/sbin').mkdir(parents=True);shutil.rmtree(root/'etc/sudoers.d');(root/'etc/sudoers.d').mkdir()
  run(0,root) # simulate rebuilding RAM paths after reboot
  assert (base/'ENABLE').exists() and hook.is_file()
  assert not (root/'var/run/rp2040-fan-control').exists() # install doesn't launch daemon
  # Test event in an isolated root with a wrapper that records invocation.
  wrapper=root/'usr/local/sbin/rp2040-fan-control';wrapper.write_text('#!/bin/sh\nprintf "%s\\n" "$1" >> "'+str(root/'calls')+'"\n');wrapper.chmod(0o755)
  hs=hook.read_text().replace('BASE=/boot/config/plugins/rp2040-fan-control','BASE='+str(base)).replace('WRAPPER=/usr/local/sbin/rp2040-fan-control','WRAPPER='+str(wrapper))
  ht=root/'hook-test.sh';ht.write_text(hs)
  subprocess.run(['sh',str(ht)],env=env,check=True)
  assert (root/'calls').read_text()=='start\n'
  (base/'ENABLE').unlink();subprocess.run(['sh',str(ht)],env=env,check=True);assert (root/'calls').read_text()=='start\n'
  (base/'ENABLE').touch();pending=base/'backup/test/recovery-pending';pending.parent.mkdir();pending.touch();subprocess.run(['sh',str(ht)],env=env,check=True);assert (root/'calls').read_text()=='start\n';pending.unlink()
  run(1,root)
  assert not (base/'ENABLE').exists() and (base/'config.json').read_text()=='{"test":"preserve"}'
  if existed: assert hook.read_text()=='old-event\n'
  else: assert not hook.exists()
  assert not list((base/'backup').rglob('recovery-pending'))
  print('PASS: install, enabled-update refusal, RAM bootstrap, startup ENABLE/recovery guards, uninstall', 'EXISTING hook' if existed else 'NEW hook')
with tempfile.TemporaryDirectory(prefix='rpboot-',dir=tmpdir) as td:
 root=Path(td);base=setup(root);(base/'ENABLE').touch();run(0,root,ok=False,extra={'SIM_ACTIVE':'1'});assert not (root/'usr/local/sbin/rp2040-fan-control').exists()
 print('PASS: untracked active daemon blocks installation')
