# ReefScope

Underwater video analysis for fish activity and coral health research.

[![CI](https://github.com/WALKERKILLER/reefscope/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/WALKERKILLER/reefscope/actions/workflows/ci.yml)

**English** · [简体中文](README.zh-CN.md)

ReefScope brings video review, fish detection, and a research roadmap for tracking, coral segmentation, and reproducible evaluation into one repository. It builds on a Vue 3 and Django application, with shared data contracts for algorithm and frontend development.

## Project status

The current application includes video upload, YOLO-based fish detection, task progress, playback, and detection overlays. The repository also includes Docker configuration, CI, sample contracts, and a manual container-publishing workflow.

The following capabilities are planned:

- Fish tracking with persistent track IDs and time-weighted image-plane heatmaps.
- Coral segmentation, reviewed health labels, and reproducible training.
- Deterministic evaluation and training reports.
- Ocean monitoring dashboards with synchronized video overlays.

Model weights, videos, and training datasets are not included. Sample fixtures are illustrative; no model accuracy or coral-health performance is claimed. The application is intended for local research use and currently lacks API authentication.

## Quick start

### Requirements

- Python 3.12 and [uv](https://docs.astral.sh/uv/).
- Node.js 22 and npm.
- ffmpeg available on `PATH`.
- An authorized fish-detection model compatible with the pinned Ultralytics version.

### Backend

```bash
git clone https://github.com/WALKERKILLER/reefscope.git
cd reefscope
uv venv --python 3.12
source .venv/bin/activate

# CPU setup; see the development guide for CUDA.
uv pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
uv pip install -r backend/requirements.txt
```

Place your model at `backend/models/model_best.pt`, then start the backend:

```bash
cd backend
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

### Frontend

In a second terminal, from the repository root:

```bash
cd frontend
npm ci
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Open [localhost:5173](http://127.0.0.1:5173), upload an MP4 video, and start detection. The health endpoint is [localhost:8000/api/health](http://127.0.0.1:8000/api/health).

These commands use a POSIX shell. See the [development guide](docs/developers/development.md) for CUDA and Docker setup. Keep the service local until authentication, media access controls, and deployment hardening are implemented.

## Development

Run the repository and sample-contract checks without GPU dependencies:

```bash
python3 scripts/check.py
```

For backend checks without model inference, use a separate Python 3.12 environment with `backend/requirements-ci.txt`. Full commands and validation boundaries are documented in the [testing guide](docs/developers/testing.md). CI runs repository checks, Django checks and tests, and the frontend build. Container publishing is manually triggered and does not deploy a server.

## Documentation

- [Documentation index](docs/README.md) — the entry point for all project documentation.
- [Developer guide](docs/developers/README.md) — setup, architecture, testing, and releases.
- [MVP research](docs/mvp/README.md) — scientific scope, data contracts, and model proposals.
- [Agent collaboration](docs/agents/learning-workflow.md) — repository-local VibeWise guidance and repo-seed governance.
- [Work packages](docs/mvp/10-work-packages-and-integration.md) — module responsibilities and integration criteria.
- [Milestones](https://github.com/WALKERKILLER/reefscope/milestones) and [tasks](https://github.com/WALKERKILLER/reefscope/issues?q=is%3Aissue%20is%3Aopen) — work to claim and review.

Detailed project documentation is currently maintained in Simplified Chinese.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md), choose a work package, and agree on its inputs, outputs, and acceptance criteria before implementation. Changes to shared contracts need review; pull requests should include relevant tests and evidence.

Research results must identify their model, dataset, and evaluation protocol. Image-plane heatmaps do not establish geographic hotspots or population counts. Coral label mappings require expert review, and unavailable metrics must retain their missing-data reason.

## License and provenance

A project-wide license has not yet been assigned because authorization for the inherited source needs confirmation. Model weights, datasets, and third-party dependencies have their own terms. See [provenance and reuse boundaries](docs/developers/provenance.md) before redistribution.
