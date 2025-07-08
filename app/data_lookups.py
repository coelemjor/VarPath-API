import logging
import psycopg
from typing import Optional, List, Dict, Tuple, Set

from .core.config import settings

log = logging.getLogger("app.data_lookups")

SEVERITY_ORDER = {
    "likely_pathogenic": 3,
    "ambiguous": 2,
    "likely_benign": 1
}

async def lookup_alphamissense(
    db_conn: psycopg.AsyncConnection,
    coords: Optional[Dict],
    assembly: str
) -> Optional[Tuple[float, str]]:
    """
    Asynchronously queries the PostgreSQL database for AlphaMissense predictions.

    If multiple predictions exist for a genomic coordinate (due to multiple transcripts),
    this function returns only the most severe prediction based on SEVERITY_ORDER.
    """
    if not coords or not all(k in coords for k in ['chrom', 'pos', 'ref', 'alt']):
        return None
    try:
        chrom, pos, ref, alt = str(coords['chrom']), int(coords['pos']), str(coords['ref']), str(coords['alt'])
    except (KeyError, ValueError) as e:
        log.error(f"Invalid coordinate data for AlphaMissense lookup: {coords} - {e}")
        return None

    query = f"""
        SELECT am_pathogenicity, am_class
        FROM {settings.AM_TABLE_NAME}
        WHERE chromosome = %s AND position = %s AND ref_allele = %s AND alt_allele = %s;
        """
    params = (chrom, pos, ref, alt)
    
    try:
        async with db_conn.cursor() as acur:
            await acur.execute(query, params)
            results = await acur.fetchall()

        if not results:
            log.info(f"No AlphaMissense prediction found for {chrom}:{pos}:{ref}:{alt}")
            return None
        
        best_score, best_class, best_severity = -1.0, None, -1
        for row in results:
            current_score, current_class = row[0], row[1]
            current_severity = SEVERITY_ORDER.get(current_class, 0)
            
            if current_severity > best_severity:
                best_severity, best_class, best_score = current_severity, current_class, current_score
            elif current_severity == best_severity and current_score > best_score:
                best_score = current_score
        
        log.info(f"Selected most severe AlphaMissense prediction: Score={best_score}, Class='{best_class}'")
        return (best_score, best_class)

    except (Exception, psycopg.Error) as e:
        log.error(f"Database error during AlphaMissense lookup: {e}")
        return None

def get_reactome_pathways(
    gene_identifier: Optional[str],
    reactome_map: Dict[str, Set[str]]
) -> List[str]:
    """Performs a fast in-memory lookup for Reactome pathways using the pre-loaded map."""
    if not gene_identifier: return []
    pathway_set = reactome_map.get(gene_identifier, set())
    return sorted(list(pathway_set)) if pathway_set else []

async def lookup_gnomad_af(db_conn: psycopg.AsyncConnection, coords: Optional[Dict], assembly: str) -> Optional[float]:
    """Placeholder: To be implemented for async gnomAD allele frequency lookup."""
    return None

async def lookup_clinvar(db_conn: psycopg.AsyncConnection, coords: Optional[Dict], assembly: str) -> Optional[str]:
    """Placeholder: To be implemented for async ClinVar clinical significance lookup."""
    return None
