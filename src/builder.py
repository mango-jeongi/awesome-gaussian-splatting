"""Compiler that transforms `data/papers.json` (SSOT) into `README.md` and `docs/papers.json`."""

from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path

from src.schema import PaperDatabase, PaperRecord, TaxonomyConfig

REPO_URL = "https://github.com/mango-jeongi/awesome-gaussian-splatting"
PAGES_URL = "https://mango-jeongi.github.io/awesome-gaussian-splatting/"


def _format_links(p: PaperRecord) -> str:
    badges: list[str] = []
    if p.paper_url:
        label = f"arXiv:{p.arxiv_id}" if p.arxiv_id else "Paper"
        badges.append(f"[[{label}]]({p.paper_url})")
    if p.pdf_url:
        badges.append(f"[[PDF]]({p.pdf_url})")
    if p.code_url:
        badges.append(f"[[Code]]({p.code_url})")
    if p.project_url:
        badges.append(f"[[Project]]({p.project_url})")
    return " ".join(badges) if badges else "—"


def generate_readme(db: PaperDatabase, taxonomy: TaxonomyConfig) -> str:
    """Render a clean, truncation-safe Markdown index from the One Big Table."""
    total = len(db.papers)
    with_code = sum(1 for p in db.papers if p.code_url)
    last_date = db.last_updated[:10]

    cat_counts: Counter[str] = Counter()
    for p in db.papers:
        cat_counts[p.primary_category] += 1

    lines: list[str] = [
        "# Awesome 3D Gaussian Splatting (3DGS) — Frontier Research Database",
        "",
        f"[![CI Quality Gate]({REPO_URL}/actions/workflows/ci.yml/badge.svg)]({REPO_URL}/actions/workflows/ci.yml) "
        f"[![Daily arXiv Feed]({REPO_URL}/actions/workflows/daily-feed.yml/badge.svg)]({REPO_URL}/actions/workflows/daily-feed.yml) "
        f"[![Searchable Web Database](https://img.shields.io/badge/Web_Database-GitHub_Pages-0ea5e9?logo=github)]({PAGES_URL}) "
        f"[![Papers Indexed](https://img.shields.io/badge/Papers_Indexed-{total}-10b981)](#taxonomy-overview)",
        "",
        "> **Interactive Searchable Database**: Browse, filter by subdomain or emergent technical tags, toggle Dark/Light mode, and export BibTeX citations at **[mango-jeongi.github.io/awesome-gaussian-splatting](https://mango-jeongi.github.io/awesome-gaussian-splatting/)**.",
        "",
        "An autonomous, schema-validated **One Big Table (OBT)** research database tracking frontier **3D/4D Gaussian Splatting** and neural rendering literature. Built with **Data Operations & DevSecOps** best practices:",
        "- **Single Source of Truth**: Canonical records stored in [`data/papers.json`](data/papers.json) and validated via **Pydantic v2** (supporting both arXiv preprints and non-arXiv IEEE/CVF/ACM publications).",
        "- **Declarative Taxonomy & Emergent Tagging**: Subdomains and technical tags are defined in [`config/taxonomy.yaml`](config/taxonomy.yaml) and enriched via GitHub Models (`gpt-4o-mini`) with deterministic fallback.",
        "- **Trunk-Based CI/CD (<72h Branch SLA)**: Daily arXiv ingestion lands on `feed`, synced to `main` every Wednesday (`midweek-sync.yml`) and published to GitHub Pages with tagged releases every Sunday (`weekly-release.yml`).",
        "",
        f"*Last updated: `{last_date}` | Total Papers: **{total}** | With Official Code: **{with_code}***",
        "",
        "---",
        "",
        "## Taxonomy Overview",
        "",
        "| Category | Papers | Description |",
        "| :--- | :---: | :--- |",
    ]

    for cat in taxonomy.categories:
        cnt = cat_counts.get(cat.name, 0)
        anchor = cat.name.lower().replace("&", "").replace(",", "").replace(" ", "-")
        while "--" in anchor:
            anchor = anchor.replace("--", "-")
        lines.append(f"| **[{cat.name}](#{anchor})** | `{cnt}` | {cat.description} |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Latest Frontier Additions (Top 25 Most Recent)",
            "",
            "| Date | Title | First Author | Category | Links |",
            "| :---: | :--- | :--- | :--- | :---: |",
        ]
    )

    for p in db.papers[:25]:
        venue_badge = f" *({p.venue})*" if p.venue else ""
        safe_title = p.title.replace("|", "\\|")
        lines.append(
            f"| `{p.published_date}` | **{safe_title}**{venue_badge} | {p.first_author} | `{p.primary_category}` | {_format_links(p)} |"
        )

    lines.extend(["", "---", "", "## Categorized Paper Catalog", ""])

    for cat in taxonomy.categories:
        cat_papers = [p for p in db.papers if p.primary_category == cat.name]
        lines.append(f"### {cat.name}")
        lines.append("")
        lines.append(f"*{cat.description}* ({len(cat_papers)} papers)")
        lines.append("")
        if not cat_papers:
            lines.append("_No papers indexed in this category yet._")
            lines.append("")
            continue

        lines.append("<details>")
        lines.append(
            f"<summary><strong>View {len(cat_papers)} papers in {cat.name}</strong></summary>"
        )
        lines.append("")
        lines.append("| Date | Title & TL;DR | Authors | Tags | Links |")
        lines.append("| :---: | :--- | :--- | :--- | :---: |")
        for p in cat_papers[:60]:
            safe_title = p.title.replace("|", "\\|")
            safe_tldr = (p.tldr or "").replace("|", "\\|")
            venue_str = f" **[{p.venue}]**" if p.venue else ""
            tag_pills = ", ".join(f"`{t}`" for t in p.tags[:4])
            lines.append(
                f"| `{p.published_date[:7]}` | **{safe_title}**{venue_str}<br><sub>{safe_tldr}</sub> | {p.first_author} | {tag_pills} | {_format_links(p)} |"
            )
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## Adding New Tags or Categories",
            "",
            "1. Edit [`config/taxonomy.yaml`](config/taxonomy.yaml) to add a new category or keyword trigger under `categories` or `technical_tags`.",
            "2. Run the retroactive Schema-on-Read re-indexer:",
            "   ```bash",
            "   uv run python -m src.cli retag",
            "   uv run python -m src.cli build",
            "   ```",
            "3. Both `data/papers.json`, `README.md`, and the dynamic filter pills on the GitHub Pages web app will automatically reflect the expanded taxonomy.",
            "",
            "---",
            "",
            "## Acknowledgments & Credits",
            "",
            "- Automated daily arXiv crawling concept inspired by [yangzf-1023/awesome-gaussian-splatting](https://github.com/yangzf-1023/awesome-gaussian-splatting).",
            "- Searchable web interface design inspired by [MrNeRF/awesome-3D-gaussian-splatting](https://github.com/MrNeRF/awesome-3D-gaussian-splatting) and [Radiance Fields Research Database](https://radiancefields.com/papers).",
        ]
    )

    return "\n".join(lines).strip() + "\n"


def build_artifacts(
    data_path: str | Path,
    taxonomy_path: str | Path,
    readme_path: str | Path,
    docs_data_path: str | Path,
) -> None:
    """Compile README.md and copy data/papers.json to docs/papers.json for GitHub Pages."""
    db = PaperDatabase.load(data_path)
    taxonomy = TaxonomyConfig.from_yaml(taxonomy_path)

    readme_md = generate_readme(db, taxonomy)
    Path(readme_path).write_text(readme_md, encoding="utf-8")

    docs_target = Path(docs_data_path)
    docs_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(data_path, docs_target)
