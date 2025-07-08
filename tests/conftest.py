# tests/conftest.py

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport # <<< IMPORT ASGITransport
import psycopg
from psycopg_pool import AsyncConnectionPool
from typing import AsyncGenerator

# Import the main FastAPI app from your application.
from app.main import app

@pytest.fixture(scope="session")
def test_client() -> TestClient:
    """Creates a synchronous test client for making requests to the FastAPI app."""
    client = TestClient(app)
    return client

@pytest.fixture(scope="session")
async def async_test_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Creates an asynchronous test client for testing an ASGI application like FastAPI.
    """
    # Use ASGITransport to wrap the FastAPI app for httpx.
    transport = ASGITransport(app=app)
    # The client is initialized with the transport and a base_url.
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
