import uuid

import pytest

from app.core.security import (
    TokenPayloadError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify_roundtrip():
    plain = "s3cret-Password!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_create_and_decode_access_token_roundtrip():
    user_id = str(uuid.uuid4())
    token = create_access_token(subject=user_id, extra_claims={"role": "admin"})
    payload = decode_access_token(token)
    assert payload["sub"] == user_id
    assert payload["role"] == "admin"


def test_decode_access_token_rejects_garbage():
    with pytest.raises(TokenPayloadError):
        decode_access_token("not-a-real-jwt")


def test_decode_access_token_rejects_tampered_signature():
    token = create_access_token(subject=str(uuid.uuid4()))
    tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    with pytest.raises(TokenPayloadError):
        decode_access_token(tampered)
