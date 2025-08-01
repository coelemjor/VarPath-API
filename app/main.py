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
    version="2.2.0",
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

def _find_most_severe_alphamissense(vep_consequences: List[Dict[str, Any]]) -> Optional[Tuple[float, str]]:
    """
    Iterates through all transcript consequences to find the most severe AlphaMissense prediction.
    """
    SEVERITY_ORDER = { "likely_pathogenic": 3, "ambiguous": 2, "likely_benign": 1 }
    
    best_score = -1.0
    best_class = None
    best_severity = -1
    found_am = False

    for consequence in vep_consequences:
        # Only consider missense variants for AlphaMissense scores.
        if "missense_variant" not in consequence.get("consequence_terms", []):
            continue

        am_data = consequence.get("alphamissense")
        if am_data and isinstance(am_data, dict):
            try:
                current_score = float(am_data.get("am_pathogenicity"))
                current_class = am_data.get("am_class")
                current_severity = SEVERITY_ORDER.get(current_class, 0)
                found_am = True

                # Compare with the best prediction found so far.
                if current_severity > best_severity:
                    best_severity = current_severity
                    best_class = current_class
                    best_score = current_score
                elif current_severity == best_severity and current_score > best_score:
                    best_score = current_score

            except (ValueError, TypeError) as e:
                log.error(f"Could not parse AlphaMissense data from VEP: '{am_data}' - {e}")
    
    if found_am:
        return (best_score, best_class)
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

    am_score, am_pred = None, None
    am_result = _find_most_severe_alphamissense(vep_consequences)
    if am_result:
        am_score, am_pred = am_result

    highest_impact_order = {"HIGH": 1, "MODERATE": 2, "LOW": 3, "MODIFIER": 4}
    vep_consequences.sort(key=lambda x: (highest_impact_order.get(x.get("impact", "MODIFIER"), 5), 0 if x.get("canonical") == 1 else 1))
    relevant_consequence = vep_consequences[0]
    
    ensembl_gene_id = relevant_consequence.get("gene_id")
    pathways = await get_reactome_pathways_via_api(ensembl_gene_id) if ensembl_gene_id else []
    
    hgvsc_raw = relevant_consequence.get("hgvsc")
    hgvsp_raw = relevant_consequence.get("hgvsp")

    return VariantContextResponse(
        input_variant=variant_identifier,
        resolved_variant=vep_response.get("input", variant_identifier),
        gene_symbol=relevant_consequence.get("gene_symbol"),
        ensembl_gene_id=ensembl_gene_id,
        transcript_id=relevant_consequence.get("transcript_id"),
        consequence=",".join(relevant_consequence.get("consequence_terms", [])),
        hgvsc=hgvsc_raw.split(':')[-1] if hgvsc_raw and ':' in hgvsc_raw else hgvsc_raw,
        hgvsp=hgvsp_raw.split(':')[-1] if hgvsp_raw and ':' in hgvsp_raw else hgvsp_raw,
        impact=relevant_consequence.get("impact"),
        alphamissense_score=am_score,
        alphamissense_prediction=am_pred,
        pathways=pathways
    )
