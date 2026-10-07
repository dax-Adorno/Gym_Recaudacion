from __future__ import annotations

import argparse
import base64
import getpass
import json
import re
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from moove_recovery.infrastructure.licensing import PRODUCT, canonical_payload


def create_key(password: bytes) -> tuple[bytes, bytes]:
    if len(password) < 12:
        raise ValueError("La clave debe protegerse con al menos 12 caracteres.")
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(password),
    )
    return private, key.public_key().public_bytes_raw()


def issue_license(private: bytes, password: bytes, code: str) -> bytes:
    if not re.fullmatch(r"MR1-[0-9A-F]{64}", code):
        raise ValueError("Codigo de equipo invalido.")
    key = serialization.load_pem_private_key(private, password=password)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Se necesita una clave Ed25519.")
    payload: dict[str, object] = {"schema": 1, "product": PRODUCT, "machine": code}
    signature = base64.b64encode(key.sign(canonical_payload(payload))).decode("ascii")
    return json.dumps({"payload": payload, "signature": signature}, indent=2).encode("ascii")


def outside_repository(path: Path) -> Path:
    resolved = path.resolve()
    repository = Path(__file__).resolve().parents[2]
    if resolved == repository or repository in resolved.parents:
        raise ValueError("Guarda claves y licencias fuera del repositorio.")
    return resolved


def save_new(path: Path, content: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description="Emisor privado de licencias MOOVE RECOVERY")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate-key")
    generate.add_argument("--private", type=Path, required=True)
    generate.add_argument("--public", type=Path, required=True)
    issue = subparsers.add_parser("issue")
    issue.add_argument("--private", type=Path, required=True)
    issue.add_argument("--machine", required=True)
    issue.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        private_path = outside_repository(args.private)
        if args.command == "generate-key":
            public_path = outside_repository(args.public)
            if private_path == public_path or private_path.exists() or public_path.exists():
                raise ValueError("Elige dos archivos nuevos y diferentes.")
            password = getpass.getpass("Contrasena para proteger la clave: ")
            if password != getpass.getpass("Repetir contrasena: "):
                raise ValueError("Las contrasenas no coinciden.")
            private, public = create_key(password.encode())
            save_new(private_path, private)
            try:
                save_new(public_path, public)
            except OSError:
                private_path.unlink()
                raise
            print("Clave protegida creada. Conserva una copia segura fuera del repositorio.")
        else:
            output = outside_repository(args.output)
            password = getpass.getpass("Contrasena de la clave: ").encode()
            license_bytes = issue_license(private_path.read_bytes(), password, args.machine)
            save_new(output, license_bytes)
            print("Licencia emitida. Entrega solo el archivo de licencia al cliente.")
    except (ValueError, OSError):
        print(
            "No se pudo completar: revisa rutas, permisos, codigo y contrasena. No se sobrescriben archivos."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
