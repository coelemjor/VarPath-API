import httpx
import logging
from typing import Optional, List, Dict, Any

from .core.config import settings

log = logging.getLogger("app.external_apis")

async def get_vep_annotation_via_api(vep_api_input_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches variant annotations from the Ensembl VEP REST API, including AlphaMissense scores.
    """
    if not vep_api_input_id:
        return None

    endpoint = f"/vep/human/hgvs/{vep_api_input_id}"
    params = {
        "content-type": "application/json",
        "hgvs": "1",
        "AlphaMissense": "1" 
    }
    url = f"{settings.ENSEMBL_API_SERVER}{endpoint}"
    log.info(f"Querying VEP API for: {vep_api_input_id}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={"Content-Type": "application/json"}, params=params, timeout=30)
            
            log.debug(f"VEP API Raw Response Text: {response.text}")

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

async def get_reactome_pathways_via_api(ensembl_gene_id: str) -> List[str]:
    """
    Fetches associated pathways for a given Ensembl Gene ID from the Reactome API.
    """
    if not ensembl_gene_id:
        return []
    
    endpoint = f"/data/pathways/low/entity/{ensembl_gene_id}/allForms"
    url = f"{settings.REACTOME_API_SERVER}{endpoint}"
    headers = {'accept': 'application/json'}
    log.info(f"Querying Reactome API for gene: {ensembl_gene_id}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=15)

            # --- DEBUG LOGGING ---
            log.debug(f"Reactome API Raw Response Text: {response.text}")
            # --- END DEBUG LOGGING ---

            response.raise_for_status()
            data = response.json()
        
        pathway_ids = [pathway['stId'] for pathway in data if pathway and 'stId' in pathway]
        log.info(f"Found {len(pathway_ids)} pathways for {ensembl_gene_id}.")
        return sorted(pathway_ids)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            log.info(f"No pathways found in Reactome for {ensembl_gene_id} (404).")
        else:
            log.error(f"HTTP error calling Reactome API for '{ensembl_gene_id}': {e.response.status_code} - {e.response.text}")
        return []
    except httpx.RequestError as e:
        log.error(f"Network error calling Reactome API for '{ensembl_gene_id}': {e}")
        return []
