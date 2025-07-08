import psycopg
import gzip
import logging
import time
import sys
import argparse
from pathlib import Path

# Allows this script to import from the 'app' package.
sys.path.append(str(Path(__file__).resolve().parent))

from app.core.config import settings

logging.basicConfig(level=settings.LOGGING_LEVEL.upper(), format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("am_loader")

def drop_target_table(cur: psycopg.Cursor):
    """Drops the target table for a clean reload."""
    drop_sql = f"DROP TABLE IF EXISTS {settings.AM_TABLE_NAME};"
    log.warning(f"Dropping table '{settings.AM_TABLE_NAME}' for clean reload...")
    cur.execute(drop_sql)
    log.info("Table dropped successfully.")

def create_target_table(cur: psycopg.Cursor):
    """Ensures the target database table exists with the correct schema."""
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {settings.AM_TABLE_NAME} (
        chromosome TEXT NOT NULL,
        position BIGINT NOT NULL,
        ref_allele TEXT NOT NULL,
        alt_allele TEXT NOT NULL,
        genome TEXT,
        uniprot_id TEXT,
        transcript_id TEXT NOT NULL,
        protein_variant TEXT,
        am_pathogenicity FLOAT NOT NULL,
        am_class TEXT NOT NULL,
        PRIMARY KEY (chromosome, position, ref_allele, alt_allele, transcript_id)
    );
    """
    log.info(f"Ensuring table '{settings.AM_TABLE_NAME}' exists...")
    cur.execute(create_table_sql)

def load_data_direct_copy(cur: psycopg.Cursor, filepath: Path):
    """Performs a bulk load of the data file using PostgreSQL's COPY command."""
    if not filepath.exists():
        log.critical(f"ERROR: Source data file not found at '{filepath}'.")
        exit(1)
        
    columns = ('chromosome', 'position', 'ref_allele', 'alt_allele', 'genome', 'uniprot_id', 'transcript_id', 'protein_variant', 'am_pathogenicity', 'am_class')
    copy_sql = f"COPY {settings.AM_TABLE_NAME} ({','.join(columns)}) FROM STDIN (FORMAT CSV, DELIMITER '\t', HEADER FALSE, QUOTE E'\b')"

    log.info(f"Starting bulk load from {filepath} into '{settings.AM_TABLE_NAME}'...")
    start_time = time.time()
    rows_processed = 0
    with gzip.open(filepath, 'rt', encoding='utf-8') as f_in:
        with cur.copy(copy_sql) as copy:
            for line in f_in:
                if line.startswith('#'): continue
                if len(line.strip().split('\t')) != len(columns):
                    log.warning(f"Skipping malformed line: {line.strip()}")
                    continue
                copy.write(line.encode('utf-8'))
                rows_processed += 1
    end_time = time.time()
    log.info(f"Successfully copied {rows_processed:,} rows in {end_time - start_time:.2f} seconds.")

def create_indexes(cur: psycopg.Cursor):
    """Creates indexes on the target table after data loading for query performance."""
    index_sql_coords = f"CREATE INDEX IF NOT EXISTS idx_am_coords ON {settings.AM_TABLE_NAME} (chromosome, position, ref_allele, alt_allele);"
    index_sql_transcript = f"CREATE INDEX IF NOT EXISTS idx_am_transcript ON {settings.AM_TABLE_NAME} (transcript_id);"
    
    log.info(f"Creating coordinate index on '{settings.AM_TABLE_NAME}'...")
    start_time = time.time()
    cur.execute(index_sql_coords)
    log.info(f"Coordinate index creation took {time.time() - start_time:.2f} seconds.")

    log.info(f"Creating transcript index on '{settings.AM_TABLE_NAME}'...")
    start_time = time.time()
    cur.execute(index_sql_transcript)
    log.info(f"Transcript index creation took {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load AlphaMissense data into PostgreSQL.")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Drop the existing table before loading data for a clean import."
    )
    args = parser.parse_args()

    try:
        log.info(f"Connecting to database '{settings.DB_NAME}'...")
        with psycopg.connect(settings.DATABASE_CONNINFO) as conn:
            log.info("Connection successful.")
            
            # Wrap the entire sequence of operations in a single transaction.
            # If any step fails, all previous steps in this block will be rolled back.
            with conn.transaction():
                log.info("Beginning database transaction...")
                with conn.cursor() as cur:
                    if args.clean:
                        drop_target_table(cur)
                    
                    create_target_table(cur)
                    load_data_direct_copy(cur, settings.ALPHAMISSENSE_FILE)
                    create_indexes(cur)
            
            log.info("Transaction committed. Data loading and indexing process finished successfully.")

    except psycopg.OperationalError as e:
        log.error(f"Database connection failed: {e}")
        log.error("Please ensure PostgreSQL is running and .env variables are correct.")
    except Exception as e:
        log.error(f"An unexpected error occurred during the loading process: {e}")

    log.info("Script Finished.")
