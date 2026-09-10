from __future__ import annotations

import argparse
from pathlib import Path
from app.license.signer import LicenseSigner
from app.package.builder import BuildRequest, PackageBuilder

DEVELOPER = "Stephen Hu <stephenhu031028@gmail.com>"

def main() -> int:
    parser = argparse.ArgumentParser(description=f"Offline PHP LicenseProtector | Developer: {DEVELOPER}")
    sub = parser.add_subparsers(dest="command", required=True)
    keygen = sub.add_parser("keygen", help="Generate vendor Ed25519 key pair")
    keygen.add_argument("--private", required=True, type=Path)
    keygen.add_argument("--public", required=True, type=Path)
    build = sub.add_parser("build", help="Build a customer release ZIP")
    for name in ("project", "private-key", "public-key", "output"):
        build.add_argument(f"--{name}", required=True, type=Path)
    build.add_argument("--domain", default="")
    build.add_argument("--ipv4", default="")
    build.add_argument("--version", required=True)
    args = parser.parse_args()
    if args.command == "keygen":
        LicenseSigner.generate_keypair(args.private, args.public)
        print(f"Key pair generated. Developer: {DEVELOPER}")
        return 0
    result = PackageBuilder(print).build(BuildRequest(args.project, args.domain, args.ipv4, args.version,
                                                        args.output, args.private_key, args.public_key))
    print(f"Release: {result.zip_path}\nLicense ID: {result.license_id}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
