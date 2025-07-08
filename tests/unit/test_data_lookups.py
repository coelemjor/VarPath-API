# tests/unit/test_data_lookups.py

import pytest
import psycopg
from app.data_lookups import lookup_alphamissense
from unittest.mock import MagicMock, AsyncMock # Import for explicit mocking

@pytest.mark.asyncio
async def test_lookup_alphamissense_most_severe(mocker):
    """
    Tests the logic for selecting the most severe prediction when multiple
    results are returned from the database.
    """
    # Create an async-aware mock for the cursor itself.
    mock_cursor = AsyncMock()
    # Configure the awaitable `fetchall` to resolve with our mock data.
    mock_cursor.fetchall.return_value = [
        (0.1, 'likely_benign'),
        (0.95, 'likely_pathogenic'),
        (0.6, 'ambiguous'),
        (0.9, 'likely_pathogenic')
    ]

    # Create a mock for the async context manager that `conn.cursor()` returns.
    mock_async_context_manager = AsyncMock()
    # The `__aenter__` method of the context manager should return the cursor mock.
    mock_async_context_manager.__aenter__.return_value = mock_cursor

    # Create the final mock for the database connection.
    mock_db_conn = AsyncMock()
    # Replace the default async `cursor` attribute with a synchronous MagicMock
    # that returns our pre-configured async context manager. This correctly
    # simulates the behavior of psycopg3's async connection.
    mock_db_conn.cursor = MagicMock(return_value=mock_async_context_manager)

    coords = {"chrom": "chr1", "pos": 123, "ref": "A", "alt": "T"}
    
    result = await lookup_alphamissense(mock_db_conn, coords, "GRCh38")

    assert result == (0.95, 'likely_pathogenic')

@pytest.mark.asyncio
async def test_lookup_alphamissense_no_result(mocker):
    """
    Tests the case where the database query returns no results.
    """
    mock_cursor = AsyncMock()
    mock_cursor.fetchall.return_value = [] # Mock returns an empty list.

    mock_async_context_manager = AsyncMock()
    mock_async_context_manager.__aenter__.return_value = mock_cursor

    mock_db_conn = AsyncMock()
    mock_db_conn.cursor = MagicMock(return_value=mock_async_context_manager)
    
    coords = {"chrom": "chr1", "pos": 123, "ref": "A", "alt": "T"}
    result = await lookup_alphamissense(mock_db_conn, coords, "GRCh38")
    
    assert result is None

@pytest.mark.asyncio
async def test_lookup_alphamissense_db_error(mocker):
    """
    Tests that the function handles a database error gracefully.
    """
    mock_cursor = AsyncMock()
    # Configure the mock `execute` method to raise a psycopg Error.
    mock_cursor.execute.side_effect = psycopg.Error("Simulated DB connection error")

    mock_async_context_manager = AsyncMock()
    mock_async_context_manager.__aenter__.return_value = mock_cursor
    
    mock_db_conn = AsyncMock()
    mock_db_conn.cursor = MagicMock(return_value=mock_async_context_manager)
    
    coords = {"chrom": "chr1", "pos": 123, "ref": "A", "alt": "T"}
    result = await lookup_alphamissense(mock_db_conn, coords, "GRCh38")
    
    assert result is None
