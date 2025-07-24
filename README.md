# Variant Context API

An API designed to provide meaningful biological context for human genetic variants.

Our DNA contains a vast amount of genetic information, and small changes or "variants" can sometimes have a significant impact on health and disease. This API acts as an annotation tool, taking a specific variant and returning crucial information about its potential effects, the gene it impacts, and the biological pathways it may influence.


[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Framework](https://img.shields.io/badge/Framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)

---

## Core Functionality

This API provides key annotations for a given variant identifier (GRCh38) by integrating the following services:

* **Ensembl VEP:** For primary annotation of variant consequences, affected genes, and transcripts.
* **AlphaMissense:** Pathogenicity predictions for missense variants are retrieved via the VEP plugin.
* **Reactome:** Associated biological pathways are identified via the Reactome API.

## API Usage

The API is accessed via a single `GET` endpoint.

**Live Endpoint:** `https://api.varpath.cc/variant/context`

### Query Parameter

* `variant_identifier` (string, **required**): The variant to annotate. Accepts rsID, coordinate-based, and HGVS formats.

### Example Requests

Here are several examples using `curl`. Simply replace the placeholder domain with your live API URL.

**Search By Genomic Coordinates (`chr:pos:ref:alt`)**

```bash
curl "https://api.varpath.cc/variant/context?variant_identifier=7:140753336:A:T"
```

**Example Response**

```bash
{"input_variant":"7:140753336:A:T","resolved_variant":"7:g.140753336A>T","requested_assembly":"GRCh38","gene_symbol":"BRAF","ensembl_gene_id":"ENSG00000157764","transcript_id":"ENST00000288602","consequence":"missense_variant","hgvsc":"c.1919T>A","hgvsp":"p.Val640Glu","impact":"MODERATE","alphamissense_score":0.9927,"alphamissense_prediction":"likely_pathogenic","pathways":["R-HSA-1295596","R-HSA-170968","R-HSA-170984","R-HSA-187706","R-HSA-5673000","R-HSA-5674135","R-HSA-5674499","R-HSA-5675221","R-HSA-6802946","R-HSA-6802948","R-HSA-6802952","R-HSA-6802955","R-HSA-9649948","R-HSA-9656223","R-HSA-9726840","R-HSA-9726842"]}
```
