<?php
/*
 * RP2040 Fan Control for Unraid — development UI 0.5.0.
 * The page never opens the serial port and never calculates fan curves.
 */

$statusFile = '/var/run/rp2040-fan-control/status.json';
$commandFile = '/var/run/rp2040-fan-control/command.json';
$resultFile = '/var/run/rp2040-fan-control/command-result.json';
$varIniFile = '/var/local/emhttp/var.ini';
$allowedModes = ['AUTO', 'SILENT', 'TURBO'];
$error = null;
$notice = null;
$submittedRequestId = '';

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

/* CSRF-protected POST: only writes a request file; daemon applies it. */
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
    $vars = is_readable($varIniFile) ? @parse_ini_file($varIniFile) : false;
    $expectedToken = is_array($vars) ? (string)($vars['csrf_token'] ?? '') : '';
    $postedToken = (string)($_POST['csrf_token'] ?? '');
    $mode = strtoupper((string)($_POST['mode'] ?? ''));

    if ($expectedToken === '' || $postedToken === '' || !hash_equals($expectedToken, $postedToken)) {
        http_response_code(403);
        $error = 'Solicitud rechazada: token CSRF ausente o no válido.';
    } elseif (!in_array($mode, $allowedModes, true)) {
        http_response_code(400);
        $error = 'Modo solicitado no válido.';
    } elseif (!is_dir(dirname($commandFile)) || !is_writable(dirname($commandFile))) {
        http_response_code(503);
        $error = 'El canal IPC no está disponible. Comprueba que el daemon está iniciado.';
    } elseif (is_file($commandFile)) {
        http_response_code(409);
        $error = 'Ya hay una solicitud pendiente. Espera a que el daemon la procese.';
    } else {
        try {
            $requestId = bin2hex(random_bytes(16));
            $request = [
                'schema_version' => 1,
                'request_id' => $requestId,
                'created_at' => microtime(true),
                'action' => 'set_mode',
                'mode' => $mode,
            ];
            $encoded = json_encode($request, JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR);
            $tmp = tempnam(dirname($commandFile), '.command-');
            if ($tmp === false) throw new RuntimeException('No se pudo crear el archivo temporal.');
            $written = file_put_contents($tmp, $encoded . "\n", LOCK_EX);
            if ($written === false || $written !== strlen($encoded . "\n")) {
                @unlink($tmp);
                throw new RuntimeException('No se pudo escribir la solicitud.');
            }
            @chmod($tmp, 0640);
            /*
             * link() publishes atomically without replacing an existing command.
             * rename() would overwrite a request created concurrently after the
             * earlier is_file() check, losing the first user's pending command.
             */
            if (!@link($tmp, $commandFile)) {
                @unlink($tmp);
                if (is_file($commandFile)) {
                    http_response_code(409);
                    $error = 'Ya hay una solicitud pendiente. Espera a que el daemon la procese.';
                } else {
                    throw new RuntimeException('No se pudo publicar la solicitud IPC.');
                }
            } else {
                @unlink($tmp);
            }
            if ($error !== null) {
                // Keep the page on this request; do not redirect after a conflict.
            } else {
                $submittedRequestId = $requestId;
            $pagePath = parse_url((string)($_SERVER['REQUEST_URI'] ?? '/'), PHP_URL_PATH);
            if (!is_string($pagePath) || $pagePath === '' || str_contains($pagePath, "\r") || str_contains($pagePath, "\n")) {
                $pagePath = '/Main';
            }
                header('Location: ' . $pagePath . '?request_id=' . rawurlencode($requestId), true, 303);
                exit;
            }
        } catch (Throwable $e) {
            $error = 'No se pudo enviar la solicitud al daemon.';
            error_log('RP2040 Fan Control IPC: ' . $e->getMessage());
        }
    }
}

$status = rp2040_read_json($statusFile);
$result = rp2040_read_json($resultFile);
$requestIdFromQuery = (string)($_GET['request_id'] ?? '');
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
$controlsEnabled = $statusFresh && $csrfToken !== '' && is_dir(dirname($commandFile)) && is_writable(dirname($commandFile));
$currentMode = (string)($status['mode'] ?? '');
?>
<div class="rp2040-fan-control">
  <h2>RP2040 Fan Control</h2>
  <p>Estado y modos del controlador. El daemon Python conserva el control térmico y la comunicación con el RP2040.</p>

  <?php if ($error !== null): ?><div class="alert alert-danger"><?= rp2040_h($error) ?></div><?php endif; ?>
  <?php if ($notice !== null): ?><div class="alert alert-info"><?= rp2040_h($notice) ?></div><?php endif; ?>
  <?php if (!$statusFresh): ?>
    <div class="alert alert-warning">El estado no está disponible o lleva más de 10 segundos sin actualizarse. Los controles quedan deshabilitados.</div>
  <?php endif; ?>

  <div class="panel panel-default">
    <div class="panel-heading">Estado del controlador</div>
    <div class="panel-body">
      <table class="table table-striped">
        <tbody>
          <tr><th>Daemon</th><td><?= rp2040_value($status['daemon']['state'] ?? null) ?></td></tr>
          <tr><th>Versión</th><td><?= rp2040_value($status['daemon']['version'] ?? null) ?></td></tr>
          <tr><th>Modo actual</th><td><strong><?= rp2040_value($currentMode) ?></strong></td></tr>
          <tr><th>Serie conectada</th><td><?= array_key_exists('connected', $status['serial'] ?? []) ? (($status['serial']['connected'] === true) ? 'Sí' : 'No') : '—' ?></td></tr>
          <tr><th>Fail-safe</th><td><?= array_key_exists('fail_safe', $status['serial'] ?? []) ? (($status['serial']['fail_safe'] === true) ? '<strong>ACTIVO</strong>' : 'No') : '—' ?></td></tr>
          <tr><th>Último envío correcto</th><td><?= rp2040_value($status['serial']['last_tx_age_seconds'] ?? null, ' s') ?></td></tr>
          <tr><th>Reconexiones</th><td><?= rp2040_value($status['serial']['reconnect_count'] ?? null) ?></td></tr>
          <tr><th>CPU</th><td><?= rp2040_temp($status['cpu_temperature_c'] ?? null) ?></td></tr>
          <tr><th>Última actualización</th><td><?= $timestamp > 0 ? rp2040_h(date('Y-m-d H:i:s', (int)$timestamp)) : '—' ?><?= $statusAge !== null ? ' (' . rp2040_h((string)$statusAge) . ' s)' : '' ?></td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="panel panel-default">
    <div class="panel-heading">Ventiladores</div>
    <div class="panel-body">
      <table class="table table-striped">
        <thead><tr><th>Grupo</th><th>Temperatura</th><th>Comando enviado</th><th>Objetivo calculado</th></tr></thead>
        <tbody>
          <?php foreach (['fan1' => 'FAN1', 'fan2' => 'FAN2'] as $key => $label): $fan = is_array($status['fans'][$key] ?? null) ? $status['fans'][$key] : []; ?>
            <tr>
              <td><?= rp2040_h($label) ?></td>
              <td><?= rp2040_temp($fan['temperature_c'] ?? null) ?></td>
              <td><?= rp2040_value($fan['command_percent'] ?? null, '%') ?></td>
              <td><?= rp2040_value($fan['target_percent'] ?? null, '%') ?></td>
            </tr>
          <?php endforeach; ?>
        </tbody>
      </table>
      <p class="text-muted">Los porcentajes son valores de comando; no representan RPM medidas por tacómetro.</p>
    </div>
  </div>

  <div class="panel panel-default">
    <div class="panel-heading">Modo de ventilación</div>
    <div class="panel-body">
      <p>Selecciona un modo. El cambio solo se considerará aplicado cuando el daemon confirme la solicitud.</p>
      <?php foreach ($allowedModes as $mode): ?>
        <form method="post" action="" style="display:inline-block; margin:0 8px 8px 0;">
          <input type="hidden" name="csrf_token" value="<?= rp2040_h($csrfToken) ?>">
          <input type="hidden" name="mode" value="<?= rp2040_h($mode) ?>">
          <button class="btn <?= $currentMode === $mode ? 'btn-primary' : 'btn-default' ?>" type="submit" <?= (!$controlsEnabled || $currentMode === $mode) ? 'disabled' : '' ?>><?= rp2040_h($mode) ?></button>
        </form>
      <?php endforeach; ?>
      <?php if ($csrfToken === ''): ?><p class="text-danger">No se ha podido obtener el token CSRF de Unraid; los cambios de modo están deshabilitados.</p><?php endif; ?>
    </div>
  </div>
</div>
