<?php
/*
 * RP2040 Fan Control for Unraid — development UI 0.5.0.
 * The page never opens the serial port and never calculates fan curves.
 */

/* Mutating forms must use the Unraid route, where its CSRF gateway runs.
 * The direct PHP endpoint is reserved for read-only live status polling. */
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST'
    && realpath((string)($_SERVER['SCRIPT_FILENAME'] ?? '')) === __FILE__) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    exit('Envía las operaciones mediante la página de Unraid.');
}

$statusFile = '/var/run/rp2040-fan-control/status.json';
$commandFile = '/var/run/rp2040-fan-control/command.json';
$resultFile = '/var/run/rp2040-fan-control/command-result.json';
$varIniFile = '/var/local/emhttp/var.ini';
$allowedModes = ['AUTO', 'SILENT', 'TURBO'];
$error = null;
$notice = null;
$submittedRequestId = '';
$modeReturnUrl = null;

function rp2040_h($value): string {
    return htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
function rp2040_read_json(string $path): ?array {
    if (!is_readable($path)) return null;
    $raw = @file_get_contents($path);
    if ($raw === false || strlen($raw) > 65536) return null;
    $value = json_decode($raw, true);
    return is_array($value) ? $value : null;
}
function rp2040_value($value, string $suffix = ''): string {
    if ($value === null || $value === '' || !is_scalar($value)) return '—';
    return rp2040_h($value) . rp2040_h($suffix);
}
function rp2040_temp($value): string {
    if (!is_numeric($value)) return '—';
    return rp2040_h(number_format((float)$value, 1, ',', '.')) . ' °C';
}
function rp2040_helper_json(string $action): ?array {
    $allowed = ['status', 'inventory', 'get-config', 'serial-config'];
    if (!in_array($action, $allowed, true)) return null;
    $cmd = 'sudo -n /usr/local/sbin/rp2040-fan-control-webui ' . $action . ' 2>/dev/null';
    $raw = @shell_exec($cmd);
    if (!is_string($raw) || $raw === '') return null;
    $value = json_decode($raw, true);
    return is_array($value) ? $value : null;
}
function rp2040_helper_action(string $action, ?array $payload = null): array {
    $allowed = ['start', 'stop', 'restart', 'save-config', 'save-serial-port'];
    if (!in_array($action, $allowed, true)) return [false, 'Acción no permitida.'];
    $descriptors = [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']];
    $proc = @proc_open('sudo -n /usr/local/sbin/rp2040-fan-control-webui ' . $action, $descriptors, $pipes);
    if (!is_resource($proc)) return [false, 'No se pudo ejecutar el servicio auxiliar con permisos controlados.'];
    if ($payload !== null) fwrite($pipes[0], json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR));
    fclose($pipes[0]);
    $stdout = stream_get_contents($pipes[1]); fclose($pipes[1]);
    $stderr = stream_get_contents($pipes[2]); fclose($pipes[2]);
    $code = proc_close($proc);
    if ($code !== 0) return [false, 'La operación falló. Comprueba el registro del plugin.' . ($stderr !== '' ? ' ' . trim($stderr) : '')];
    return [true, trim((string)$stdout) !== '' ? trim((string)$stdout) : 'Operación completada.'];
}

/* Unraid validates csrf_token at the request gateway before loading this page. */
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
    // Avoid the HTMLFormElement.action property collision in Unraid's Dynamix JS.
    $action = (string)($_POST['operation'] ?? 'set_mode');
    if (in_array($action, ['start', 'stop', 'restart'], true)) {
        [$ok, $message] = rp2040_helper_action($action);
        if ($ok) $notice = $message; else { http_response_code(503); $error = $message; }
    } elseif ($action === 'save_serial_port') {
        $port = (string)($_POST['serial_port'] ?? 'auto');
        [$ok, $message] = rp2040_helper_action('save-serial-port', ['port' => $port]);
        if ($ok) $notice = $message; else { http_response_code(400); $error = $message; }
    } elseif ($action === 'save_config') {
        $inventory = rp2040_helper_json('inventory');
        if (!is_array($inventory)) {
            http_response_code(503); $error = 'No se pudo consultar el inventario de discos mediante el auxiliar privilegiado.';
        } else {
            $byKey = [];
            foreach ($inventory as $disk) {
                if (!is_array($disk) || !is_string($disk['model'] ?? null) || !is_string($disk['serial'] ?? null)) continue;
                $key = hash('sha256', $disk['model'] . "\0" . $disk['serial']);
                $byKey[$key] = ['model' => $disk['model'], 'serial' => $disk['serial']];
            }
            $selected1 = is_array($_POST['fan1_disks'] ?? null) ? $_POST['fan1_disks'] : [];
            $selected2 = is_array($_POST['fan2_disks'] ?? null) ? $_POST['fan2_disks'] : [];
            $resolve = static function(array $keys) use ($byKey): array {
                $out = [];
                foreach ($keys as $key) {
                    if (!is_string($key) || !isset($byKey[$key])) throw new RuntimeException('Se ha seleccionado un disco que no pertenece al inventario actual.');
                    $out[] = $byKey[$key];
                }
                return $out;
            };
            try {
                $payload = ['schema_version' => 1, 'fans' => [
                    'fan1' => ['disks' => $resolve($selected1), 'use_cpu' => isset($_POST['use_cpu_fan1']) && $_POST['use_cpu_fan1'] === '1'],
                    'fan2' => ['disks' => $resolve($selected2), 'use_cpu' => isset($_POST['use_cpu_fan2']) && $_POST['use_cpu_fan2'] === '1'],
                ]];
                [$ok, $message] = rp2040_helper_action('save-config', $payload);
                if ($ok) $notice = $message; else { http_response_code(400); $error = $message; }
            } catch (Throwable $e) {
                http_response_code(400); $error = $e->getMessage();
            }
        }
    } else {
        $mode = strtoupper((string)($_POST['mode'] ?? ''));
        if (!in_array($mode, $allowedModes, true)) {
            http_response_code(400); $error = 'Modo solicitado no válido.';
        } elseif (!is_dir(dirname($commandFile)) || !is_writable(dirname($commandFile))) {
            http_response_code(503); $error = 'El canal IPC no está disponible. Comprueba que el daemon está iniciado.';
        } elseif (is_file($commandFile)) {
            http_response_code(409); $error = 'Ya hay una solicitud pendiente. Espera a que el daemon la procese.';
        } else {
            try {
                $requestId = bin2hex(random_bytes(16));
                $request = ['schema_version' => 1, 'request_id' => $requestId, 'created_at' => microtime(true), 'action' => 'set_mode', 'mode' => $mode];
                $encoded = json_encode($request, JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR);
                $tmp = tempnam(dirname($commandFile), '.command-');
                if ($tmp === false) throw new RuntimeException('No se pudo crear el archivo temporal.');
                $written = file_put_contents($tmp, $encoded . "\n", LOCK_EX);
                if ($written === false || $written !== strlen($encoded . "\n")) { @unlink($tmp); throw new RuntimeException('No se pudo escribir la solicitud.'); }
                @chmod($tmp, 0640);
                if (!@link($tmp, $commandFile)) {
                    @unlink($tmp);
                    if (is_file($commandFile)) { http_response_code(409); $error = 'Ya hay una solicitud pendiente. Espera a que el daemon la procese.'; }
                    else throw new RuntimeException('No se pudo publicar la solicitud IPC.');
                } else @unlink($tmp);
                if ($error === null) {
                    $submittedRequestId = $requestId;
                    $pagePath = parse_url((string)($_SERVER['REQUEST_URI'] ?? ''), PHP_URL_PATH);
                    if (!is_string($pagePath) || !preg_match('~^/(?:Settings|Utilities)/RP2040FanControl$~D', $pagePath)) {
                        $pagePath = '/Settings/RP2040FanControl';
                    }
                    $modeReturnUrl = $pagePath . '?request_id=' . rawurlencode($requestId);
                    // Unraid owns the outer response. Always render the included page;
                    // its local GET navigation below completes the form without exiting
                    // midway through the surrounding renderer or relying on HTTP headers.
                    $notice = 'Solicitud enviada. Esperando confirmación del daemon.';
                }
            } catch (Throwable $e) { $error = 'No se pudo enviar la solicitud al daemon.'; error_log('RP2040 Fan Control IPC: ' . $e->getMessage()); }
        }
    }
}

$status = rp2040_read_json($statusFile);
$result = rp2040_read_json($resultFile);
$requestIdFromQuery = $submittedRequestId;
if ($requestIdFromQuery === '' && ($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'GET') {
    $requestIdFromQuery = (string)($_GET['request_id'] ?? '');
}
if (!preg_match('/^[a-f0-9]{32}$/D', $requestIdFromQuery)) $requestIdFromQuery = '';
if ($requestIdFromQuery !== '' && preg_match('/^[a-f0-9]{32}$/', $requestIdFromQuery)) {
    if (is_array($result) && ($result['request_id'] ?? '') === $requestIdFromQuery) {
        $notice = (bool)($result['ok'] ?? false)
            ? 'Modo aceptado por el daemon y transmitido por serie: ' . (string)($result['applied_mode'] ?? '') . '. El firmware actual no devuelve ACK.'
            : 'El daemon rechazó la solicitud: ' . (string)($result['message'] ?? 'sin detalles') . '.';
    } else {
        $notice = 'Solicitud enviada. Esperando confirmación del daemon; el cambio todavía no está confirmado.';
    }
}

$timestamp = is_array($status) && is_numeric($status['timestamp'] ?? null) ? (float)$status['timestamp'] : 0.0;
$rawStatusAge = $timestamp > 0 ? time() - $timestamp : null;
/* Reject implausibly future-dated snapshots instead of treating them as fresh. */
$statusAge = ($rawStatusAge !== null && $rawStatusAge >= -5) ? max(0, $rawStatusAge) : null;
$statusFresh = $statusAge !== null && $statusAge <= 10;
$vars = is_readable($varIniFile) ? @parse_ini_file($varIniFile) : false;
$csrfToken = is_array($vars) ? (string)($vars['csrf_token'] ?? '') : '';
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'GET' && ($_GET['rp2040_live'] ?? '') === '1') {
    $liveService = rp2040_helper_json('status');
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, max-age=0');
    echo json_encode([
        'command_result' => $requestIdFromQuery !== '' && is_array($result) && ($result['request_id'] ?? '') === $requestIdFromQuery ? $result : null,
        'status' => $status,
        'age' => $statusAge,
        'fresh' => $statusFresh,
        'controls' => $statusFresh && $csrfToken !== '' && is_dir(dirname($commandFile)) && is_writable(dirname($commandFile)),
        'service' => (string)($liveService['state'] ?? 'unavailable'),
    ], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}
$controlsEnabled = $statusFresh && $csrfToken !== '' && is_dir(dirname($commandFile)) && is_writable(dirname($commandFile));
$currentMode = (string)($status['mode'] ?? '');
$serviceInfo = rp2040_helper_json('status');
$serviceState = (string)($serviceInfo['state'] ?? 'unavailable');
$inventory = rp2040_helper_json('inventory');
$config = rp2040_helper_json('get-config');
$serialConfig = rp2040_helper_json('serial-config');
if (!is_array($serialConfig) || !is_array($serialConfig['ports'] ?? null)) $serialConfig = ['selected' => 'auto', 'ports' => []];
$selectedSerialPort = is_string($serialConfig['selected'] ?? null) ? $serialConfig['selected'] : 'auto';
$availableSerialPorts = array_values(array_filter($serialConfig['ports'], 'is_string'));
if (!is_array($inventory)) $inventory = [];
if (!is_array($config) || !is_array($config['fans'] ?? null)) $config = ['fans' => ['fan1' => ['disks' => [], 'use_cpu' => false], 'fan2' => ['disks' => [], 'use_cpu' => false]]];
$selectedKeys = ['fan1' => [], 'fan2' => []];
foreach (['fan1', 'fan2'] as $fanKey) {
    foreach (($config['fans'][$fanKey]['disks'] ?? []) as $disk) {
        if (is_array($disk) && is_string($disk['model'] ?? null) && is_string($disk['serial'] ?? null)) $selectedKeys[$fanKey][hash('sha256', $disk['model'] . "\0" . $disk['serial'])] = true;
    }
}
?>
<div class="rp2040-fan-control">
  <style>
    .rp2040-fan-control{max-width:1440px;margin:0 auto;padding:0 12px 28px;box-sizing:border-box}
    .rp2040-fan-control *{box-sizing:border-box}
    .rp2040-fan-control .rp2040-layout{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;align-items:start}
    .rp2040-fan-control .rp2040-card{min-width:0;margin:0 0 16px;border:1px solid #ccc;border-radius:4px;background:rgba(255,255,255,.35);overflow:hidden}
    .rp2040-fan-control .rp2040-card>.panel-heading{font-weight:700}
    .rp2040-fan-control .rp2040-card>.panel-body{padding:16px}
    .rp2040-fan-control .rp2040-disks{display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:8px;max-height:340px;overflow:auto;padding:10px;background:rgba(0,0,0,.035);border:1px solid #ddd;border-radius:4px}
    .rp2040-fan-control .rp2040-disk{display:flex;gap:7px;align-items:flex-start;margin:0;padding:8px;border:1px solid #ddd;border-radius:3px;background:rgba(255,255,255,.45);overflow-wrap:anywhere}
    .rp2040-fan-control .rp2040-disk input{flex:0 0 auto;margin-top:3px}
    .rp2040-fan-control .rp2040-disk small{display:block;color:#555;margin-top:3px}
    .rp2040-fan-control .rp2040-status-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;align-items:start}
    .rp2040-fan-control .rp2040-metric{display:grid;grid-template-columns:minmax(130px,1fr) minmax(100px,1fr);gap:10px;padding:8px 10px;border-bottom:1px solid #ddd}
    .rp2040-fan-control .rp2040-metric:last-child{border-bottom:0}
    .rp2040-fan-control .rp2040-metric strong{overflow-wrap:anywhere}
    .rp2040-fan-control .rp2040-fan-metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
    .rp2040-fan-control .rp2040-fan-metric{padding:14px;border:1px solid #ddd;border-radius:4px;background:rgba(0,0,0,.025)}
    .rp2040-fan-control .rp2040-fan-metric h4{margin:0 0 12px}
    .rp2040-fan-control .rp2040-fan-metric .rp2040-metric{padding-left:0;padding-right:0}
    .rp2040-fan-control .rp2040-status-layout{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
    .rp2040-fan-control .rp2040-status-layout>[data-live="warnings"]{grid-column:1/-1}
    .rp2040-fan-control .rp2040-full{grid-column:1/-1}
    .rp2040-fan-control h3{margin-top:0}
    @media(max-width:800px){.rp2040-fan-control .rp2040-layout,.rp2040-fan-control .rp2040-status-grid,.rp2040-fan-control .rp2040-fan-metrics,.rp2040-fan-control .rp2040-status-layout{grid-template-columns:minmax(0,1fr)}.rp2040-fan-control .rp2040-full{grid-column:auto}}
  </style>
  <h2>RP2040 Fan Control</h2>
  <p>Estado y modos del controlador. El daemon Python conserva el control térmico y la comunicación con el RP2040.</p>

  <?php if ($error !== null): ?><div class="alert alert-danger"><?= rp2040_h($error) ?></div><?php endif; ?>
  <?php if ($notice !== null): ?><div class="alert alert-info" data-live="command-result" role="status"><?= rp2040_h($notice) ?></div><?php endif; ?>
  <div class="rp2040-layout">
  <div class="panel panel-default rp2040-card">
    <div class="panel-heading">Servicio del daemon</div>
    <div class="panel-body">
      <p>Estado del servicio: <strong data-live="service"><?= rp2040_h($serviceState) ?></strong></p>
      <?php foreach (['start' => 'Iniciar', 'restart' => 'Reiniciar', 'stop' => 'Detener'] as $serviceAction => $serviceLabel): ?>
        <form method="post" action="" style="display:inline-block; margin:0 8px 8px 0;" onsubmit="return confirm('¿Confirmas esta operación sobre el daemon?');">
          <input type="hidden" name="csrf_token" value="<?= rp2040_h($csrfToken) ?>">
          <input type="hidden" name="operation" value="<?= rp2040_h($serviceAction) ?>">
          <button class="btn <?= $serviceAction === 'start' ? 'btn-success' : ($serviceAction === 'stop' ? 'btn-danger' : 'btn-default') ?>" type="submit" <?= $csrfToken === '' ? 'disabled' : '' ?>><?= rp2040_h($serviceLabel) ?></button>
        </form>
      <?php endforeach; ?>
      <p class="text-muted">Iniciar valida la configuración, crea ENABLE y arranca el daemon. Si el RP2040 no está conectado, el daemon reintentará la conexión en fail-safe lógico; no se puede asegurar que se hayan aplicado órdenes a los ventiladores.</p>
    </div>
  </div>

  <div class="panel panel-default rp2040-card">
    <div class="panel-heading">Puerto serie del RP2040</div>
    <div class="panel-body">
      <p>Elige una ruta estable del RP2040 antes de iniciar. Solo se ofrecen puertos ttyACM y rutas by-id compatibles; no se seleccionan puertos ttyS.</p>
      <form method="post" action="">
        <input type="hidden" name="csrf_token" value="<?= rp2040_h($csrfToken) ?>">
        <input type="hidden" name="operation" value="save_serial_port">
        <label for="rp2040_serial_port">Puerto</label>
        <select id="rp2040_serial_port" name="serial_port" class="form-control" style="max-width:560px; margin-bottom:10px;" <?= $csrfToken === '' ? 'disabled' : '' ?>>
          <option value="auto" <?= $selectedSerialPort === 'auto' ? 'selected' : '' ?>>Automático (un único ttyACM compatible)</option>
          <?php if ($selectedSerialPort !== 'auto' && !in_array($selectedSerialPort, $availableSerialPorts, true)): ?>
            <option value="<?= rp2040_h($selectedSerialPort) ?>" selected disabled><?= rp2040_h($selectedSerialPort) ?> (no detectado)</option>
          <?php endif; ?>
          <?php foreach ($availableSerialPorts as $serialPort): ?>
            <option value="<?= rp2040_h($serialPort) ?>" <?= $selectedSerialPort === $serialPort ? 'selected' : '' ?>><?= rp2040_h($serialPort) ?></option>
          <?php endforeach; ?>
        </select>
        <button class="btn btn-default" type="submit" <?= $csrfToken === '' ? 'disabled' : '' ?>>Guardar puerto serie</button>
      </form>
      <?php if (!$availableSerialPorts): ?><p class="text-warning">No se detecta un puerto ttyACM/by-id. Puedes guardar Automático para que el daemon intente reconectar; sin RP2040 no podrá transmitir órdenes.</p><?php endif; ?>
      <p class="text-muted">El cambio solo se acepta con el daemon detenido y ENABLE ausente. Si está en marcha, deténlo antes de cambiar el puerto.</p>
    </div>
  </div>

  </div>

  <div class="panel panel-default rp2040-card">
    <div class="panel-heading">Configuración de fuentes térmicas</div>
    <div class="panel-body">
      <p>Un HDD solo puede pertenecer a un ventilador. Puedes combinar HDD y CPU en cualquiera de los dos grupos.</p>
      <?php if (!$inventory): ?><div class="alert alert-warning">No se ha podido obtener el inventario de HDD. Comprueba que el auxiliar privilegiado está instalado y autorizado.</div><?php endif; ?>
      <form method="post" action="">
        <input type="hidden" name="csrf_token" value="<?= rp2040_h($csrfToken) ?>">
        <input type="hidden" name="operation" value="save_config">
        <div class="rp2040-layout">
          <?php foreach (['fan1' => 'FAN1', 'fan2' => 'FAN2'] as $fanKey => $fanLabel): ?>
            <div>
              <h4><?= rp2040_h($fanLabel) ?></h4>
              <label><input type="checkbox" name="use_cpu_<?= rp2040_h($fanKey) ?>" value="1" <?= !empty($config['fans'][$fanKey]['use_cpu']) ? 'checked' : '' ?>> Usar temperatura de CPU</label>
              <div class="rp2040-disks">
                <?php foreach ($inventory as $disk):
                  if (!is_array($disk) || !is_string($disk['model'] ?? null) || !is_string($disk['serial'] ?? null)) continue;
                  $diskKey = hash('sha256', $disk['model'] . "\0" . $disk['serial']);
                  $checked = isset($selectedKeys[$fanKey][$diskKey]);
                  $otherFan = $fanKey === 'fan1' ? 'fan2' : 'fan1';
                  $assignedElsewhere = isset($selectedKeys[$otherFan][$diskKey]);
                ?>
                  <label class="rp2040-disk" style="font-weight:normal;">
                    <input type="checkbox" name="<?= rp2040_h($fanKey) ?>_disks[]" value="<?= rp2040_h($diskKey) ?>" <?= $checked ? 'checked' : '' ?> <?= $assignedElsewhere ? 'disabled' : '' ?>>
                    <strong><?= rp2040_h($disk['model']) ?></strong><br>
                    <small><?= rp2040_h($disk['device'] ?? '') ?> · Serie: <?= rp2040_h($disk['serial']) ?><?= $assignedElsewhere ? ' · Asignado a ' . rp2040_h(strtoupper($otherFan)) : '' ?></small>
                  </label>
                <?php endforeach; ?>
              </div>
            </div>
          <?php endforeach; ?>
        </div>
        <button class="btn btn-primary" type="submit" <?= $csrfToken === '' ? 'disabled' : '' ?>>Guardar configuración</button>
      </form>
      <p class="text-muted">Los cambios se guardan de forma persistente. Si el daemon está en marcha, reinícialo para que adopte la nueva configuración.</p>
    </div>
  </div>

  <div class="rp2040-status-layout">
  <div class="panel panel-default rp2040-card">
    <div class="panel-heading">Estado del controlador</div>
    <div class="panel-body">
      <div class="rp2040-metric"><strong>Daemon</strong><span data-live="daemon"><?= rp2040_value($status['daemon']['state'] ?? null) ?></span></div>
      <div class="rp2040-metric"><strong>Versión</strong><span data-live="version"><?= rp2040_value($status['daemon']['version'] ?? null) ?></span></div>
      <div class="rp2040-metric"><strong>Modo actual</strong><span><strong data-live="mode"><?= rp2040_value($currentMode) ?></strong></span></div>
      <div class="rp2040-metric"><strong>Serie conectada</strong><span data-live="connected"><?= array_key_exists('connected', $status['serial'] ?? []) ? (($status['serial']['connected'] === true) ? 'Sí' : 'No') : '—' ?></span></div>
      <div class="rp2040-metric"><strong>Fail-safe</strong><span data-live="failsafe"><?= array_key_exists('fail_safe', $status['serial'] ?? []) ? (($status['serial']['fail_safe'] === true) ? 'ACTIVO' : 'No') : '—' ?></span></div>
      <div class="rp2040-metric"><strong>Último envío correcto</strong><span data-live="lasttx"><?= rp2040_value($status['serial']['last_tx_age_seconds'] ?? null, ' s') ?></span></div>
      <div class="rp2040-metric"><strong>Reconexiones</strong><span data-live="reconnects"><?= rp2040_value($status['serial']['reconnect_count'] ?? null) ?></span></div>
      <div class="rp2040-metric"><strong>CPU</strong><span data-live="cpu"><?= rp2040_temp($status['cpu_temperature_c'] ?? null) ?></span></div>
      <div class="rp2040-metric"><strong>Última actualización</strong><span data-live="updated"><?= $timestamp > 0 ? rp2040_h(date('Y-m-d H:i:s', (int)$timestamp)) : '—' ?><?= $statusAge !== null ? ' (' . rp2040_h((string)$statusAge) . ' s)' : '' ?></span></div>
    </div>
  </div>

  <?php
    $sourceWarnings = is_array($status['source_warnings'] ?? null) ? $status['source_warnings'] : [];
    $hasSourceWarnings = false;
    foreach (['fan1', 'fan2'] as $warningFan) {
      if (is_array($sourceWarnings[$warningFan] ?? null) && count($sourceWarnings[$warningFan]) > 0) $hasSourceWarnings = true;
    }
  ?>
  <?php if ($hasSourceWarnings): ?>
    <div class="alert alert-warning" role="alert" data-live="warnings">
      <strong>Advertencias de fuentes térmicas</strong>
      <ul>
        <?php foreach (['fan1' => 'FAN1', 'fan2' => 'FAN2'] as $warningFan => $warningLabel): ?>
          <?php foreach (($sourceWarnings[$warningFan] ?? []) as $sourceWarning): ?>
            <li><?= rp2040_h($warningLabel . ': ' . (string)$sourceWarning) ?></li>
          <?php endforeach; ?>
        <?php endforeach; ?>
      </ul>
      <p>Las fuentes restantes con lecturas válidas siguen regulando el ventilador. Si no queda ninguna fuente válida, se ordena el 100 %.</p>
    </div>
  <?php endif; ?>

  <div class="panel panel-default rp2040-card">
    <div class="panel-heading">Ventiladores</div>
    <div class="panel-body">
      <div class="rp2040-fan-metrics">
        <?php foreach (['fan1' => 'FAN1', 'fan2' => 'FAN2'] as $key => $label): $fan = is_array($status['fans'][$key] ?? null) ? $status['fans'][$key] : []; ?>
          <section class="rp2040-fan-metric"><h4><?= rp2040_h($label) ?></h4>
            <div class="rp2040-metric"><strong>Temperatura</strong><span data-live="<?= $key ?>-temp"><?= rp2040_temp($fan['temperature_c'] ?? null) ?></span></div>
            <div class="rp2040-metric"><strong>Comando enviado</strong><span data-live="<?= $key ?>-command"><?= rp2040_value($fan['command_percent'] ?? null, '%') ?></span></div>
            <div class="rp2040-metric"><strong>Objetivo calculado</strong><span data-live="<?= $key ?>-target"><?= rp2040_value($fan['target_percent'] ?? null, '%') ?></span></div>
          </section>
        <?php endforeach; ?>
      </div>
      <p class="text-muted">Los porcentajes son valores de comando; no representan RPM medidas por tacómetro.</p>
    </div>
  </div>

  </div>
  <div class="panel panel-default rp2040-card">
    <div class="panel-heading">Modo de ventilación</div>
    <div class="panel-body">
      <p>Selecciona un modo. El daemon confirma la escritura serie; el firmware actual no devuelve ACK.</p>
      <?php foreach ($allowedModes as $mode): ?>
        <form method="post" action="" style="display:inline-block; margin:0 8px 8px 0;">
          <input type="hidden" name="csrf_token" value="<?= rp2040_h($csrfToken) ?>">
          <input type="hidden" name="mode" value="<?= rp2040_h($mode) ?>">
          <button class="btn <?= $currentMode === $mode ? 'btn-primary' : 'btn-default' ?>" data-mode-button="<?= rp2040_h($mode) ?>" type="submit" <?= (!$controlsEnabled || $currentMode === $mode) ? 'disabled' : '' ?>><?= rp2040_h($mode) ?></button>
        </form>
      <?php endforeach; ?>
      <?php if ($csrfToken === ''): ?><p class="text-danger">No se ha podido obtener el token CSRF de Unraid; los cambios de modo están deshabilitados.</p><?php endif; ?>
    </div>
  </div>
</div>
<?php if ($modeReturnUrl !== null): ?>
<script>
window.location.replace(<?= json_encode($modeReturnUrl, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_THROW_ON_ERROR) ?>);
</script>
<?php endif; ?>
<script>
(function(){
  const root=document.querySelector('.rp2040-fan-control'); if(!root)return;
  const trackedRequestId=<?= json_encode($requestIdFromQuery, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_THROW_ON_ERROR) ?>;
  const endpoint='/plugins/rp2040-fan-control/pages/index.php?rp2040_live=1'+(trackedRequestId?'&request_id='+encodeURIComponent(trackedRequestId):'');
  const put=(key,value)=>{const el=root.querySelector('[data-live="'+key+'"]');if(el)el.textContent=value==null||value===''?'—':String(value)};
  const fmtTemp=v=>typeof v==='number'?v.toLocaleString('es-ES',{minimumFractionDigits:1,maximumFractionDigits:1})+' °C':'—';
  const fmtVal=(v,s='')=>v==null?'—':String(v)+s;
  async function update(){try{
    const response=await fetch(endpoint,{cache:'no-store',credentials:'same-origin'});if(!response.ok)return;
    const data=await response.json(),s=data.status||{},serial=s.serial||{},fans=s.fans||{},daemon=s.daemon||{};
    const result=data.command_result;
    if(trackedRequestId&&result&&result.request_id===trackedRequestId){
      const notice=root.querySelector('[data-live="command-result"]');
      if(notice){notice.textContent=String(result.message||'Solicitud procesada.')+(result.ok&&result.applied_mode?' Modo: '+result.applied_mode:'');notice.classList.toggle('alert-info',result.ok===true);notice.classList.toggle('alert-danger',result.ok!==true)}
    }
    put('service',data.service);put('daemon',daemon.state);put('version',daemon.version);put('mode',s.mode);
    put('connected',serial.connected===true?'Sí':serial.connected===false?'No':'—');put('failsafe',serial.fail_safe===true?'ACTIVO':serial.fail_safe===false?'No':'—');
    put('lasttx',fmtVal(serial.last_tx_age_seconds==null?null:Number(serial.last_tx_age_seconds).toFixed(1),' s'));put('reconnects',serial.reconnect_count);put('cpu',fmtTemp(s.cpu_temperature_c));
    const ts=Number(s.timestamp||0);put('updated',ts?new Date(ts*1000).toLocaleString('sv-SE')+' ('+String(data.age??'—')+' s)':'—');
    ['fan1','fan2'].forEach(k=>{const f=fans[k]||{};put(k+'-temp',fmtTemp(f.temperature_c));put(k+'-command',fmtVal(f.command_percent,'%'));put(k+'-target',fmtVal(f.target_percent,'%'))});
    root.querySelectorAll('[data-mode-button]').forEach(button=>{const active=button.dataset.modeButton===(s.mode||'');button.disabled=!data.controls||active;button.classList.toggle('btn-primary',active);button.classList.toggle('btn-default',!active)});
    let stale=root.querySelector('[data-live="stale"]');if(!data.fresh&&!stale){stale=document.createElement('div');stale.className='alert alert-warning';stale.dataset.live='stale';stale.textContent='El estado no está disponible o lleva más de 10 segundos sin actualizarse. Los controles de modo quedan deshabilitados.';root.querySelector('h2').after(stale)}else if(data.fresh&&stale)stale.remove();
    let warnings=root.querySelector('[data-live="warnings"]');const all=[];Object.entries(s.source_warnings||{}).forEach(([fan,items])=>(items||[]).forEach(item=>all.push((fan==='fan1'?'FAN1':'FAN2')+': '+item)));
    if(all.length){if(!warnings){warnings=document.createElement('div');warnings.className='alert alert-warning';warnings.dataset.live='warnings';root.querySelector('.rp2040-status-layout').prepend(warnings)}warnings.innerHTML='<strong>Advertencias de fuentes térmicas</strong><ul>'+all.map(x=>'<li>'+x.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))+'</li>').join('')+'</ul><p>Las fuentes restantes con lecturas válidas siguen regulando el ventilador. Si no queda ninguna fuente válida, se ordena el 100 %.</p>'}else if(warnings)warnings.remove();
  }catch(e){console.error('RP2040 Fan Control: fallo al actualizar el estado',e)}}
  update();window.setInterval(update,5000);
})();
</script>
