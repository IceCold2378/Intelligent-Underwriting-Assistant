"""
Tests for authentication endpoints.
"""

import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    """Can register a new user and receive a JWT token."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "securepassword123",
        "full_name": "New User",
        "organization": "Test Corp",
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    """Cannot register with the same email twice."""
    payload = {
        "email": "duplicate@example.com",
        "password": "securepassword123",
        "full_name": "User One",
    }
    response1 = await client.post("/api/v1/auth/register", json=payload)
    assert response1.status_code == 201

    response2 = await client.post("/api/v1/auth/register", json=payload)
    assert response2.status_code == 401  # AuthenticationError


@pytest.mark.asyncio
async def test_register_short_password(client):
    """Cannot register with a password shorter than 8 characters."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "short@example.com",
        "password": "1234567",  # 7 chars
        "full_name": "Short Pass",
    })
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_success(client):
    """Can log in with correct credentials."""
    # Register first
    await client.post("/api/v1/auth/register", json={
        "email": "logintest@example.com",
        "password": "securepassword123",
        "full_name": "Login Test",
    })

    # Login
    response = await client.post("/api/v1/auth/login", json={
        "email": "logintest@example.com",
        "password": "securepassword123",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """Cannot log in with wrong password."""
    await client.post("/api/v1/auth/register", json={
        "email": "wrongpass@example.com",
        "password": "securepassword123",
        "full_name": "Wrong Pass",
    })

    response = await client.post("/api/v1/auth/login", json={
        "email": "wrongpass@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_profile(client, auth_headers):
    """Can fetch own profile with valid token."""
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert data["role"] == "analyst"


@pytest.mark.asyncio
async def test_get_profile_no_auth(client):
    """Cannot access profile without a token."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
