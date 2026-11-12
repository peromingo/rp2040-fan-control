<?php
/* Test helper only: mirrors the panel's no-overwrite publication primitive. */
$dir = $argv[1];
$id = $argv[2];
$ready = $argv[3];
$release = $argv[4];
$tmp = tempnam($dir, '.command-');
if ($tmp === false) { fwrite(STDERR, "tempnam failed\n"); exit(2); }
$data = json_encode([
    'request_id' => $id,
    'mode' => ($id === 'request_A') ? 'AUTO' : 'TURBO',
], JSON_THROW_ON_ERROR) . "\n";
if (file_put_contents($tmp, $data, LOCK_EX) !== strlen($data)) {
    @unlink($tmp); fwrite(STDERR, "write failed\n"); exit(3);
}
@chmod($tmp, 0640);
if (file_put_contents($ready, 'ready') === false) {
    @unlink($tmp); fwrite(STDERR, "ready marker failed\n"); exit(4);
}
$deadline = microtime(true) + 5;
while (!is_file($release) && microtime(true) < $deadline) { usleep(1000); }
if (!is_file($release)) { @unlink($tmp); fwrite(STDERR, "release timeout\n"); exit(5); }
if (@link($tmp, $dir . '/command.json')) {
    @unlink($tmp); echo "WON $id\n"; exit(0);
}
@unlink($tmp); echo "LOST $id\n"; exit(1);
