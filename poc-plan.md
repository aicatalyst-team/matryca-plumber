# PoC Plan: matryca-plumber

## Project Overview

**Matryca Plumber** is an enterprise-grade, local-first autonomous AI daemon and headless mutation plane for Logseq OG knowledge management. It provides a FastAPI-based "Sovereign UI" web dashboard, a CLI, an MCP server, and a background maintenance daemon.

- **Source**: https://github.com/MarcoPorcellato/matryca-plumber
- **License**: Apache-2.0
- **Language**: Python 3.12+ (FastAPI/Uvicorn) + React 19 (Vite/Tailwind)
- **Version**: v2.0.0-alpha.5

## PoC Type

**web-app** — The primary deployable is a FastAPI web server (Sovereign UI) that serves both a REST API and a React frontend dashboard.

## PoC Components

| Component | Language | Build System | Entry Point | Port |
|---|---|---|---|---|
| matryca-plumber | Python + JS | pip + npm | `src.cli.ui_server:app` | 8080 (remapped from 8500) |

## Infrastructure Requirements

| Requirement | Value |
|---|---|
| needs_inference_server | false |
| needs_vector_db | false |
| needs_gpu | false |
| needs_pvc | false |
| needs_llm_api | false |
| resource_profile | small |
| deployment_model | deployment |
| listens_on_port | true (8080) |
| long_running | true |
| test_strategy | http |

## Deployment Configuration

- **Namespace**: `poc-matryca-plumber`
- **Container Port**: 8080 (remapped from original 8500)
- **Replicas**: 1
- **Image**: Internal OpenShift registry (`image-registry.openshift-image-registry.svc:5000`)

### Environment Variables

| Variable | Value | Purpose |
|---|---|---|
| `MATRYCA_UI_ALLOW_LAN` | `1` | Allow binding to 0.0.0.0 for container networking |
| `MATRYCA_UI_TOKEN` | `poc-demo-token-2026` | Required auth token when LAN mode is enabled |
| `LOGSEQ_GRAPH_PATH` | `/opt/app-root/data` | Dummy graph path (no real vault in container) |

## Test Scenarios

### Scenario 1: Health Check

- **Type**: http
- **Endpoint**: `GET /api/health`
- **Expected**: HTTP 200 with JSON response
- **Timeout**: 30s

### Scenario 2: Homepage / Dashboard

- **Type**: http
- **Endpoint**: `GET /`
- **Expected**: HTTP 200 with HTML content (React SPA)
- **Timeout**: 30s

### Scenario 3: API Preflight

- **Type**: http
- **Endpoint**: `GET /api/preflight`
- **Expected**: HTTP 200 with JSON preflight check results
- **Timeout**: 30s

### Scenario 4: OpenAPI Docs

- **Type**: http
- **Endpoint**: `GET /docs`
- **Expected**: HTTP 200 with Swagger UI HTML
- **Timeout**: 30s

## Risk Mitigation

1. **No Logseq vault**: The container runs without a real Logseq graph. API endpoints that require a configured graph path may return error responses — this is acceptable for the PoC. The health endpoint and dashboard should still be accessible.

2. **Port remapping**: The original default port (8500) is remapped to 8080 for OpenShift compatibility (non-privileged port).

3. **Auth token**: The Sovereign UI requires `MATRYCA_UI_TOKEN` when `MATRYCA_UI_ALLOW_LAN=1`. A static demo token is configured.

## Success Criteria

- Container starts and serves HTTP on port 8080
- `/api/health` returns 200
- `/` serves the React dashboard (or fallback message if frontend not built)
- At least 3 of 4 test scenarios pass
