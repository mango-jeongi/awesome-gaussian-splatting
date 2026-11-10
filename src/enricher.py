"""Multi-provider enrichment engine for URLs, venues, categories, tags, and TL;DRs.

Execution Priority:
1. Deterministic Regex Extraction (Always runs first to extract GitHub repos, project pages, and conference venues from comment/abstract).
2. Priority 1 LLM: GitHub Models (`gpt-4o-mini` via `https://models.inference.ai.azure.com`) if `GH_MODELS_TOKEN` or `GITHUB_TOKEN` is configured.
3. Priority 2 LLM: Google Gemini (`gemini-2.5-flash`) — Placeholder / skipped by default unless `ENABLE_GEMINI=true` and `GEMINI_API_KEY` are set.
4. Priority 3 Fallback: Deterministic taxonomy keyword scoring (`config/taxonomy.yaml`) and lead-sentence TL;DR extraction.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx

from src.schema import PaperRecord, TaxonomyConfig

GITHUB_REPO_RE = re.compile(
    r"https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
    re.IGNORECASE,
)
PROJECT_URL_RE = re.compile(
    r"https?://(?:[A-Za-z0-9-]+\.)+(?:github\.io|pages\.dev|netlify\.app|vercel\.app)(?:/[A-Za-z0-9_./-]*)?",
    re.IGNORECASE,
)
VENUE_RE = re.compile(
    r"\b(CVPR|ICCV|ECCV|SIGGRAPH(?:\s+Asia)?|NeurIPS|ICLR|ICML|AAAI|IJCAI|ICRA|IROS|CoRL|RSS|BMVC|3DV|WACV|MICCAI|ISBI|TVCG|TOG|TPAMI|RAL|RA-L)\s*['’]?(20\d{2}|\d{2})?\b",
    re.IGNORECASE,
)


def extract_urls_and_venue(record: PaperRecord) -> PaperRecord:
    """Extract GitHub code URLs, project page URLs, and conference venues from comment and abstract."""
    blob = f"{record.comment or ''} {record.abstract or ''}"

    code_url = record.code_url
    if not code_url:
        gh_matches = GITHUB_REPO_RE.findall(blob)
        if gh_matches:
            cleaned = gh_matches[0].rstrip(".,;:)]}>\"'")
            code_url = re.sub(r"\.git$", "", cleaned)

    project_url = record.project_url
    if not project_url:
        proj_matches = PROJECT_URL_RE.findall(blob)
        if proj_matches:
            project_url = proj_matches[0].rstrip(".,;:)]}>\"'")

    venue = record.venue
    if not venue:
        venue_match = VENUE_RE.search(blob)
        if venue_match:
            conf = venue_match.group(1).upper()
            if conf == "RAL":
                conf = "RA-L"
            yr = venue_match.group(2)
            if yr and len(yr) == 2:
                yr = f"20{yr}"
            elif not yr:
                yr = str(record.year)
            venue = f"{conf} {yr}".strip()

    return record.with_provider_updates(
        update={
            "code_url": code_url,
            "project_url": project_url,
            "venue": venue,
        }
    )


def matches_pattern(pattern: str, text: str) -> bool:
    """Match a keyword pattern with word-boundary safety for short acronyms/terms."""
    p = pattern.strip().lower()
    if not p:
        return False
    # If short token (<= 4 chars, e.g. ct, mri, lod, sdf, vr, xr, sar), enforce regex word boundary
    if len(p) <= 4 and re.match(r"^[a-z0-9_-]+$", p):
        return bool(re.search(r"\b" + re.escape(p) + r"\b", text))
    return p in text


def synthesize_tldr(title: str, abstract: str) -> str:
    """Distill the core technical contribution from an abstract, stripping generic preamble."""
    if not abstract:
        return ""

    text = re.sub(r"\s+", " ", abstract).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)

    background_markers = (
        "neural radiance field",
        "recently,",
        "in recent years",
        "novel view synthesis",
        "has attracted significant attention",
        "has emerged as",
        "have achieved impressive",
        "is a fundamental problem",
        "has demonstrated remarkable",
        "remains challenging",
        "despite the success",
        "although 3d gaussian",
        "3d gaussian splatting (3dgs) has",
        "3d gaussian splatting has revolutionized",
    )

    action_markers = (
        "we propose",
        "we introduce",
        "we present",
        "we develop",
        "we design",
        "this paper proposes",
        "this paper introduces",
        "this paper presents",
        "this paper develops",
        "this work proposes",
        "this work introduces",
        "this work presents",
        "this work develops",
        "to address this",
        "to overcome this",
        "to tackle this",
    )

    # 1. Prefer explicit contribution sentence
    candidate = ""
    for s in sentences:
        s_lower = s.lower().strip()
        if any(m in s_lower for m in action_markers):
            candidate = s.strip()
            break

    # 2. Otherwise pick first non-background sentence highlighting capability
    if not candidate:
        for s in sentences:
            s_lower = s.lower().strip()
            if any(s_lower.startswith(bm) or bm in s_lower[:50] for bm in background_markers):
                continue
            if any(
                w in s_lower
                for w in (
                    "achieves",
                    "enables",
                    "allows",
                    "formulates",
                    "demonstrates",
                    "outperforms",
                )
            ):
                candidate = s.strip()
                break

    # 3. Fallback to first non-background sentence or first sentence
    if not candidate:
        non_bg = [
            s.strip()
            for s in sentences
            if not any(s.lower().strip().startswith(bm) for bm in background_markers)
        ]
        candidate = non_bg[0] if non_bg else sentences[0].strip()

    # Clean boilerplate prefixes into concise active summary
    clean = candidate
    clean = re.sub(
        r"^(in this (paper|work|study|letter),?\s+)?we\s+propose\s+(a\s+novel\s+|an\s+effective\s+|a\s+new\s+)?",
        "Proposes ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^(in this (paper|work|study|letter),?\s+)?we\s+introduce\s+(a\s+novel\s+|an\s+effective\s+|a\s+new\s+)?",
        "Introduces ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^(in this (paper|work|study|letter),?\s+)?we\s+present\s+(a\s+novel\s+|an\s+effective\s+|a\s+new\s+)?",
        "Presents ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^(in this (paper|work|study|letter),?\s+)?we\s+develop\s+(a\s+novel\s+|an\s+effective\s+|a\s+new\s+)?",
        "Develops ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^(in this (paper|work|study|letter),?\s+)?we\s+design\s+(a\s+novel\s+|an\s+effective\s+|a\s+new\s+)?",
        "Designs ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^this (paper|work|study)\s+proposes\s+(a\s+novel\s+|an\s+effective\s+|a\s+new\s+)?",
        "Proposes ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^this (paper|work|study)\s+introduces\s+(a\s+novel\s+|an\s+effective\s+|a\s+new\s+)?",
        "Introduces ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^this (paper|work|study)\s+presents\s+(a\s+novel\s+|an\s+effective\s+|a\s+new\s+)?",
        "Presents ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^to (address|tackle|overcome) (this|these) (issue|problem|limitation)s?,?\s+(we\s+)?(propose|introduce|present)\s+",
        "Proposes ",
        clean,
        flags=re.IGNORECASE,
    )

    # Clean trailing fragments
    clean = re.sub(r"\s+", " ", clean).strip()
    if len(clean) > 210:
        cut = clean[:207]
        last_space = cut.rfind(" ")
        clean = (cut[:last_space] if last_space > 120 else cut) + "..."

    if clean and clean[0].islower():
        clean = clean[0].upper() + clean[1:]
    return clean


class DeterministicEnricher:
    """Rule-based category classifier and technical tagger driven by `config/taxonomy.yaml`."""

    def __init__(self, taxonomy: TaxonomyConfig) -> None:
        self.taxonomy = taxonomy

    def enrich(self, record: PaperRecord) -> PaperRecord:
        record = extract_urls_and_venue(record)
        text = f"{record.title} {record.abstract} {record.comment or ''}".lower()

        # Score each category in taxonomy.yaml with word-boundary awareness
        scored_cats: list[tuple[int, str]] = []
        for cat in self.taxonomy.categories:
            score = sum(1 for kw in cat.keywords if matches_pattern(kw, text))
            if score > 0:
                scored_cats.append((score, cat.name))

        scored_cats.sort(key=lambda x: x[0], reverse=True)
        if scored_cats:
            categories = [name for _, name in scored_cats[:2]]
        elif record.categories and record.categories != [self.taxonomy.default_category]:
            categories = record.categories
        else:
            categories = [self.taxonomy.default_category]

        # Match technical tags from taxonomy.yaml with word-boundary safety
        matched_tags: list[str] = []
        for tag_name, triggers in self.taxonomy.technical_tags.items():
            if any(matches_pattern(trig, text) for trig in triggers):
                matched_tags.append(tag_name)

        # Preserve any existing emergent tags discovered earlier (excluding overused "3DGS" and "Ultrasound & Medical")
        valid_cat_names = {c.name for c in self.taxonomy.categories}
        existing_custom_tags = [
            t
            for t in record.tags
            if t not in matched_tags
            and t not in valid_cat_names
            and t not in ("3DGS", "Ultrasound & Medical")
        ]
        all_tags = matched_tags + existing_custom_tags
        if not all_tags:
            all_tags = ["Foundations"]

        # Generate refined TL;DR if missing or if it looks like a boilerplate first sentence
        tldr = record.tldr
        needs_refinement = (
            not tldr
            or tldr.lower().startswith("3d gaussian splatting (3dgs) has recently")
            or tldr.lower().startswith("in this paper, we propose")
            or tldr.lower().startswith("neural radiance fields")
        )
        if needs_refinement and record.abstract:
            tldr = synthesize_tldr(record.title, record.abstract)

        return PaperRecord.model_validate(
            record.with_provider_updates(
                update={
                    "primary_category": categories[0],
                    "categories": categories,
                    "tags": all_tags[:8],
                    "tldr": tldr or record.tldr,
                }
            ).model_dump()
        )


class GeminiEnricher:
    """Priority 2 LLM Enricher (Google Gemini Flash) — Placeholder / Skipped by default."""

    def __init__(self, taxonomy: TaxonomyConfig) -> None:
        self.taxonomy = taxonomy
        self.enabled = os.getenv("ENABLE_GEMINI", "false").lower() in ("1", "true", "yes")
        self.api_key = os.getenv("GEMINI_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self.enabled and self.api_key)

    def enrich(self, record: PaperRecord) -> PaperRecord | None:
        """Placeholder stub: skipped unless explicitly enabled and configured."""
        if not self.is_available():
            return None
        return None


class GitHubModelsEnricher:
    """Priority 1 LLM Enricher using GitHub Models (`gpt-4o-mini`) via Azure AI Inference endpoint."""

    ENDPOINT = "https://models.inference.ai.azure.com/chat/completions"

    def __init__(self, taxonomy: TaxonomyConfig, model: str = "gpt-4o-mini") -> None:
        self.taxonomy = taxonomy
        self.model = model
        self.token = os.getenv("GH_MODELS_TOKEN") or os.getenv("GITHUB_TOKEN") or ""
        self.enabled = os.getenv("ENABLE_GH_MODELS", "true").lower() in ("1", "true", "yes")

    def is_available(self) -> bool:
        return bool(self.enabled and self.token)

    def enrich(self, record: PaperRecord) -> PaperRecord | None:
        if not self.is_available():
            return None

        valid_categories = [c.name for c in self.taxonomy.categories]
        canonical_tags = list(self.taxonomy.technical_tags.keys())

        system_prompt = (
            "You are an expert computer vision research indexer specializing in 3D Gaussian Splatting (3DGS). "
            "Given a paper title and abstract, return a strict JSON object with keys:\n"
            f"- 'categories': 1 or 2 category names chosen strictly from {json.dumps(valid_categories)}\n"
            f"- 'tags': 2 to 5 technical tags (choose applicable tags from {json.dumps(canonical_tags)} plus up to 2 concise emergent technical tags in Title-Case if the paper introduces a novel sub-topic)\n"
            "- 'tldr': A single crisp technical sentence (<200 chars) summarizing the core contribution."
        )
        user_prompt = f"Title: {record.title}\nAbstract: {record.abstract}"

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    self.ENDPOINT,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"},
                    },
                )
                resp.raise_for_status()
                payload = resp.json()
                content = payload["choices"][0]["message"]["content"]
                parsed = json.loads(content)

                cats = [c for c in parsed.get("categories", []) if c in valid_categories]
                tags = [str(t).strip() for t in parsed.get("tags", []) if str(t).strip()]
                tldr = str(parsed.get("tldr", "")).strip()

                if not cats:
                    return None

                base = extract_urls_and_venue(record)
                return PaperRecord.model_validate(
                    base.with_provider_updates(
                        update={
                            "primary_category": cats[0],
                            "categories": cats[:2],
                            "tags": tags[:8] or base.tags,
                            "tldr": tldr or base.tldr,
                        }
                    ).model_dump()
                )
        except Exception:
            return None


class MultiProviderEnricher:
    """Orchestrates Priority 1 (GitHub Models) -> Priority 2 (Gemini Placeholder) -> Priority 3 (Deterministic)."""

    def __init__(self, taxonomy_path: str | Path) -> None:
        self.taxonomy = TaxonomyConfig.from_yaml(taxonomy_path)
        self.gh_models = GitHubModelsEnricher(self.taxonomy)
        self.gemini = GeminiEnricher(self.taxonomy)
        self.deterministic = DeterministicEnricher(self.taxonomy)

    def enrich(self, record: PaperRecord, use_llm: bool = True) -> PaperRecord:
        # Always run deterministic pass as baseline (captures regex URLs, venues, and baseline tags)
        enriched = self.deterministic.enrich(record)

        if not use_llm:
            return enriched

        # Priority 1: GitHub Models (gpt-4o-mini)
        if self.gh_models.is_available():
            llm_res = self.gh_models.enrich(enriched)
            if llm_res is not None:
                # Merge deterministic tags with LLM emergent tags
                merged_tags = list(dict.fromkeys(llm_res.tags + enriched.tags))[:8]
                return llm_res.with_provider_updates(update={"tags": merged_tags})

        # Priority 2: Google Gemini Flash (Placeholder / skipped by default)
        if self.gemini.is_available():
            gem_res = self.gemini.enrich(enriched)
            if gem_res is not None:
                return gem_res

        # Priority 3: Deterministic fallback
        return enriched
