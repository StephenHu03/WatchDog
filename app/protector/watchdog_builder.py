from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from app.license.schema import LicenseDocument


class WatchdogBuilder:
    """Build the protected files copied into a customer release.

    The loader deliberately contains only the verification path. The business
    project remains ordinary editable PHP. ``core.bin`` is an opaque authenticated
    blob that makes the protected area less convenient to patch with a text editor.
    """

    def build(self, project_root: Path, document: LicenseDocument, public_key_path: Path) -> list[Path]:
        directory = project_root / "protected" / "watchdog"
        directory.mkdir(parents=True, exist_ok=True)
        public_pem = public_key_path.read_bytes()
        # PHP sodium requires the 32-byte raw Ed25519 public key. Keep the PEM
        # only on the vendor side and serialize the raw key into the release.
        public_raw = serialization.load_pem_public_key(public_pem).public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        public_b64 = base64.b64encode(public_raw).decode("ascii")
        # Store no private key in the release. The blob is only a tamper-evident
        # marker for the protected area; the signed license remains authoritative.
        payload = json.dumps({"license_id": document.payload.license_id, "product_id": document.payload.product_id}, sort_keys=True).encode()
        key = hashlib.sha256(public_raw + document.payload.license_id.encode()).digest()
        iv = hashlib.sha256(document.payload.license_id.encode() + public_raw).digest()[:16]
        cipher = base64.b64encode(iv + payload + hashlib.sha256(key + payload).digest()).decode("ascii")
        (directory / "core.bin").write_text(cipher, encoding="ascii")
        (directory / "public.key").write_text(public_b64, encoding="ascii")
        loader = '''<?php
/* LICENSE_PROTECTOR_BOOTSTRAP_V1 */
declare(strict_types=1);
$__lp_d = static function(string $v): string { $v = strtolower(trim($v)); if (strpos($v, '://') !== false) { $v = (string)(parse_url($v, PHP_URL_HOST) ?? ''); } else { $v = explode('/', $v, 2)[0]; $v = explode(':', $v, 2)[0]; } return rtrim($v, '.'); };
$__lp_i = static function(string $v): string { return filter_var(trim($v), FILTER_VALIDATE_IP, FILTER_FLAG_IPV4) ?: ''; };
$__lp_fail = static function(string $c): never { error_log('license_id=' . (defined('LP_LICENSE_ID') ? LP_LICENSE_ID : 'unknown') . ' error_code=' . $c . ' timestamp=' . gmdate('c')); http_response_code(403); exit('License validation failed (' . $c . ')'); };
$__lp_base = dirname(__DIR__, 2);
$__lp_license = $__lp_base . '/license.dat';
$__lp_pub = $__lp_base . '/protected/watchdog/public.key';
if (!is_file($__lp_license) || !is_file($__lp_pub)) { $__lp_fail('LIC-1001'); }
$__lp_raw = json_decode((string)file_get_contents($__lp_license), true);
if (!is_array($__lp_raw) || !isset($__lp_raw['signature'])) { $__lp_fail('LIC-1006'); }
$__lp_sig = base64_decode((string)$__lp_raw['signature'], true);
$__lp_payload = $__lp_raw; unset($__lp_payload['signature']);
/* LicenseSigner writes keys in lexical order; PHP preserves decoded object order.
   JSON_SORT_KEYS is unavailable on PHP 8.3, so do not require it at runtime. */
$__lp_canon = json_encode($__lp_payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
$__lp_public = base64_decode((string)file_get_contents($__lp_pub), true);
/* Ed25519 is intentionally verified by PHP's built-in sodium extension. OpenSSL's
   generic digest API does not support Ed25519 on all PHP 8.x builds. */
$__lp_ok = function_exists('sodium_crypto_sign_verify_detached') && is_string($__lp_sig) && is_string($__lp_public) && strlen($__lp_public) >= 32 && sodium_crypto_sign_verify_detached($__lp_sig, (string)$__lp_canon, substr($__lp_public, -32));
if (!$__lp_ok && !function_exists('sodium_crypto_sign_verify_detached')) { $__lp_fail('LIC-1007'); }
if (!$__lp_ok) { $__lp_fail('LIC-1002'); }
if (!defined('LP_LICENSE_ID')) { define('LP_LICENSE_ID', (string)$__lp_payload['license_id']); }
$__lp_exp = $__lp_payload['expires_at'] ?? null;
if ($__lp_exp && strtotime((string)$__lp_exp) <= time()) { $__lp_fail('LIC-1005'); }
/*
 * Hyperf starts bin/hyperf.php through CLI, which has no HTTP Host. Its
 * generated middleware includes this loader for every request and provides
 * $__lp_request_host in that include scope. Traditional PHP validates here.
 */
$__lp_require_binding = PHP_SAPI !== 'cli' || isset($__lp_request_host);
if ($__lp_require_binding) {
    $__lp_host = $__lp_d((string)($__lp_request_host ?? $_SERVER['HTTP_HOST'] ?? $_SERVER['SERVER_NAME'] ?? ''));
    $__lp_domain = $__lp_d((string)($__lp_payload['domain'] ?? ''));
    $__lp_dm = $___lp_domain !== '' && $__lp_host === $__lp_domain;
    $__lp_ips = [];
    foreach (gethostbynamel(gethostname()) ?: [] as $__lp_x) { if ($__lp_i($__lp_x) !== '') { $__lp_ips[] = $__lp_i($__lp_x); } }
    $__lp_cfg = $__lp_i((string)($_SERVER['SERVER_ADDR'] ?? '')); if ($__lp_cfg !== '') { $__lp_ips[] = $__lp_cfg; }
    $__lp_im = false; $__lp_want_ip = $__lp_i((string)($__lp_payload['ipv4'] ?? '')); foreach ($__lp_ips as $__lp_x) { if ($__lp_x === $__lp_want_ip) { $__lp_im = true; break; } }
    if (!$__lp_dm && !$__lp_im) { $__lp_fail($__lp_want_ip !== '' && !$__lp_ips ? 'LIC-1007' : 'LIC-1003'); }
}
$__lp_manifest = $__lp_base . '/MANIFEST';
if (is_file($__lp_manifest)) { $___lp_m = json_decode((string)file_get_contents($__lp_manifest), true); if (!is_array($___lp_m) || !isset($___lp_m['files'])) { $__lp_fail('LIC-1008'); } foreach ($___lp_m['files'] as $__lp_f => $__lp_h) { if (!is_file($__lp_base . '/' . $__lp_f) || hash_file('sha256', $__lp_base . '/' . $__lp_f) !== $__lp_h) { $__lp_fail('LIC-1008'); } } }
?>
'''.replace('$___lp_domain', '$__lp_domain').replace('$___lp_m', '$__lp_m')
        (directory / "loader.php").write_text(loader, encoding="utf-8", newline="\n")
        return [directory / "core.bin", directory / "public.key", directory / "loader.php"]
