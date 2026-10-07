from __future__ import annotations

import base64
import hashlib
import json
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PRODUCT = "moove-recovery"
MAX_LICENSE_BYTES = 8192


class LicenseError(ValueError):
    pass


def machine_code(machine_guid: str) -> str:
    normalized = machine_guid.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", normalized):
        raise LicenseError("No se pudo identificar esta instalacion de Windows.")
    digest = hashlib.sha256(f"{PRODUCT}:machine:v1:{normalized}".encode()).hexdigest().upper()
    return f"MR1-{digest}"


def windows_machine_code() -> str:
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        ) as key:
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
    except OSError as error:
        raise LicenseError("No se pudo leer el identificador de Windows.") from error
    if not isinstance(guid, str):
        raise LicenseError("Identificador de Windows invalido.")
    return machine_code(guid)


def canonical_payload(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise LicenseError("La licencia contiene campos duplicados.")
        result[key] = value
    return result


def validate_license(raw: bytes, public_key: bytes, expected_machine: str) -> None:
    if not raw or len(raw) > MAX_LICENSE_BYTES:
        raise LicenseError("Tamano de licencia invalido.")
    try:
        document = json.loads(raw, object_pairs_hook=_unique_object)
        if not isinstance(document, dict) or set(document) != {"payload", "signature"}:
            raise LicenseError("Formato de licencia invalido.")
        payload = document["payload"]
        if not isinstance(payload, dict) or set(payload) != {"schema", "product", "machine"}:
            raise LicenseError("Contenido de licencia invalido.")
        if type(payload["schema"]) is not int or payload["schema"] != 1:
            raise LicenseError("Version de licencia no compatible.")
        if payload["product"] != PRODUCT:
            raise LicenseError("La licencia corresponde a otro producto.")
        if not isinstance(payload["machine"], str) or not re.fullmatch(
            r"MR1-[0-9A-F]{64}", payload["machine"]
        ):
            raise LicenseError("Codigo de equipo invalido.")
        signature = document["signature"]
        if not isinstance(signature, str):
            raise LicenseError("Firma de licencia invalida.")
        decoded = base64.b64decode(signature, validate=True)
        Ed25519PublicKey.from_public_bytes(public_key).verify(decoded, canonical_payload(payload))
        if payload["machine"] != expected_machine:
            raise LicenseError("Esta licencia pertenece a otra computadora.")
    except (ValueError, TypeError, InvalidSignature, RecursionError) as error:
        if isinstance(error, LicenseError):
            raise
        raise LicenseError("La licencia es invalida o fue modificada.") from error
