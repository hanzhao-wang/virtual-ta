from __future__ import annotations

import math
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from .common import read_jsonl, tokenize


def load_chunks(chunks_path: Path) -> list[dict[str, Any]]:
    return read_jsonl(chunks_path)


def build_fts_query(question: str) -> str:
    tokens = []
    seen = set()
    for token in tokenize(question):
        if token not in seen:
            tokens.append(token)
            seen.add(token)
        if len(tokens) >= 12:
            break

    if not tokens:
        return '""'
    return " OR ".join(tokens)


def result_from_row(row: sqlite3.Row, *, retrieval_mode: str) -> dict[str, Any]:
    score = float(row["rank"])
    normalized_score = 1.0 / (1.0 + max(score, 0.0))
    content = row["content"]
    return {
        "chunk_id": row["chunk_id"],
        "doc_id": row["doc_id"],
        "category": row["category"],
        "source_path": row["source_path"],
        "file_type": row["file_type"],
        "title": row["title"],
        "chunk_index": row["chunk_index"],
        "locator_type": row["locator_type"],
        "locator": row["locator"],
        "extraction_status": row["extraction_status"],
        "excerpt": content[:1200],
        "preview": row["preview"] or content[:280],
        "score": round(normalized_score, 6),
        "retrieval_mode": retrieval_mode,
    }


def retrieve_with_sqlite(db_path: Path, question: str, top_k: int) -> list[dict[str, Any]]:
    query = build_fts_query(question)
    if not db_path.exists():
        return []

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        sql = '''
            SELECT
                c.chunk_id,
                c.doc_id,
                c.category,
                c.source_path,
                c.file_type,
                c.title,
                c.chunk_index,
                c.locator_type,
                c.locator,
                c.extraction_status,
                c.content,
                snippet(chunks_fts, 2, '<<', '>>', ' … ', 24) AS preview,
                bm25(chunks_fts) AS rank
            FROM chunks_fts
            JOIN chunks c ON c.chunk_id = chunks_fts.chunk_id
            WHERE chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        '''
        rows = connection.execute(sql, (query, top_k * 3)).fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        connection.close()

    results = [result_from_row(row, retrieval_mode="sqlite_fts") for row in rows]
    return rerank_results(question, results)[:top_k]


def retrieve_with_fallback(chunks_path: Path, question: str, top_k: int) -> list[dict[str, Any]]:
    chunks = load_chunks(chunks_path)
    if not chunks:
        return []

    query_tokens = tokenize(question)
    if not query_tokens:
        return []

    doc_freq: Counter[str] = Counter()
    tokenized_chunks = []

    for chunk in chunks:
        tokens = tokenize(chunk.get("text", ""))
        tokenized_chunks.append(tokens)
        doc_freq.update(set(tokens))

    total_docs = max(len(chunks), 1)
    results = []

    for chunk, tokens in zip(chunks, tokenized_chunks):
        counts = Counter(tokens)
        score = 0.0
        for token in query_tokens:
            tf = counts[token]
            if tf == 0:
                continue
            idf = math.log(1.0 + total_docs / (1.0 + doc_freq[token]))
            score += tf * idf

        lower_question = question.lower()
        lower_text = chunk.get("text", "").lower()
        if lower_question in lower_text:
            score += 5.0

        title = chunk.get("title", "")
        if lower_question in title.lower():
            score += 2.0

        if score > 0:
            text = chunk.get("text", "")
            results.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "doc_id": chunk["doc_id"],
                    "category": chunk["category"],
                    "source_path": chunk["source_path"],
                    "file_type": chunk.get("file_type", ""),
                    "title": title,
                    "chunk_index": chunk.get("chunk_index", 0),
                    "locator_type": chunk.get("locator_type", "document"),
                    "locator": chunk.get("locator", "document"),
                    "extraction_status": chunk.get("extraction_status", "indexed"),
                    "excerpt": text[:1200],
                    "preview": text[:280],
                    "score": round(score, 6),
                    "retrieval_mode": "json_fallback",
                }
            )

    return rerank_results(question, results)[:top_k]


def rerank_results(question: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    question_lower = question.lower()
    category_bonus = {
        "lecture": "lectures",
        "slide": "lectures",
        "tutorial": "tutorials",
        "question book": "tutorials",
        "assignment": "assignments",
        "project": "assignments",
        "quiz": "quizzes",
        "exercise": "exercises",
        "exam": "exercises",
    }

    adjusted = []
    for row in results:
        score = float(row["score"])
        category = row.get("category", "")
        for trigger, target_category in category_bonus.items():
            if trigger in question_lower and category == target_category:
                score += 0.15
        if row.get("extraction_status") == "indexed":
            score += 0.02
        adjusted.append({**row, "score": round(score, 6)})

    adjusted.sort(key=lambda item: item["score"], reverse=True)

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, int]] = set()
    for row in adjusted:
        key = (
            row["source_path"],
            row.get("locator_type", "document"),
            str(row.get("locator", "document")),
            int(row.get("chunk_index", 0)),
        )
        if key not in seen:
            deduped.append({**row, "score": min(float(row.get("score", 0.0)), 1.0)})
            seen.add(key)
    return deduped


def retrieve(
    question: str,
    db_path: Path,
    chunks_path: Path,
    top_k: int = 8,
) -> dict[str, Any]:
    results = retrieve_with_sqlite(db_path, question, top_k)
    if not results:
        results = retrieve_with_fallback(chunks_path, question, top_k)
    return {
        "question": question,
        "top_k": top_k,
        "result_count": len(results),
        "results": results,
    }
