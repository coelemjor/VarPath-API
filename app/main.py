from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Tuple

import logging

from .core.config import settings
from .variant_parser import normalize_variant_for_vep
from .external_apis import get_vep_annotation_via_api, get_reactome_pathways_via_api

logging.basicConfig(level=settings.LOGGING_LEVEL.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("app.main")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=f"Provides functional context for genetic variants based on {settings.ASSEMBLY}.",
    version="2.2.0", # Version bump for parser fixes
)

class VariantContextResponse(BaseModel):
    """Defines the structure and validation for the API's JSON response."""
    input_variant: str
    resolved_variant: str
    requested_assembly: str = Field(settings.ASSEMBLY, description="Genome assembly used for annotation")
    gene_symbol: Optional[str] = None
    ensembl_gene_id: Optional[str] = None
    transcript_id: Optional[str] = None
    consequence: Optional[str] = None
    hgvsc: Optional[str] = None
    hgvsp: Optional[str] = None
    impact: Optional[str] = None
    alphamissense_score: Optional[float] = Field(None, description="AlphaMissense pathogenicity score")
    alphamissense_prediction: Optional[str] = Field(None, description="AlphaMissense classification")
    pathways: List[str] = Field([], description="List of associated Reactome pathway IDs")

def _parse_alphamissense_from_vep(vep_consequence: Dict[str, Any]) -> Optional[Tuple[float, str]]:
    """
    Helper to parse AlphaMissense data from the VEP transcript consequence object.
    The VEP AlphaMissense plugin adds an 'alphamissense' key directly to the consequence.
    """
    # Look for the 'alphamissense' key directly in the consequence object.
    am_data = vep_consequence.get("alphamissense")

    # Check if the data exists and is a dictionary.
    if am_data and isinstance(am_data, dict):
        try:
            # Extract the score and class from the dictionary.
            score = float(am_data.get("am_pathogenicity"))
            prediction = am_data.get("am_class")
            
            # Ensure both values were found before returning.
            if score is not None and prediction is not None:
                return (score, prediction)
        except (ValueError, TypeError) as e:
            # Log an error if the values have an unexpected type.
            log.error(f"Could not parse AlphaMissense data from VEP: '{am_data}' - {e}")
            
    return None

@app.get(
    "/variant/context",
    response_model=VariantContextResponse,
    summary=f"Get Functional Context for a Variant ({settings.ASSEMBLY})",
    tags=["Variant Annotation"]
)
async def get_variant_context_query(
    variant_identifier: str = Query(..., description=f"Variant identifier assumed {settings.ASSEMBLY}", examples=["7:140753336:A:T", "rs113488022"])
):
    """Orchestrates the asynchronous annotation process for a given variant identifier."""
    log.info(f"Processing request for variant: {variant_identifier}")

    vep_api_input_id = normalize_variant_for_vep(variant_identifier)
    if not vep_api_input_id:
        raise HTTPException(status_code=400, detail=f"Invalid or unparseable variant format: {variant_identifier}")

    vep_response = await get_vep_annotation_via_api(vep_api_input_id)
    if not vep_response:
        raise HTTPException(status_code=404, detail=f"Could not find annotation for variant: {variant_identifier}")

    vep_consequences = vep_response.get("transcript_consequences")
    if not vep_consequences:
        raise HTTPException(status_code=404, detail=f"No transcript consequences found for variant: {variant_identifier}")

    highest_impact_order = {"HIGH": 1, "MODERATE": 2, "LOW": 3, "MODIFIER": 4}
    vep_consequences.sort(key=lambda x: (highest_impact_order.get(x.get("impact", "MODIFIER"), 5), 0 if x.get("canonical") == 1 else 1))
    relevant_consequence = vep_consequences[0]
    
    ensembl_gene_id = relevant_consequence.get("gene_id")
    consequence_str = ",".join(relevant_consequence.get("consequence_terms", [])) or None
    
    am_score, am_pred = None, None
    if "missense_variant" in (consequence_str or ""):
        # The logic to call the parser is now implemented correctly.
        am_result = _parse_alphamissense_from_vep(relevant_consequence)
        if am_result:
            am_score, am_pred = am_result

    pathways = await get_reactome_pathways_via_api(ensembl_gene_id) if ensembl_gene_id else []
    
    hgvsc_raw = relevant_consequence.get("hgvsc")
    hgvsp_raw = relevant_consequence.get("hgvsp")

    return VariantContextResponse(
        input_variant=variant_identifier,
        resolved_variant=vep_response.get("input", variant_identifier),
        gene_symbol=relevant_consequence.get("gene_symbol"),
        ensembl_gene_id=ensembl_gene_id,
        transcript_id=relevant_consequence.get("transcript_id"),
        consequence=consequence_str,
        hgvsc=hgvsc_raw.split(':')[-1] if hgvsc_raw and ':' in hgvsc_raw else hgvsc_raw,
        hgvsp=hgvsp_raw.split(':')[-1] if hgvsp_raw and ':' in hgvsp_raw else hgvsp_raw,
        impact=relevant_consequence.get("impact"),
        alphamissense_score=am_score,
        alphamissense_prediction=am_pred,
        pathways=pathways
    )
