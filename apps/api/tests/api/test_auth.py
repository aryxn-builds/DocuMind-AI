import os
import time
from unittest.mock import patch

os.environ["SUPABASE_URL"] = "https://mock.supabase.co"

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Helper functions to generate keys
def generate_rsa_key_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key

def generate_ec_key_pair():
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key

# Generate keys once for tests
rsa_private_key = generate_rsa_key_pair()
rsa_public_key = rsa_private_key.public_key()
ec_private_key = generate_ec_key_pair()
ec_public_key = ec_private_key.public_key()

def get_pem(key, is_private=False):
    if is_private:
        return key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
    return key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

class MockPyJWK:
    def __init__(self, key, algorithm):
        self.key = key
        self.algorithm_name = algorithm

def create_mock_jwk(public_key, alg, kid="test-kid"):
    pem = get_pem(public_key)
    return MockPyJWK(pem, alg)

def generate_token(private_key, alg, payload_overrides=None, kid="test-kid"):
    payload = {
        "iss": "https://mock.supabase.co/auth/v1",
        "sub": "test-user-id",
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()) - 10
    }
    if payload_overrides:
        payload.update(payload_overrides)

    headers = {"kid": kid} if kid else {}
    return jwt.encode(payload, get_pem(private_key, True), algorithm=alg, headers=headers)


def test_get_me_unauthorized():
    response = client.get("/api/v1/me")
    assert response.status_code == 401

def test_get_me_invalid_token():
    response = client.get("/api/v1/me", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == 401
    assert "detail" in response.json()

@patch("app.core.security.jwks_client")
def test_valid_es256_token(mock_jwks_client):
    mock_jwks_client.get_signing_key_from_jwt.return_value = create_mock_jwk(ec_public_key, "ES256")
    token = generate_token(ec_private_key, "ES256")
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

@patch("app.core.security.jwks_client")
def test_valid_rs256_token(mock_jwks_client):
    mock_jwks_client.get_signing_key_from_jwt.return_value = create_mock_jwk(rsa_public_key, "RS256")
    token = generate_token(rsa_private_key, "RS256")
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

@patch("app.core.security.jwks_client")
def test_hs256_rejection(mock_jwks_client):
    # Mock JWKS returning an EC key
    mock_jwks_client.get_signing_key_from_jwt.return_value = create_mock_jwk(ec_public_key, "ES256")
    # But token is signed with HS256 (Algorithm Confusion attack attempt)
    # The attacker signs with HS256 using a plain string derived from the public key
    token = jwt.encode(
        {"iss": "https://mock.supabase.co/auth/v1", "sub": "test", "aud": "authenticated", "exp": int(time.time()) + 3600},
        "not-a-pem-but-a-secret-string",
        algorithm="HS256",
        headers={"kid": "test-kid"}
    )
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    # Should say Invalid token: The specified alg value is not allowed
    assert "The specified alg value is not allowed" in response.json()["detail"]

@patch("app.core.security.jwks_client")
def test_unsupported_asymmetric_rejection(mock_jwks_client):
    # token signed with ES384 but we only allow ES256 and RS256
    ec384_private = ec.generate_private_key(ec.SECP384R1())
    mock_jwks_client.get_signing_key_from_jwt.return_value = create_mock_jwk(ec384_private.public_key(), "ES384")
    token = generate_token(ec384_private, "ES384")
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "The specified alg value is not allowed" in response.json()["detail"]

@patch("app.core.security.jwks_client")
def test_invalid_signature(mock_jwks_client):
    # Use one key to sign, another key for JWKS verification
    wrong_key = generate_rsa_key_pair()
    mock_jwks_client.get_signing_key_from_jwt.return_value = create_mock_jwk(wrong_key.public_key(), "RS256")
    token = generate_token(rsa_private_key, "RS256")
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]

@patch("app.core.security.jwks_client")
def test_expiry_rejection(mock_jwks_client):
    mock_jwks_client.get_signing_key_from_jwt.return_value = create_mock_jwk(ec_public_key, "ES256")
    # Expired token
    token = generate_token(ec_private_key, "ES256", payload_overrides={"exp": int(time.time()) - 100})
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "Token has expired" in response.json()["detail"]

@patch("app.core.security.jwks_client")
def test_issuer_rejection(mock_jwks_client):
    mock_jwks_client.get_signing_key_from_jwt.return_value = create_mock_jwk(ec_public_key, "ES256")
    token = generate_token(ec_private_key, "ES256", payload_overrides={"iss": "https://wrong.issuer.com"})
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]

@patch("app.core.security.jwks_client")
def test_audience_rejection(mock_jwks_client):
    mock_jwks_client.get_signing_key_from_jwt.return_value = create_mock_jwk(ec_public_key, "ES256")
    token = generate_token(ec_private_key, "ES256", payload_overrides={"aud": "wrong-audience"})
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]
