# Deploying Matryca Plumber on OpenShift: Bringing Local-First AI Knowledge Management to the Enterprise

When developers build AI-powered tools that interact with personal knowledge bases, they face a fundamental tension: how do you keep data local and safe while making the tooling accessible across enterprise environments? Matryca Plumber, an open-source project by Marco Porcellato, addresses this challenge as an autonomous AI daemon and MCP server for Logseq knowledge graphs. We set out to prove that this local-first application can run on OpenShift, bringing its Sovereign UI dashboard and API infrastructure into a containerized, enterprise-ready deployment.

## What Is Matryca Plumber?

Matryca Plumber is a Python-based application that bridges AI agents and Logseq OG knowledge vaults. It provides four primary interfaces:

- **CLI tools** for structured read/write operations on Logseq's block tree
- **MCP server** using FastMCP stdio protocol, enabling tool connectivity with AI agents like Claude and Cursor
- **Background daemon** for autonomous maintenance tasks such as semantic summaries, link healing, and entity consolidation
- **Sovereign UI** — a FastAPI web dashboard with a React 19 frontend for configuration, monitoring, and control

The project emphasizes OCC (optimistic concurrency control) safety: if you edit a page while an AI agent is thinking, the agent's commit aborts rather than overwriting your changes. This write-safety guarantee is central to the project's value proposition.

## Why OpenShift?

While Matryca Plumber is designed as a local-first tool, there are compelling reasons to run it on a container platform:

**Team-accessible dashboards.** The Sovereign UI provides real-time telemetry, daemon control, and graph analytics. Running it on OpenShift makes this dashboard accessible to distributed teams without requiring everyone to install the tool locally.

**MCP server availability.** The MCP protocol is a growing standard for AI agent tool connectivity, a key component of Red Hat's agentic AI strategy. Deploying an MCP-capable service on OpenShift validates how these tools integrate with enterprise infrastructure.

**Reproducible environments.** Containerizing the application with UBI images ensures consistent behavior across development, staging, and production — regardless of the host operating system.

## The Containerization Challenge

Matryca Plumber had no existing Dockerfile. The application combines a Python 3.12+ backend with a React 19 frontend built using Vite, requiring a multi-stage container build.

### Stage 1: Frontend Build

The first stage uses `registry.access.redhat.com/ubi9/nodejs-22` to build the React dashboard. One detail that required attention: UBI Node.js images default to a non-root user (UID 1001), and the working directory must be set to `/opt/app-root/src` (the default) rather than a subdirectory to avoid permission errors during `npm ci`.

```dockerfile
FROM registry.access.redhat.com/ubi9/nodejs-22 AS frontend-builder
WORKDIR /opt/app-root/src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build
```

### Stage 2: Python Runtime

The second stage uses `registry.access.redhat.com/ubi9/python-312` for the application runtime. A key architectural detail: the Sovereign UI server resolves the frontend assets path using `Path(__file__).resolve().parents[2]` from `src/cli/ui_server.py`, meaning the built frontend must be placed at `frontend/dist/` relative to the Python source root.

```dockerfile
FROM registry.access.redhat.com/ubi9/python-312
WORKDIR /opt/app-root/src
COPY pyproject.toml MANIFEST.in ./
COPY src/ ./src/
COPY --from=frontend-builder /opt/app-root/src/dist/ ./frontend/dist/
RUN pip install --no-cache-dir .
```

The port was remapped from 8500 (the Sovereign UI default) to 8080 for OpenShift compatibility, and `MATRYCA_UI_ALLOW_LAN=1` was set to enable binding to `0.0.0.0` inside the container.

## Building and Deploying

We used OpenShift's binary build strategy, which uploads the local source directory to the cluster and builds the image on-cluster using the internal registry. This approach eliminates the need for external registry credentials during the build phase.

```bash
oc new-build --name=matryca-plumber --binary --strategy=docker
oc start-build matryca-plumber --from-dir=. --follow --wait
```

The build completed in about 5 minutes, producing an image in the internal registry. The Kubernetes deployment consisted of a single Deployment and ClusterIP Service, with readiness and liveness probes targeting `/api/health`.

## Validation Results

All four test scenarios passed:

| Test | Result | Details |
|---|---|---|
| Health Check (`/api/health`) | PASS | Returns `{"status": "ok"}` in 20ms |
| Homepage Dashboard (`/`) | PASS | Serves the React SPA (832 bytes HTML shell) |
| API Preflight (`/api/preflight`) | PASS | Returns preflight check results with auth token |
| API Config (`/api/config`) | PASS | Full configuration object with 20+ settings |

The Sovereign UI's authentication model uses a custom `x-matryca-token` header rather than standard Bearer tokens, which is a deliberate design choice for the local-first security model. The health endpoint is exempt from authentication, making it suitable for Kubernetes health probes.

## What We Learned

**UBI image permissions matter.** The initial build failed because we used a subdirectory as WORKDIR in the Node.js builder stage. UBI images have specific directory permissions that differ from community images — working within the default `/opt/app-root/src` path is the simplest approach.

**Local-first applications can deploy on platforms.** Despite being designed for single-user, local operation, Matryca Plumber's clean FastAPI architecture deployed without code changes. The only adaptations were environment variables (`MATRYCA_UI_ALLOW_LAN`, `MATRYCA_UI_TOKEN`) that the project already supported.

**MCP on OpenShift has potential.** This PoC validates the deployment pattern for MCP-capable services on OpenShift. As MCP adoption grows in the AI tooling ecosystem, having proven deployment patterns on enterprise platforms becomes increasingly valuable.

## Next Steps

For production use, the deployment would benefit from:

- **Persistent volume** for the Logseq graph directory, enabling actual graph operations
- **OpenShift Route** for external access to the Sovereign UI dashboard
- **Secret management** for the authentication token via Kubernetes Secrets
- **Integration testing** with MCP-compatible clients connecting through the cluster network

The full PoC artifacts — Dockerfile, Kubernetes manifests, test scripts, and detailed report — are available on the [autopoc-artifacts branch](https://github.com/aicatalyst-team/matryca-plumber/tree/autopoc-artifacts).

---

*This PoC was executed using the AutoPoC pipeline on OpenShift, validating containerization and deployment of the [Matryca Plumber](https://github.com/MarcoPorcellato/matryca-plumber) project (Apache-2.0 license) by Marco Porcellato.*
