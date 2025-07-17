# Variant Context API

A high-performance, asynchronous API to provide functional context for human genetic variants. This service orchestrates real-time calls to external bioinformatics APIs to deliver on-the-fly annotations.

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

**Live Endpoint:** `https://your-api-domain.com/variant/context` (Placeholder)
**Local Endpoint:** `http://127.0.0.1:8000/variant/context`

### Query Parameter

* `variant_identifier` (string, **required**): The variant to annotate. Accepts rsID, coordinate-based, and HGVS formats.

### Example Requests

Here are several examples using `curl`. Simply replace the placeholder domain with your live API URL.

**1. By Genomic Coordinates (`chr:pos:ref:alt`)**

```bash
curl -X GET "[https://your-api-domain.com/variant/context?variant_identifier=7:140753336:A:T](https://your-api-domain.com/variant/context?variant_identifier=7:140753336:A:T)"