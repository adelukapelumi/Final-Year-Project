from __future__ import annotations

import base64
import hashlib
import hmac
import secrets


def hash_nin(nin: str) -> str:
    normalized = "".join(ch for ch in nin if ch.isdigit())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_session_token() -> str:
    return secrets.token_urlsafe(32)


def _derive_keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    stream = bytearray()
    counter = 0
    while len(stream) < length:
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        stream.extend(block)
        counter += 1
    return bytes(stream[:length])


def encrypt_vote(vote_value: str, key: bytes) -> str:
    plaintext = vote_value.encode("utf-8")
    nonce = secrets.token_bytes(16)
    keystream = _derive_keystream(key, nonce, len(plaintext))
    ciphertext = bytes(left ^ right for left, right in zip(plaintext, keystream))
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_vote(ciphertext: str, key: bytes) -> str:
    payload = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))
    nonce = payload[:16]
    encrypted_vote = payload[16:]
    keystream = _derive_keystream(key, nonce, len(encrypted_vote))
    plaintext = bytes(left ^ right for left, right in zip(encrypted_vote, keystream))
    return plaintext.decode("utf-8")


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
