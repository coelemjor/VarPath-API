from fastapi import FastAPI, Query, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, AsyncGenerator, Set, Any
from contextlib import asynccontextmanager
import logging
import os
import psycopg
from psycopg_pool import AsyncConnectionPool, PoolTimeout
import gzip
from pathlib import Path

from .core.config import settings
from .variant_parser import normalize_variant_for_vep
from .external_apis import get_vep_annotation_via_api
from .data_lookups import lookup_alphamissense, get_reactome_pathways

logging.basicConfig(level=settings.LOGGING_LEVEL.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("app.main")

db_pool: Optional[AsyncConnectionPool] = None
reactome_map: Dict[str, Set[str]] = {}

def load_reactome_data_on_startup(filepath: Path) -> Dict[str, Set[str]]:
    """Loads the Reactome gene-to-pathway map into memory for fast lookups."""
    mapping: Dict[str, Set[str]] = {}
    log.info(f"Loading Reactome mapping from: {filepath}")
    if not filepath.exists():
        log.error(f"Reactome mapping file not found: {filepath}. Pathway lookup will be unavailable.")
        return mapping
    try:
        open_func = gzip.open if str(filepath).endswith(".gz") else open
        with open_func(filepath, 'rt', encoding='utf-8') as f:
            for line in f:
                if line.startswith('#'): continue
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    gene_id, pathway_id = parts[0], parts[1]
                    if gene_id not in mapping: mapping[gene_id] = set()
                    mapping[gene_id].add(pathway_id)
        log.info(f"Successfully loaded {len(mapping)} gene entries from Reactome file.")
    except Exception as e:
        log.error(f"Error loading Reactome mapping file {filepath}: {e}")
    return mapping

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown events for resource handling."""
    log.info("Application startup: Initializing resources...")
    global db_pool, reactome_map
    
    db_pool = AsyncConnectionPool(conninfo=settings.DATABASE_CONNINFO, min_size=1, max_size=10, timeout=30)
    log.info("Database connection pool created.")
    
    reactome_map = load_reactome_data_on_startup(settings.REACTOME_MAP_FILE)
    
    yield
    
    log.info("Application shutdown: Releasing resources...")
    if db_pool:
        await db_pool.close()
        log.info("Database connection pool closed.")
    reactome_map.clear()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=f"Provides functional context for genetic variants based on {settings.ASSEMBLY}.",
    version="1.3.0",
    lifespan=lifespan
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

async def get_db_connection() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    """FastAPI dependency to efficiently provide a database connection per request."""
    if db_pool is None: raise HTTPException(status_code=500, detail="Database connection pool is not available.")
    try:
        async with db_pool.connection() as aconn:
            yield aconn
    except PoolTimeout: raise HTTPException(status_code=503, detail="Service temporarily unavailable.")
    except Exception: raise HTTPException(status_code=500, detail="Internal database error.")

@app.get(
    "/variant/context",
    response_model=VariantContextResponse,
    summary=f"Get Functional Context for a Variant ({settings.ASSEMBLY})",
    tags=["Variant Annotation"]
)
async def get_variant_context_query(
    db_conn: psycopg.AsyncConnection = Depends(get_db_connection),
    variant_identifier: str = Query(..., description=f"Variant identifier (e.g., 'rsID' or 'chr:pos:ref:alt') assumed {settings.ASSEMBLY}", examples=["7:140753336:A:T", "rs113488022"])
):
    """Orchestrates the asynchronous annotation process for a given variant identifier."""
    log.info(f"Processing request for variant: {variant_identifier}")

    vep_api_input_id = normalize_variant_for_vep(variant_identifier)
    if not vep_api_input_id:
        raise HTTPException(status_code=400, detail=f"Invalid or unparseable variant format: {variant_identifier}")

    vep_response = await get_vep_annotation_via_api(vep_api_input_id)
    if vep_response is None:
        raise HTTPException(status_code=502, detail="VEP annotation service failed.")
    
    vep_consequences = vep_response.get("transcript_consequences")
    if not vep_consequences:
        raise HTTPException(status_code=404, detail=f"No transcript consequences found for variant: {variant_identifier}")

    # Select the most biologically significant consequence from the VEP results.
    highest_impact_order = {"HIGH": 1, "MODERATE": 2, "LOW": 3, "MODIFIER": 4}
    vep_consequences.sort(key=lambda x: (highest_impact_order.get(x.get("impact", "MODIFIER"), 5), 0 if x.get("canonical") == 1 else 1))
    relevant_consequence = vep_consequences[0]
    
    coords_for_db = _derive_coords_from_vep(vep_response)
    
    gene_symbol = relevant_consequence.get("gene_symbol")
    ensembl_gene_id = relevant_consequence.get("gene_id")
    consequence_str = ",".join(relevant_consequence.get("consequence_terms", [])) or None
    hgvsc_raw = relevant_consequence.get("hgvsc")
    hgvsp_raw = relevant_consequence.get("hgvsp")

    am_score, am_pred = None, None
    if "missense_variant" in (consequence_str or "") and coords_for_db:
        am_result = await lookup_alphamissense(db_conn, coords_for_db, settings.ASSEMBLY)
        if am_result: am_score, am_pred = am_result

    pathways = get_reactome_pathways(
        ensembl_gene_id if ensembl_gene_id else gene_symbol,
        reactome_map
    )

    return VariantContextResponse(
        input_variant=variant_identifier,
        resolved_variant=vep_response.get("input", variant_identifier),
        gene_symbol=gene_symbol,
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

def _derive_coords_from_vep(vep_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Helper to reliably extract coordinate data from a VEP response object."""
    try:
        allele_parts = vep_response["allele_string"].split("/")
        ref = allele_parts[0]
        alt = allele_parts[1] if len(allele_parts) > 1 else "-"
        
        chrom = str(vep_response.get("seq_region_name", ""))
        db_chrom = f"chr{chrom}" if not chrom.startswith("chr") else chrom

        return {"chrom": db_chrom, "pos": int(vep_response["start"]), "ref": ref, "alt": alt}
    except (KeyError, IndexError, TypeError, ValueError) as e:
        log.error(f"Could not derive coordinates from VEP response: {e}")
        return None
