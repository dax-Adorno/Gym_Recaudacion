import base64
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from moove_recovery.infrastructure.licensing import (
    PRODUCT,
    LicenseError,
    canonical_payload,
    machine_code,
    validate_license,
)

GUID = "12345678-1234-1234-1234-123456789abc"


def signed_license(key, **changes):
    payload = {"schema": 1, "product": PRODUCT, "machine": machine_code(GUID)} | changes
    return json.dumps(
        {
            "payload": payload,
            "signature": base64.b64encode(key.sign(canonical_payload(payload))).decode(),
        }
    ).encode()


def test_valid_license_and_machine_code():
    key = Ed25519PrivateKey.generate()
    code = machine_code(GUID)
    assert code == machine_code(f" {GUID.upper()} ")
    validate_license(signed_license(key), key.public_key().public_bytes_raw(), code)


@pytest.mark.parametrize("guid", ["", "PC-Lucas", "00:11:22:33:44:55"])
def test_invalid_machine_identity(guid):
    with pytest.raises(LicenseError):
        machine_code(guid)


@pytest.mark.parametrize(
    "changes",
    [{"schema": 2}, {"schema": True}, {"product": "other"}, {"machine": "invalid"}, {"extra": 1}],
)
def test_invalid_signed_payload(changes):
    key = Ed25519PrivateKey.generate()
    with pytest.raises(LicenseError):
        validate_license(
            signed_license(key, **changes), key.public_key().public_bytes_raw(), machine_code(GUID)
        )


def test_other_machine_tampered_license_and_wrong_signer():
    key = Ed25519PrivateKey.generate()
    raw = signed_license(key)
    public = key.public_key().public_bytes_raw()
    other = machine_code("aaaaaaaa-1234-1234-1234-123456789abc")
    with pytest.raises(LicenseError, match="otra computadora"):
        validate_license(raw, public, other)
    altered = json.loads(raw)
    altered["payload"]["machine"] = other
    with pytest.raises(LicenseError):
        validate_license(json.dumps(altered).encode(), public, other)
    with pytest.raises(LicenseError):
        validate_license(
            raw, Ed25519PrivateKey.generate().public_key().public_bytes_raw(), machine_code(GUID)
        )


@pytest.mark.parametrize(
    "raw", [b"", b"x" * 8193, b"[]", b"{", b"{}", b'{"payload":1,"payload":2,"signature":""}']
)
def test_malformed_license(raw):
    with pytest.raises(LicenseError):
        validate_license(raw, b"x" * 32, machine_code(GUID))
