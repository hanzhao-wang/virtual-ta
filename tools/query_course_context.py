from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.common import relative_to_repo, repo_path, resolve_config, write_json
from lib.retrieval import retrieve


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve the most relevant local course chunks for a question.")
    parser.add_argument("--config", help="Path to config TOML file.")
    parser.add_argument("--question", required=True, help="Question to retrieve context for.")
    parser.add_argument("--top-k", type=int, help="Number of chunks to return.")
    parser.add_argument("--out", help="Optional output JSON path.")
    args = parser.parse_args()

    _, config = resolve_config(args.config)
    cache_cfg = config["cache"]
    retrieval_cfg = config["retrieval"]

    db_path = repo_path(cache_cfg["sqlite_index"])
    chunks_path = repo_path(cache_cfg["chunks"])
    top_k = args.top_k or int(retrieval_cfg.get("default_top_k", 8))

    payload = retrieve(args.question, db_path=db_path, chunks_path=chunks_path, top_k=top_k)

    if args.out:
        out_path = repo_path(args.out)
        write_json(out_path, payload)
        print(f"Wrote retrieval payload to {relative_to_repo(out_path)}")
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
