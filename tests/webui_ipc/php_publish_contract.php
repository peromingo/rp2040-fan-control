<?php
/* Test helper: emits the same request schema consumed by RuntimeIPC. */
$dir = $argv[1];
$mode = $argv[2];
$id = $argv[3];
if (!in_array($mode, ['AUTO', 'SILENT', 'TURBO'], true)) { exit(2); }
if (!preg_match('/^[A-Za-z0-9_-]{8,80}$/', $id)) { exit(3); }
$request = [
    'schema_version' => 1,
    'request_id' => $id,
    'created_at' => microtime(true),
    'action' => 'set_mode',
    'mode' => $mode,
];
$encoded = json_encode($request, JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR) . "\n";
$tmp = tempnam($dir, '.command-');
if ($tmp === false) { exit(4); }
try {
    if (file_put_contents($tmp, $encoded, LOCK_EX) !== strlen($encoded)) { exit(5); }
    chmod($tmp, 0640);
    if (!link($tmp, $dir . '/command.json')) { exit(6); }
} finally {
    @unlink($tmp);
}
