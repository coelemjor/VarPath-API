# --- tests/unit/test_external_apis.py ---

import pytest
import httpx
import respx # The respx library is used to mock HTTP requests
from app.external_apis import get_vep_annotation_via_api
from app.core.config import settings

# `@pytest.mark.asyncio` is from the pytest-asyncio plugin.
# It tells pytest to run this test function using an asyncio event loop,
# which is necessary for testing `async def` functions.
@pytest.mark.asyncio
# `respx_mock` is a fixture provided by the respx library.
# Including it as an argument tells pytest to activate the mocking for this test.
async def test_get_vep_annotation_successful(respx_mock):
    """
    Tests a successful VEP API call (200 OK with valid data).
    """
    # Define a mock JSON response that mimics a real Ensembl VEP API response.
    mock_vep_response = [{
        "input": "rs113488022",
        "transcript_consequences": [{"gene_id": "ENSG00000157764", "gene_symbol": "BRAF"}]
    }]
    
    # Configure the mock route.
    # This tells `respx` to intercept any GET request to this URL pattern
    # and return our predefined mock response instead of making a real network call.
    url = f"{settings.ENSEMBL_API_SERVER}/vep/human/hgvs/rs113488022"
    respx_mock.get(url).mock(return_value=httpx.Response(200, json=mock_vep_response))

    # Call the function we are testing. It will now hit our mock instead of the real API.
    result = await get_vep_annotation_via_api("rs113488022")

    # Assert that the result matches the expected output.
    assert result is not None
    assert result == mock_vep_response[0]

@pytest.mark.asyncio
async def test_get_vep_annotation_not_found(respx_mock):
    """
    Tests the case where the VEP API returns 200 OK but an empty list (variant not found).
    """
    mock_vep_response = []
    url = f"{settings.ENSEMBL_API_SERVER}/vep/human/hgvs/not_a_variant"
    respx_mock.get(url).mock(return_value=httpx.Response(200, json=mock_vep_response))

    result = await get_vep_annotation_via_api("not_a_variant")
    
    # The function should return None when the API result is an empty list.
    assert result is None

@pytest.mark.asyncio
async def test_get_vep_annotation_bad_request(respx_mock):
    """
    Tests the case where the VEP API returns a 400 Bad Request error.
    """
    url = f"{settings.ENSEMBL_API_SERVER}/vep/human/hgvs/bad_input"
    respx_mock.get(url).mock(return_value=httpx.Response(400, json={"error": "Bad request"}))

    result = await get_vep_annotation_via_api("bad_input")
    
    # The function should catch the HTTPStatusError and return None.
    assert result is None