import logging
from typing import Optional

log = logging.getLogger("app.variant_parser")

def normalize_variant_for_vep(id_str: str) -> Optional[str]:
    """
    Validates and normalizes a user-provided variant identifier into a format
    suitable for the Ensembl VEP API. It leaves coordinate extraction to VEP.
    """
    log.info(f"Normalizing identifier for VEP: {id_str}")
    cleaned_id = id_str.strip()

    if cleaned_id.lower().startswith("rs") and cleaned_id[2:].isdigit():
        return cleaned_id

    try:
        if cleaned_id.count(':') == 3: # Handles CHR:POS:REF:ALT
            chrom, pos_str, ref, alt = [part.strip() for part in cleaned_id.split(':')]
            if not pos_str.isdigit(): raise ValueError("Position is not a number.")
            chrom_norm = chrom.replace('chr', '', 1).replace('Chr', '', 1)
            return f"{chrom_norm}:g.{pos_str}{ref.upper()}>{alt.upper()}"
        
        if '>' in cleaned_id and cleaned_id.count(':') == 1: # Handles CHR:POSREF>ALT
            chrom_pos, alt = [part.strip() for part in cleaned_id.split('>', 1)]
            chrom_val, pos_ref = chrom_pos.split(':', 1)
            pos_str = "".join(filter(str.isdigit, pos_ref))
            ref = "".join(filter(str.isalpha, pos_ref)).upper()
            if not pos_str or not ref: raise ValueError("Could not parse POSREF.")
            chrom_norm = chrom_val.replace('chr', '', 1).replace('Chr', '', 1)
            return f"{chrom_norm}:g.{pos_str}{ref}>{alt.upper()}"

    except (ValueError, IndexError):
        log.warning(f"Could not parse '{cleaned_id}' as a simple coordinate format.")
    
    if ':' in cleaned_id and any(prefix in cleaned_id for prefix in ['g.', 'c.', 'p.', 'n.']):
        return cleaned_id

    log.error(f"Unrecognized variant format: {cleaned_id}")
    return None
