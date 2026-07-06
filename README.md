# 🎬 Movie Recommender — CI/CD Pipeline

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=phoenix8875_movie_recomendation&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=phoenix8875_movie_recomendation)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=phoenix8875_movie_recomendation&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=phoenix8875_movie_recomendation)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=phoenix8875_movie_recomendation&metric=bugs)](https://sonarcloud.io/summary/new_code?id=phoenix8875_movie_recomendation)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=phoenix8875_movie_recomendation&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=phoenix8875_movie_recomendation)

A 3-tier movie recommendation app — **Nginx → FastAPI → PostgreSQL** — that
started as a hand-deployed Docker Compose project and evolved into a fully
automated **GitOps CI/CD pipeline** on Kubernetes.

This README explains **how a code change turns into a running deployment,
untouched by hand** — every pipeline stage, why it exists, and how it hands
off to the next. For the original container-networking deep-dive (nginx
reverse proxy, Docker DNS, request flow), see
[`docs/architecture_notes.md`](docs/architecture_notes.md).

---

## 🚀 The Pipeline, End to End

```
 ┌────────────┐
 │  Developer │
 │  git push  │
 └─────┬──────┘
       │
       ▼
╔══════════════════════════════ CI  —  App Repo  (GitHub Actions) ═══════════════════════════╗
║                                                                                              ║
║   ①LINT        ②TEST         ③SAST          ④BUILD          ⑤SCAN          ⑥DAST          ║
║   ruff    ──►  pytest   ──►  SonarCloud ──►  Docker    ──►  Trivy     ──►  OWASP ZAP        ║
║   style       unit tests    quality gate    build+push     image scan     live app scan     ║
║                                                             + push SARIF                     ║
║                                                             to Security tab                  ║
║                                                                                              ║
╚═══════════════════════════════════════════════════╤════════════════════════════════════════╝
                                                     │
                                          ⑦ commit new image tag
                                                     │
                                                     ▼
╔══════════════════════ CD (config)  —  Helm Repo  (Git = source of truth) ══════════════════╗
║                                                                                              ║
║           values.yaml  { backend.image.tag: "<new-sha>", frontend.image.tag: "<new-sha>" }  ║
║                                                                                              ║
╚═══════════════════════════════════════════════════╤════════════════════════════════════════╝
                                                     │
                                     ⑧ Argo CD detects the commit
                                                     │
                                                     ▼
╔══════════════════════ CD (deploy)  —  Kubernetes Cluster  (Argo CD) ═══════════════════════╗
║                                                                                              ║
║   Argo CD syncs  ──►  Helm renders chart  ──►  kubectl apply  ──►  pods roll to new image   ║
║   (auto + self-heal)                                                     │                  ║
║                                                                            ▼                 ║
║                                                              ⑨ App live at :30080            ║
║                                                              Prometheus + Grafana watching    ║
╚══════════════════════════════════════════════════════════════════════════════════════════════╝
```

**Why "CI/CD/CD"?** Continuous **Integration** (build & verify), continuous
**Delivery** (the image is always ready to deploy), and continuous
**Deployment** (Argo CD ships it with no human clicking "deploy"). All three
happen automatically on every push to `main`.

---

## 🔗 Two Repos, One Pipeline

The pipeline deliberately spans **two repositories** — this is the standard
"app repo vs. config repo" GitOps split:

```
┌─────────────────────────────┐         commits          ┌──────────────────────────────┐
│   movie-recomendation        │   the new image tag      │  helm-chart-based-deployment  │
│   (this repo — the CODE)     │ ────────────────────────► │  (the DEPLOY CONFIG)          │
│                               │                           │                                │
│   • Dockerfiles               │                           │   • Helm chart                │
│   • FastAPI + Nginx source    │                           │   • values.yaml                │
│   • GitHub Actions workflow   │                           │   • SealedSecrets              │
└─────────────────────────────┘                           └───────────────┬────────────────┘
                                                                            │
                                                                  watched by Argo CD
                                                                            │
                                                                            ▼
                                                                  Kubernetes Cluster
```

**Why split them?** CI (build/test/scan) and CD (what's deployed) change for
different reasons and at different rates. Keeping them separate means Argo CD
only ever needs to watch *one* thing — the Helm repo — and that repo is a
complete, accurate record of exactly what's running in the cluster at any
moment. A `git log` on the Helm repo **is** the deployment history.

---

## 📋 Every CI Stage, Explained

Each stage runs on a fresh GitHub-hosted VM and must pass before the next one starts.

| # | Stage | Tool | What it checks | If it fails |
|:-:|:------|:-----|:----------------|:------------|
| ① | **Lint** | `ruff` | Python style and common errors | Reports only — doesn't block (yet) |
| ② | **Unit Tests** | `pytest` | Password hashing, schema validation — pure logic, no DB needed | **Pipeline stops** — nothing gets built |
| ③ | **SAST** | SonarCloud | Reads the *source code* for bugs, code smells, security hotspots | **Pipeline stops** if the Quality Gate is red |
| ④ | **Build & Push** | Docker Buildx | Builds backend + frontend images, tags each with the **git commit SHA** | Build errors stop the pipeline |
| ⑤ | **Image Scan** | Trivy | Scans the *built image's* OS/library packages for known CVEs → SARIF → Security tab | Reports only (HIGH/CRITICAL surfaced, doesn't block) |
| ⑥ | **DAST** | OWASP ZAP | Attacks the *live running app* over HTTP — missing security headers, XSS surface, etc. | Reports only |
| ⑦ | **Deploy Trigger** | `yq` + `git push` | Rewrites the image tag in the Helm repo's `values.yaml` and commits | This commit *is* the deploy signal |

### Why three different security tools?

Each one inspects the application at a **different layer** — none of them
overlap, which is why all three earn a place in the pipeline:

```
   SAST (SonarCloud)          Image Scan (Trivy)           DAST (OWASP ZAP)
   ──────────────────         ───────────────────          ──────────────────
   reads SOURCE CODE          reads the BUILT IMAGE         attacks the LIVE APP
   "is this code written      "does this image contain     "is the running app
    insecurely?"                known-vulnerable libs?"       exploitable right now?"
```

---

## 🔐 Quality & Security at a Glance

The badges at the top of this README are **live** — they reflect the current
state of the `main` branch on SonarCloud, updated on every pipeline run:

- **Quality Gate** — pass/fail verdict combining bugs, vulnerabilities, code
  smells, and coverage against SonarCloud's default rule set. The pipeline's
  SAST stage **fails the build** if this goes red.
- **Vulnerabilities / Bugs / Code Smells** — live counts, click through to the
  full SonarCloud dashboard for line-by-line detail.

Trivy's findings live in this repo's **Security → Code scanning** tab (not a
badge, since GitHub doesn't expose one) — every HIGH/CRITICAL CVE found in the
backend image, with a downloadable report attached to each pipeline run.

---

## 📦 From Commit to Cluster: the GitOps Handoff

This is the step that makes the pipeline *continuous deployment*, not just
continuous integration:

```
  CI (this repo)                                    Argo CD (in-cluster)
  ───────────────                                    ─────────────────────
  git commit "bump tag to a1b2c3d"
        │
        │  pushed to helm-chart-based-deployment
        ▼
  ┌─────────────────┐        polls / watches        ┌─────────────────────┐
  │  values.yaml     │ ◄───────────────────────────  │  Application         │
  │  tag: "a1b2c3d"  │                                │  (Argo CD resource)  │
  └─────────────────┘                                └──────────┬──────────┘
                                                                  │  detects the new commit
                                                                  ▼
                                                       helm template (renders chart)
                                                                  │
                                                                  ▼
                                                       kubectl apply (to the cluster)
                                                                  │
                                                                  ▼
                                                       old pods drain, new pods
                                                       start on image a1b2c3d
```

**Key property — `selfHeal: true`.** Argo CD doesn't just deploy once; it
continuously enforces that the cluster matches git. If someone manually edits
a resource in the cluster, Argo reverts it back to what's declared in the Helm
repo on the next sync. **Git is the only place deployment state should ever
be changed.**

**Secrets stay out of git.** Database credentials and API keys are managed as
[Bitnami Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) — encrypted
client-side with `kubeseal`, safe to commit, and only decryptable by the
controller running inside this specific cluster.

---

## ✅ How the Running App Gets Tested

Testing happens at two points in the pipeline, on two different things:

```
  BEFORE deploy (in CI, on the CODE)         AFTER deploy (on the LIVE APP)
  ───────────────────────────────────         ──────────────────────────────
  pytest — unit tests                         OWASP ZAP — DAST baseline scan
  (password hashing, schema validation)       (headers, cookies, XSS surface)
        │                                            │
        ▼                                            ▼
  gate BEFORE an image is even built          confirms the DEPLOYED app is
                                               still safe, continuously
```

Once Argo CD has synced, the app is reachable at the cluster's exposed
NodePort. A quick manual health check:

```bash
curl -I http://<node-ip>:30080          # 200 OK = frontend serving
curl -I http://<node-ip>:30080/health   # backend health check, via nginx proxy
```

And the full picture of what's running, at any time:

```bash
kubectl get application movie-watchlist -n argocd    # Synced / Healthy?
kubectl get pods -A | grep ns-helm                    # all tiers Running?
```

---

## 📊 Observability

Once deployed, the app is continuously watched by **Prometheus + Grafana**,
running in-cluster (deployed via Helm, pinned to a dedicated worker node so
metrics storage doesn't compete with the control plane):

- **Node Exporter** dashboards — per-node CPU/memory/disk health
- **Kubernetes / Compute Resources (Namespace)** — live pod CPU/memory for
  `backend-ns-helm`, `frontend-ns-helm`, `db-ns-helm`
- Pod restart counts — the earliest signal something's crash-looping

---

## 🗂️ Where Everything Lives

```
movie-recomendation/                      (this repo)
├── .github/workflows/
│   └── cicd-pipeline.yml        # the full pipeline described above
├── sonar-project.properties     # SonarCloud project config + quality gate
├── backend/
│   ├── app/                     # FastAPI source
│   ├── tests/                   # pytest unit tests (stage ②)
│   └── Dockerfile
├── frontend/
│   ├── nginx.conf                # reverse proxy config
│   └── Dockerfile
└── docs/
    └── architecture_notes.md    # container networking deep-dive (original README)

helm-chart-based-deployment/              (separate repo — watched by Argo CD)
└── helm-chart-deployment/movie-watchlist/
    ├── values.yaml               # image tags live here — CI writes to this file
    └── templates/                # Kubernetes manifests + SealedSecrets
```

---

## 🛠️ Tech Stack

| Layer | Tools |
|:------|:------|
| **App** | Python, FastAPI, Nginx, PostgreSQL, scikit-learn |
| **CI** | GitHub Actions, pytest, ruff |
| **Security** | SonarCloud (SAST), Trivy (image scan), OWASP ZAP (DAST) |
| **Packaging** | Docker, Helm |
| **CD** | Argo CD (GitOps), Bitnami Sealed Secrets |
| **Platform** | Kubernetes (k3s), AWS EC2 |
| **Observability** | Prometheus, Grafana |

For the container-level networking story — nginx reverse proxy, Docker
service DNS, and why the same image runs anywhere with zero reconfiguration —
see [`docs/architecture_notes.md`](docs/architecture_notes.md).
