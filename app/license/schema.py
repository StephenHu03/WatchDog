from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from typing import Any


def canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class LicensePayload:
    version: int
    license_id: str
    product_id: str
    product_version: str
    bind_mode: str
    domain: str | None
    ipv4: str | None
    issued_at: str
    expires_at: str | None = None
    features: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def create(cls, license_id: str, product_version: str, domain: str | None, ipv4: str | None,
               product_id: str = "PRODUCT-001", expires_at: str | None = None,
               features: list[str] | None = None) -> "LicensePayload":
        return cls(1, license_id, product_id, product_version, "DOMAIN_OR_IPV4", domain, ipv4,
                   datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                   expires_at, tuple(features or []))

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "license_id": self.license_id, "product_id": self.product_id,
                "product_version": self.product_version, "bind_mode": self.bind_mode, "domain": self.domain,
                "ipv4": self.ipv4, "issued_at": self.issued_at, "expires_at": self.expires_at,
                "features": list(self.features)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LicensePayload":
        required = ["version", "license_id", "product_id", "product_version", "bind_mode", "issued_at"]
        if any(key not in data for key in required):
            raise ValueError("LIC-1006 License malformed")
        return cls(int(data["version"]), str(data["license_id"]), str(data["product_id"]),
                   str(data["product_version"]), str(data["bind_mode"]), data.get("domain"), data.get("ipv4"),
                   str(data["issued_at"]), data.get("expires_at"), tuple(data.get("features", [])))


@dataclass(frozen=True)
class LicenseDocument:
    payload: LicensePayload
    signature: str

    def to_dict(self) -> dict[str, Any]:
        result = self.payload.to_dict()
        result["signature"] = self.signature
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LicenseDocument":
        signature = data.get("signature")
        if not isinstance(signature, str) or not signature:
            raise ValueError("LIC-1006 License malformed")
        return cls(LicensePayload.from_dict(data), signature)
