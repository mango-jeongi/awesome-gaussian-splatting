"""Compare independent CVPR accepted tables with frozen proceedings inventories."""

import hashlib
import re
import unicodedata
from html.parser import HTMLParser

from src.identity import title_key


class AcceptedTable(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_table = self.in_title = self.in_authors = False
        self.row = None
        self.rows = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table" and "elc-table" in attrs.get("class", "").split():
            self.in_table = True
        if not self.in_table:
            return
        if tag == "tr":
            self.row = {"title": [], "authors": []}
        if self.row is not None and tag == "strong":
            self.in_title = True
        if self.row is not None and tag == "i":
            self.in_authors = True

    def handle_data(self, text):
        if self.row is not None and self.in_title:
            self.row["title"].append(text)
        if self.row is not None and self.in_authors:
            self.row["authors"].append(text)

    def handle_endtag(self, tag):
        if tag == "strong":
            self.in_title = False
        if tag == "i":
            self.in_authors = False
        if tag == "tr" and self.row is not None:
            title = " ".join("".join(self.row["title"]).split())
            if title:
                self.rows.append(
                    {
                        "title": title,
                        "authors": [
                            " ".join(a.split())
                            for a in re.split(r"[⋅·]", "".join(self.row["authors"]))
                            if a.strip()
                        ],
                    }
                )
            self.row = None
            self.in_title = self.in_authors = False
        if tag == "table":
            self.in_table = False


def typography_key(text):
    text = unicodedata.normalize("NFKD", text.replace("°", "deg"))
    return re.sub(r"[^a-z0-9]", "", text.encode("ascii", "ignore").decode().lower())


def reconcile_inventory(accepted_bytes, proceedings, *, source_url, listing_sha256):
    parser = AcceptedTable()
    parser.feed(accepted_bytes.decode("utf-8"))
    parser.close()
    if not parser.rows or not proceedings:
        raise ValueError("Both source inventories must contain rows")
    accepted = {title_key(row["title"]): row for row in parser.rows}
    published = {title_key(row["title"]): row for row in proceedings}
    if len(accepted) != len(parser.rows) or len(published) != len(proceedings):
        raise ValueError("Normalized title collision requires explicit reconciliation")
    common = set(accepted) & set(published)
    variants, ambiguous = [], []
    left, right = set(accepted) - common, set(published) - common
    for key in sorted(left):
        matches = [
            other
            for other in right
            if typography_key(published[other]["title"]) == typography_key(accepted[key]["title"])
        ]
        if len(matches) == 1:
            target = matches[0]
            a, b = accepted[key], published[target]
            full_authors = bool(a["authors"]) and [typography_key(x) for x in a["authors"]] == [
                typography_key(x) for x in b["authors"]
            ]
            if full_authors:
                variants.append(
                    {"accepted": a, "proceedings": b, "full_author_sequence_matches": True}
                )
                right.remove(target)
            else:
                ambiguous.append(
                    {"accepted": a, "proceedings": b, "reason": "Full author sequence differs"}
                )
    matched_left = {title_key(pair["accepted"]["title"]) for pair in variants}
    mismatched_authors = [
        {"accepted": accepted[k], "proceedings": published[k]}
        for k in sorted(common)
        if [typography_key(x) for x in accepted[k]["authors"]]
        != [typography_key(x) for x in published[k]["authors"]]
    ]
    return {
        "accepted_source_url": source_url,
        "accepted_source_sha256": hashlib.sha256(accepted_bytes).hexdigest(),
        "listing_sha256": listing_sha256,
        "accepted_rows": len(parser.rows),
        "cvf_rows": len(proceedings),
        "normalized_title_matches": len(common),
        "exact_title_author_differences": mismatched_authors,
        "typography_pairs": variants,
        "ambiguous_pairs": ambiguous,
        "accepted_only": [accepted[k] for k in sorted(left - matched_left)],
        "cvf_only": [published[k] for k in sorted(right)],
        "canonical_identity_modified": False,
        "inventory_reconciled": False,
    }
