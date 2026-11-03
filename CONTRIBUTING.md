# Contributing to Awesome 3D Gaussian Splatting

Thank you for your interest in contributing! This project is an open-source, community-driven living aggregate of **3D/4D Gaussian Splatting** literature and neural rendering tools.

---

## How to Add Your Paper or Project

We welcome authors and researchers to submit new papers, official code repositories, and interactive project demos.

### Option 1: GitHub Issue Submission (Fastest)
1. Open a new issue using our **[Paper Submission Template](https://github.com/mango-jeongi/awesome-gaussian-splatting/issues/new?template=paper_submission.yml)**.
2. Provide your arXiv ID (or paper URL), title, primary author, and official code/project links.
3. Our automated pipeline or maintainers will verify and merge it into `data/papers.json`.

### Option 2: Pull Request (Direct Contribution)
1. Fork the repository and clone it locally.
2. Ensure you have `uv` installed (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`).
3. Set up the environment:
   ```bash
   uv sync --all-groups
   ```
4. If your paper is on arXiv, you can run the CLI ingest command or append the record to `data/papers.json`:
   ```bash
   # Validate schema adherence
   uv run python -m src.cli validate

   # Rebuild README and web portal artifacts
   uv run python -m src.cli build
   ```
5. Run the test suite:
   ```bash
   uv run pytest -v
   uv run ruff check .
   uv run ruff format --check .
   ```
6. Submit a pull request against the `feed` branch (or `main`).

---

## Proposing New Taxonomy Categories or Technical Tags

If a new subdomain is emerging in Gaussian Splatting (e.g., *Optical Flow Splatting*, *SDF Hybrids*, *Edge Robotics*):
1. Open an issue or edit [`config/taxonomy.yaml`](config/taxonomy.yaml).
2. Add keyword triggers under `categories` or `technical_tags`.
3. Test retroactive tagging:
   ```bash
   uv run python -m src.cli retag
   uv run python -m src.cli build
   ```
4. Submit a PR with the updated taxonomy and regenerated artifacts.

---

## Community Guidelines
- Respect the work of original authors and researchers.
- Maintain accurate venue attribution and code links.
- Keep the database neutral, factual, and comprehensive.

