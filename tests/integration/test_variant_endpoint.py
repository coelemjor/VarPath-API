# tests/integration/test_variant_endpoint.py

import pytest
import httpx
from typing import Optional, Dict, Any

from app.main import app
# Import the dependency function we want to override.
from app.main import get_db_connection

# Define a sample successful VEP API response for reuse in tests.
MOCK_VEP_SUCCESS_RESPONSE = {
    "input": "rs113488022",
    "seq_region_name": "7",
    "start": 140753336,
    "end": 140753336,
    "allele_string": "A/T",
    "strand": 1,
    "most_severe_consequence": "missense_variant",
    "transcript_consequences": [
        {
            "gene_id": "ENSG00000157764",
            "gene_symbol": "BRAF",
            "transcript_id": "ENST00000288602",
            "consequence_terms": ["missense_variant"],
            "impact": "MODERATE",
            "hgvsc": "ENST00000288602.11:c.1799T>A",
            "hgvsp": "ENSP00000288602.7:p.Val600Glu",
            "canonical": 1
        }
    ]
}

# This mock dependency will replace the real `get_db_connection`.
async def override_get_db_connection():
    yield None

# Apply the override to the FastAPI app for all tests in this file.
app.dependency_overrides[get_db_connection] = override_get_db_connection


@pytest.mark.asyncio
async def test_variant_endpoint_success_rsid(async_test_client: httpx.AsyncClient, mocker):
    """
    Tests the full success path of the /variant/context endpoint using an rsID.
    """
    mocker.patch("app.main.get_vep_annotation_via_api", return_value=MOCK_VEP_SUCCESS_RESPONSE)
    mock_am_lookup = mocker.patch("app.main.lookup_alphamissense", return_value=(0.95, "likely_pathogenic"))

    response = await async_test_client.get("/variant/context", params={"variant_identifier": "rs113488022"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["input_variant"] == "rs113488022"
    assert data["gene_symbol"] == "BRAF"
    assert data["alphamissense_score"] == 0.95
    mock_am_lookup.assert_awaited_once()

@pytest.mark.asyncio
async def test_variant_endpoint_invalid_input(async_test_client: httpx.AsyncClient, mocker):
    """
    Tests the endpoint's response to a malformed variant identifier.
    """
    # We patch the parser function to simulate it failing to parse the input.
    mocker.patch("app.main.normalize_variant_for_vep", return_value=None)
    
    response = await async_test_client.get("/variant/context", params={"variant_identifier": "this is not a variant"})
    
    assert response.status_code == 400
    assert "Invalid or unparseable variant format" in response.json()["detail"]

@pytest.mark.asyncio
async def test_variant_endpoint_vep_fails(async_test_client: httpx.AsyncClient, mocker):
    """
    Tests the endpoint's response when the external VEP API call fails.
    """
    # Mock the VEP API call to return None, simulating a network or server error.
    mocker.patch("app.main.get_vep_annotation_via_api", return_value=None)
    
    response = await async_test_client.get("/variant/context", params={"variant_identifier": "7:140753336:A:T"})
    
    # The API should return a 502 Bad Gateway error, as per the logic in main.py
    assert response.status_code == 502
    assert "VEP annotation service failed" in response.json()["detail"]
