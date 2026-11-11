"""Compiler that transforms `data/papers.json` (SSOT) into `README.md` and `docs/papers.json`."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from src.public import build_public
from src.schema import PaperDatabase, PaperRecord, TaxonomyConfig
from src.storage import _encode

REPO_URL = "https://github.com/mango-jeongi/awesome-gaussian-splatting"
PAGES_URL = "https://mango-jeongi.github.io/awesome-gaussian-splatting/"


def gfm_slug(text: str) -> str:
    """Generate a GitHub Flavored Markdown (GFM) header anchor slug.

    GFM downcases, strips punctuation (preserving whitespace and hyphens),
    and converts each whitespace character to a hyphen. Punctuation removal
    surrounding characters like ' & ' leaves two spaces, which translates
    to '--'.
    """
    cleaned = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"\s", "-", cleaned)


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
        "# Awesome 3D Gaussian Splatting (3DGS) — Comprehensive Research Database",
        "",
        f"[![CI Quality Gate]({REPO_URL}/actions/workflows/ci.yml/badge.svg?branch=main)]({REPO_URL}/actions/workflows/ci.yml) "
        f"[![Daily arXiv Feed]({REPO_URL}/actions/workflows/daily-feed.yml/badge.svg)]({REPO_URL}/actions/workflows/daily-feed.yml) "
        f"[![Searchable Web Database](https://img.shields.io/badge/Web_Database-GitHub_Pages-0ea5e9?logo=github)]({PAGES_URL}) "
        f"[![Papers Indexed](https://img.shields.io/badge/Papers_Indexed-{total}-10b981)](#taxonomy-overview)",
        "",
        f"> **Interactive Searchable Database**: Browse, filter by subdomain or technical tags, and export BibTeX citations at **[{PAGES_URL.replace('https://', '').rstrip('/')}]({PAGES_URL})**.",
        "",
        "An autonomous research database aggregating **3D/4D Gaussian Splatting** and neural rendering literature.",
        "- **Living Aggregate**: Continuous tracking across arXiv preprints, expanding to Hugging Face, OpenAlex, Semantic Scholar, and conference proceedings.",
        "- **Weekly Release Cycle**: Daily arXiv ingestion lands on `feed`, synced to `main` every Wednesday and published to GitHub Pages with tagged releases every Sunday.",
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
        anchor = gfm_slug(cat.name)
        lines.append(f"| **[{cat.name}](#{anchor})** | `{cnt}` | {cat.description} |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Latest Additions (Top 25 Most Recent)",
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
        if len(cat_papers) > 60:
            lines.append(
                f"Showing 60 of {len(cat_papers)} papers. [Browse the full category]({PAGES_URL}#/catalog?category={quote(cat.name, safe='')})."
            )
            lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## Architecture & Multi-Phase Roadmap",
            "",
            "- **Phase 1: Foundations & Automated Ingestion (Completed)**",
            "  - Autonomous daily arXiv delta ingestion, Schema-on-Read One Big Table (`data/papers.json`), and deterministic rule-based taxonomy tagger.",
            "  - Trunk-based CI/CD workflows and instant-search responsive GitHub Pages web portal with dark/light themes and BibTeX export.",
            "",
            "- **Phase 2: Multi-Source Literature Expansion (In Progress)**",
            "  - Hugging Face Daily Papers integration (tracking community upvotes, trending papers, and interactive Gradio spaces).",
            "  - Ingestion of non-arXiv peer-reviewed proceedings (CVPR, ICCV, ECCV, SIGGRAPH, NeurIPS).",
            "  - Headless daemon orchestration on local hardware (`ssh msi-raider`) for Figure 1 teaser thumbnails and benchmark table extraction.",
            "",
            "- **Phase 3: Citation Intelligence & Knowledge Graph Network (Active Development)**",
            "  - Integration with OpenAlex and Semantic Scholar APIs to track global citation counts and citation velocity.",
            "  - Cross-paper reference network mapping mutual citations and foundational lineage within the 3DGS corpus.",
            "",
            "---",
            "",
            "## Optional Research Synthesis",
            "",
            "An explicit PDF-cluster command prepares source-hashed receipts and optional Gemini drafts with checked page quotations. Generated claims remain unreviewed and outside ingestion. See [setup, budgets and limitations](CONTRIBUTING.md#optional-pdf-cluster-synthesis). Local PDF preparation is verified; live Gemini generation and reviewed cluster synthesis remain pending.",
            "",
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
            "## Manual Operations",
            "",
            "- Official CVF evidence capture: `uv run python -m src.cli discover-cvf --listing <saved-official-listing.html> --venue CVPR --year 2025 --max-requests 10`. It resumes hash-validated metadata capture and does not import canonical papers; see [CVPR 2025 evidence](reports/cvpr2025-metadata-capture.md), [CVPR 2024 evidence](reports/cvpr2024-metadata-capture.md), and [CVPR 2023 evidence](reports/cvpr2023-metadata-capture.md).",
            "- [Historical backfill dispatch](.github/workflows/manual-backfill.yml): choose preview/apply, a stable run key, identical frozen dates, and a request ceiling. Completed validated checkpoints are retained on `feed` for resume.",
            "- [Reviewed worker import dispatch](.github/workflows/manual-worker-import.yml): select committed review/result JSON inputs. The runner verifies the canonical public PDF digest and exact reviewed decisions; preview is the default.",
            "- Both definitions share the repository writer concurrency group, verify the feed parent before an ordinary push, and run build/schema/lint/format/tests. Source PDFs remain temporary. See [operator instructions](CONTRIBUTING.md#manual-backfill-and-reviewed-worker-imports) for exact commands and limits.",
            "",
            "---",
            "",
            "## Contributing",
            "",
            "- **Submit a Paper or Code**: Authors and researchers are encouraged to submit newly released papers, official repositories, or project demos via our [Paper Submission Form](https://github.com/mango-jeongi/awesome-gaussian-splatting/issues/new?template=paper_submission.yml).",
            "- **Direct Contributions**: See [`CONTRIBUTING.md`](CONTRIBUTING.md) for local environment setup, testing standards, and taxonomy pull request guidelines.",
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
    if Path(data_path).resolve() in {Path(readme_path).resolve(), Path(docs_data_path).resolve()}:
        raise ValueError("Build outputs must not overwrite canonical input")
    db = PaperDatabase.load(data_path)
    cache_path = Path(data_path).parent / "signals" / "openalex-cache.json"
    if cache_path.exists():
        from src.extractors.citations import apply_cached_citations
        from src.openalex_cache import OpenAlexCache

        # Project changing provider evidence only into this build-owned copy.
        # Identity conflicts fail before any public output is written.
        apply_cached_citations(db, OpenAlexCache.load(cache_path))
    taxonomy = TaxonomyConfig.from_yaml(taxonomy_path)

    readme_md = generate_readme(db, taxonomy)
    Path(readme_path).write_text(readme_md, encoding="utf-8")

    docs_target = Path(docs_data_path)
    docs_target.parent.mkdir(parents=True, exist_ok=True)
    public_legacy = db.model_copy(deep=True)
    public_legacy.archive = {}
    # Normalize dictionary ordering independently of the source storage format.
    public_legacy = PaperDatabase.model_validate_json(
        _encode(public_legacy.model_dump(mode="json"))
    )
    public_legacy.save(docs_target)
    from src.workers.review import ReviewedExtractionStore

    reviewed_path = Path(data_path).parent / "extraction" / "reviewed.json"
    reviewed = (
        ReviewedExtractionStore.model_validate_json(reviewed_path.read_bytes())
        if reviewed_path.exists()
        else None
    )
    from src.public_signals import public_signals

    signals = public_signals(db, Path(data_path).parent / "signals")
    from src.public_trending import public_trending
    from src.ranking import RankingConfig

    config = RankingConfig.load(Path(__file__).resolve().parent.parent / "config/ranking.yaml")
    trending = public_trending(db, Path(data_path).parent / "signals", config)
    build_public(
        db, docs_target.parent / "data", reviewed=reviewed, signals=signals, trending=trending
    )
