import httpx
import logging
from typing import Optional, List, Dict, Any

from .core.config import settings

log = logging.getLogger("app.external_apis")

async def get_vep_annotation_via_api(vep_api_input_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the full variant annotation object from the Ensembl VEP REST API.
    
    This function calls the VEP 'hgvs' endpoint, which can resolve various
    identifiers (rsID, HGVS strings) into a single, comprehensive annotation object.
    """
    if not vep_api_input_id:
        return None

    endpoint = f"/vep/human/hgvs/{vep_api_input_id}"
    params = {
        "content-type": "application/json",
        "fields": "input,seq_region_name,start,end,strand,allele_string,most_severe_consequence,transcript_consequences(gene_id,gene_symbol,transcript_id,biotype,consequence_terms,impact,hgvsc,hgvsp,canonical)",
        "hgvs": "1"
    }
    url = f"{settings.ENSEMBL_API_SERVER}{endpoint}"
    log.info(f"Querying VEP API for: {vep_api_input_id}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={"Content-Type": "application/json"}, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

        if data and isinstance(data, list) and len(data) > 0:
            log.info(f"Successfully fetched VEP annotation for {vep_api_input_id}.")
            return data[0]
        
        log.warning(f"VEP API returned an empty list for {vep_api_input_id}")
        return None

    except httpx.HTTPStatusError as e:
        log.error(f"HTTP error calling VEP API for '{vep_api_input_id}': {e.response.status_code} - {e.response.text}")
        return None
    except httpx.RequestError as e:
        log.error(f"Network error calling VEP API for '{vep_api_input_id}': {e}")
        return None
    except ValueError as json_err:
        log.error(f"Failed to decode JSON from VEP API for '{vep_api_input_id}': {json_err}")
        return None
