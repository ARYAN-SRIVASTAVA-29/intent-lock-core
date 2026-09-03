import base64
import hashlib
import json
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def generate_ed25519_keypair() -> tuple[str, str]:
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    private_pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = public.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


def sign_text(private_pem: str, text: str) -> str:
    private = serialization.load_pem_private_key(private_pem.encode(), password=None)
    if not isinstance(private, Ed25519PrivateKey):
        raise ValueError("Expected Ed25519 private key")
    return base64.urlsafe_b64encode(private.sign(text.encode())).decode()


def verify_text(public_pem: str, text: str, signature: str) -> bool:
    try:
        public = serialization.load_pem_public_key(public_pem.encode())
        if not isinstance(public, Ed25519PublicKey):
            return False
        public.verify(base64.urlsafe_b64decode(signature.encode()), text.encode())
        return True
    except Exception:
        return False
