import os
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"

from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)

def test_get_me_unauthorized():
    response = client.get("/api/v1/me")
    assert response.status_code == 401

def test_get_me_invalid_token():
    response = client.get(
        "/api/v1/me", 
        headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == 401
    assert "detail" in response.json()
