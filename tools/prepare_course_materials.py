from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from lib.common import (
    ensure_dir,
    first_heading,
    normalize_text,
    relative_to_repo,
    repo_path,
    resolve_config,
    slugify,
    split_into_chunks,
    utc_now_iso,
    write_jsonl,
    write_text,
)
from lib.extract import ALL_HANDLED_EXTENSIONS, combine_segments, extract_material


def iter_material_files(material_roots: dict[str, list[str]]):
    for category, roots in material_roots.items():
        for root_str in roots:
            root = repo_path(root_str)
            if not root.exists():
                yield category, root, None
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                if any(part.startswith(".") for part in path.relative_to(root).parts):
                    continue
                yield category, root, path


def make_relative_inside_root(root: Path, path: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return Path(path.name)


def create_sqlite_index(db_path: Path) -> tuple[sqlite3.Connection, bool]:
    ensure_dir(db_path.parent)
    connection = sqlite3.connect(str(db_path))
    connection.executescript(
        '''
        DROP TABLE IF EXISTS documents;
        DROP TABLE IF EXISTS chunks;
        DROP TABLE IF EXISTS chunks_fts;

        CREATE TABLE documents (
            doc_id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            source_path TEXT NOT NULL,
            title TEXT NOT NULL,
            file_type TEXT NOT NULL,
            normalized_text_path TEXT NOT NULL,
            text_length INTEGER NOT NULL,
            extraction_method TEXT NOT NULL,
            extraction_status TEXT NOT NULL,
            warnings TEXT NOT NULL
        );

        CREATE TABLE chunks (
            chunk_id TEXT PRIMARY KEY,
            doc_id TEXT NOT NULL,
            category TEXT NOT NULL,
            source_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            title TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            locator_type TEXT NOT NULL,
            locator TEXT NOT NULL,
            extraction_status TEXT NOT NULL,
            content TEXT NOT NULL
        );
        '''
    )
    fts_enabled = True
    try:
        connection.execute(
            '''
            CREATE VIRTUAL TABLE chunks_fts USING fts5(
                chunk_id UNINDEXED,
                title,
                content,
                category,
                source_path UNINDEXED,
                tokenize = "porter unicode61"
            );
            '''
        )
    except sqlite3.OperationalError:
        fts_enabled = False
    return connection, fts_enabled


def normalize_meta_paths(meta: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(meta)
    caption_path = normalized.get("caption_path")
    if caption_path:
        normalized["caption_path"] = relative_to_repo(Path(caption_path))
    return normalized


def insert_document(connection: sqlite3.Connection, row: dict[str, Any]) -> None:
    connection.execute(
        '''
        INSERT INTO documents (
            doc_id, category, source_path, title, file_type, normalized_text_path, text_length,
            extraction_method, extraction_status, warnings
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            row["doc_id"],
            row["category"],
            row["source_path"],
            row["title"],
            row["file_type"],
            row["normalized_text_path"],
            row["text_length"],
            row["extraction_method"],
            row["extraction_status"],
            "\n".join(row.get("warnings", [])),
        ),
    )


def insert_chunk(connection: sqlite3.Connection, row: dict[str, Any], *, fts_enabled: bool) -> None:
    connection.execute(
        '''
        INSERT INTO chunks (
            chunk_id, doc_id, category, source_path, file_type, title, chunk_index,
            locator_type, locator, extraction_status, content
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            row["chunk_id"],
            row["doc_id"],
            row["category"],
            row["source_path"],
            row["file_type"],
            row["title"],
            row["chunk_index"],
            row["locator_type"],
            row["locator"],
            row["extraction_status"],
            row["text"],
        ),
    )

    if fts_enabled:
        connection.execute(
            '''
            INSERT INTO chunks_fts (
                chunk_id, title, content, category, source_path
            ) VALUES (?, ?, ?, ?, ?)
            ''',
            (row["chunk_id"], row["title"], row["text"], row["category"], row["source_path"]),
        )


def failed_manifest_row(category: str, path: Path, status: str, warning: str) -> dict[str, Any]:
    title = path.stem.replace("_", " ").replace("-", " ")
    return {
        "doc_id": slugify(f"{category}-{relative_to_repo(path)}"),
        "category": category,
        "source_path": relative_to_repo(path),
        "title": title,
        "file_type": path.suffix.lower(),
        "normalized_text_path": "",
        "text_length": 0,
        "extraction_method": "unsupported" if status == "unsupported" else "failed",
        "extraction_status": status,
        "warnings": [warning],
        "indexed_at": utc_now_iso(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare local course materials for the virtual TA.")
    parser.add_argument("--config", help="Path to config TOML file.")
    args = parser.parse_args()

    config_path, config = resolve_config(args.config)

    cache_cfg = config["cache"]
    retrieval_cfg = config["retrieval"]
    ingestion_cfg = config.get("ingestion", {})

    manifest_path = repo_path(cache_cfg["manifest"])
    chunks_path = repo_path(cache_cfg["chunks"])
    db_path = repo_path(cache_cfg["sqlite_index"])
    extracted_root = repo_path(cache_cfg["extracted_root"])
    catalog_markdown = repo_path(cache_cfg["catalog_markdown"])
    caption_root = repo_path(cache_cfg.get("image_caption_root", "cache/image_captions"))

    chunk_size = int(retrieval_cfg.get("chunk_size", 1400))
    chunk_overlap = int(retrieval_cfg.get("chunk_overlap", 180))

    ensure_dir(extracted_root)
    ensure_dir(caption_root)

    connection, fts_enabled = create_sqlite_index(db_path)

    manifest_rows: list[dict[str, Any]] = []
    chunk_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    counts_by_category: Counter[str] = Counter()
    counts_by_type: Counter[str] = Counter()
    counts_by_status: Counter[str] = Counter()
    doc_counter = 0
    chunk_counter = 0

    for category, root, path in iter_material_files(config["materials"]):
        if path is None:
            warning = f"Missing configured root for category '{category}': {root}"
            warnings.append(warning)
            continue

        suffix = path.suffix.lower()
        if suffix not in ALL_HANDLED_EXTENSIONS:
            warning = (
                f"Unsupported file type for {relative_to_repo(path)}. Convert it to PDF, PPTX, DOCX, TXT, "
                "Markdown, CSV, XLSX, TeX, HTML, or add an image caption."
            )
            manifest_row = failed_manifest_row(category, path, "unsupported", warning)
            manifest_rows.append(manifest_row)
            insert_document(connection, manifest_row)
            warnings.append(warning)
            counts_by_category[category] += 1
            counts_by_status["unsupported"] += 1
            counts_by_type[suffix or "(none)"] += 1
            doc_counter += 1
            continue

        try:
            segments, meta = extract_material(path, caption_root=caption_root, config=ingestion_cfg)
        except Exception as exc:  # noqa: BLE001
            warning = f"Failed to extract {relative_to_repo(path)}: {exc}"
            manifest_row = failed_manifest_row(category, path, "failed", warning)
            manifest_rows.append(manifest_row)
            insert_document(connection, manifest_row)
            warnings.append(warning)
            counts_by_category[category] += 1
            counts_by_status["failed"] += 1
            counts_by_type[suffix or "(none)"] += 1
            doc_counter += 1
            continue

        meta = normalize_meta_paths(meta)
        file_warnings = list(meta.get("warnings", []))
        warnings.extend(f"{relative_to_repo(path)}: {warning}" for warning in file_warnings)
        text = normalize_text(combine_segments(segments))
        status = meta.get("status", "indexed")

        normalized_text_path = ""
        if text:
            relative_inside_root = make_relative_inside_root(root, path)
            normalized_path = extracted_root / category / relative_inside_root
            normalized_path = normalized_path.with_suffix(normalized_path.suffix + ".txt")
            write_text(normalized_path, text)
            normalized_text_path = relative_to_repo(normalized_path)

        title = (
            first_heading(text)
            or next((segment.get("title", "") for segment in segments if segment.get("title")), "")
            or path.stem.replace("_", " ").replace("-", " ")
        )
        doc_id = slugify(f"{category}-{relative_to_repo(path)}")

        manifest_row = {
            "doc_id": doc_id,
            "category": category,
            "source_path": relative_to_repo(path),
            "title": title,
            "file_type": suffix,
            "normalized_text_path": normalized_text_path,
            "text_length": len(text),
            "extraction_method": meta.get("method", "unknown"),
            "extraction_status": status,
            "warnings": file_warnings,
            "indexed_at": utc_now_iso(),
        }
        for key in ("page_count", "slide_count", "sheet_count", "cell_count", "segment_count", "caption_path", "member_count"):
            if key in meta:
                manifest_row[key] = meta[key]
        manifest_rows.append(manifest_row)
        insert_document(connection, manifest_row)

        for segment_index, segment in enumerate(segments):
            segment_text = normalize_text(segment.get("text", ""))
            if not segment_text:
                continue
            chunks = split_into_chunks(segment_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            for piece_index, chunk_text in enumerate(chunks):
                chunk_id = slugify(f"{doc_id}-{segment_index:04d}-{piece_index:04d}")
                chunk_title = segment.get("title") or title
                chunk_row = {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "category": category,
                    "source_path": manifest_row["source_path"],
                    "file_type": suffix,
                    "title": chunk_title,
                    "chunk_index": chunk_counter,
                    "locator_type": segment.get("locator_type", "document"),
                    "locator": segment.get("locator", "document"),
                    "extraction_status": status,
                    "text": chunk_text,
                }
                chunk_rows.append(chunk_row)
                insert_chunk(connection, chunk_row, fts_enabled=fts_enabled)
                chunk_counter += 1

        counts_by_category[category] += 1
        counts_by_type[suffix or "(none)"] += 1
        counts_by_status[status] += 1
        doc_counter += 1

    connection.commit()
    connection.close()

    write_jsonl(manifest_path, manifest_rows)
    write_jsonl(chunks_path, chunk_rows)

    lines = [
        "# Material catalog",
        "",
        f"- Config: `{relative_to_repo(config_path)}`",
        f"- Indexed at: `{utc_now_iso()}`",
        f"- Document count: **{doc_counter}**",
        f"- Chunk count: **{chunk_counter}**",
        f"- SQLite FTS enabled: **{fts_enabled}**",
        "",
        "## By category",
    ]
    for category, count in sorted(counts_by_category.items()):
        lines.append(f"- `{category}`: {count}")
    if not counts_by_category:
        lines.append("- None")

    lines.extend(["", "## By file type"])
    for suffix, count in sorted(counts_by_type.items()):
        lines.append(f"- `{suffix}`: {count}")
    if not counts_by_type:
        lines.append("- None")

    lines.extend(["", "## By extraction status"])
    for status, count in sorted(counts_by_status.items()):
        lines.append(f"- `{status}`: {count}")
    if not counts_by_status:
        lines.append("- None")

    lines.extend(["", "## Files needing attention"])
    attention = [row for row in manifest_rows if row.get("extraction_status") in {"caption_needed", "partial", "unsupported", "failed"}]
    if attention:
        for row in attention:
            detail = "; ".join(row.get("warnings", [])) or row.get("extraction_status", "")
            lines.append(f"- `{row['source_path']}` ({row['extraction_status']}): {detail}")
    else:
        lines.append("- None")

    lines.extend(["", "## Warnings"])
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- None")

    write_text(catalog_markdown, "\n".join(lines) + "\n")

    print(f"Indexed {doc_counter} documents into {relative_to_repo(db_path)}")
    print(f"Wrote manifest to {relative_to_repo(manifest_path)}")
    print(f"Wrote chunks to {relative_to_repo(chunks_path)}")
    print(f"Wrote catalog to {relative_to_repo(catalog_markdown)}")
    if warnings:
        print(f"Warnings: {len(warnings)}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
