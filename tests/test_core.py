from pathlib import Path
import json

from app.license.schema import LicensePayload
from app.license.signer import LicenseSigner
from app.license.verifier import validate_document, LicenseValidationError
from app.validation.domain import domain_matches
from app.validation.ipv4 import ipv4_matches
from app.injector.hyperf_injector import HyperfInjector


def test_domain_and_ip_are_exact():
    assert domain_matches("https://Customer.Example.com:443/path", "customer.example.com")
    assert not domain_matches("evilcustomer.example.com", "customer.example.com")
    assert ipv4_matches(["10.0.0.2", "192.168.1.2"], "192.168.1.2")
    assert not ipv4_matches(["192.168.1.20"], "192.168.1.2")


def test_ed25519_and_or_rule(tmp_path: Path):
    private, public = tmp_path / "private.pem", tmp_path / "public.pem"
    LicenseSigner.generate_keypair(private, public)
    payload = LicensePayload.create("LIC-TEST", "1.0.0", "customer.example.com", "203.0.113.10")
    document = LicenseSigner.sign(payload, LicenseSigner.load_private(private))
    assert LicenseSigner.verify(document, LicenseSigner.load_public(public))
    validate_document(document, LicenseSigner.load_public(public), "wrong.example.com", ["203.0.113.10"])
    try:
        validate_document(document, LicenseSigner.load_public(public), "wrong.example.com", ["203.0.113.11"])
    except LicenseValidationError as error:
        assert error.code == "LIC-1003"
    else:
        raise AssertionError("mismatched domain and IP must fail")


def test_hyperf_injector_registers_request_guard(tmp_path: Path):
    """Hyperf checks a request Host rather than its CLI worker startup."""
    config = tmp_path / "config" / "autoload" / "middlewares.php"
    config.parent.mkdir(parents=True)
    config.write_text("<?php\nreturn ['http' => [\\App\\Middleware\\CommonMiddleware::class]];\n", encoding="utf-8")

    generated = HyperfInjector().inject(tmp_path)
    middleware = tmp_path / "app" / "Middleware" / "LicenseProtectorMiddleware.php"

    assert middleware in generated
    assert config in generated
    assert "$__lp_request_host = $request->getHeaderLine('Host');" in middleware.read_text(encoding="utf-8")
    assert "\\App\\Middleware\\LicenseProtectorMiddleware::class" in config.read_text(encoding="utf-8")
