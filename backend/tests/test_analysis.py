"""
Tests for analysis endpoints.
"""

import pytest


@pytest.mark.asyncio
async def test_analyze_requires_auth(client):
    """Analysis endpoint requires authentication."""
    response = await client.post("/api/v1/analysis")
    assert response.status_code in (401, 422)


@pytest.mark.asyncio
async def test_analyze_no_file(client, auth_headers):
    """Returns error when no file is uploaded."""
    response = await client.post("/api/v1/analysis", headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_history_empty(client, auth_headers):
    """History is empty for a new user."""
    response = await client.get("/api/v1/analysis/history", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_dashboard_empty(client, auth_headers):
    """Dashboard metrics are zeros for a fresh user."""
    response = await client.get("/api/v1/analysis/dashboard/metrics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_analyses"] == 0
    assert data["avg_risk_score"] == 0.0


@pytest.mark.asyncio
async def test_analysis_not_found(client, auth_headers):
    """Returns 404 for a non-existent analysis."""
    response = await client.get("/api/v1/analysis/99999", headers=auth_headers)
    assert response.status_code == 404
