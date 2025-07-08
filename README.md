# Variant Context API

A high-performance, asynchronous API built with FastAPI to provide functional context and pathogenicity predictions for human genetic variants. This service orchestrates real-time calls to external bioinformatics APIs (Ensembl VEP, Reactome) to deliver a comprehensive, on-the-fly annotation for a given variant.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Framework](https://img.shields.io/badge/Framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)

---

## Key Features

* **Asynchronous Processing:** Built with `async/await` using FastAPI and `httpx` for high-throughput, non-blocking performance when calling external APIs.
* **Comprehensive VEP Annotation:** Leverages the Ensembl VEP REST API for real-time annotation of variant consequences, affected genes, and transcripts (GRCh38).
* **Integrated Pathogenicity Prediction:** Configured to use the VEP `AlphaMissense` plugin, providing state-of-the-art missense variant pathogenicity scores directly.
* **Live Pathway Analysis:** Identifies associated biological pathways by querying the Reactome API in real-time.
* **Streamlined & Deployable:** A lightweight, stateless application with minimal dependencies, designed for easy deployment on modern PaaS platforms (e.g., Render, Fly.io, Heroku).
* **Tested:** Includes a comprehensive suite of unit and integration tests using `pytest`.

## Technology Stack

* **Backend Framework:** FastAPI
* **HTTP Client:** HTTPX (for async requests to external APIs)
* **Configuration:** Pydantic Settings

## Setup and Local Execution

### Prerequisites

* Python 3.11+
* Git
