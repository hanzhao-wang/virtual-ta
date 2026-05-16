from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from lib.common import ensure_dir, relative_to_repo, repo_path, resolve_config, write_text
from lib.extract import IMAGE_EXTENSIONS, caption_path_for_image, is_caption_stub


def iter_image_files(material_roots: dict[str, list[str]]):
    seen: set[Path] = set()
    for roots in material_roots.values():
        for root_str in roots:
            root = repo_path(root_str)
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield resolved


def needs_caption(image_path: Path, caption_root: Path, *, overwrite: bool) -> bool:
    caption_path = caption_path_for_image(image_path, caption_root)
    if overwrite:
        return True
    if not caption_path.exists():
        return True
    return is_caption_stub(caption_path.read_text(encoding="utf-8", errors="ignore"))


def build_prompt(image_path: Path, base_prompt: str) -> str:
    return f"""\
{base_prompt}

Image path: `{relative_to_repo(image_path)}`

Output format:
- Start with a one-sentence description.
- Include bullet points for visible text/labels/formulas and important visual structure.
- Include a final `Course concept:` line.
- If text is unreadable, say it is unreadable rather than guessing.
"""


def caption_one(
    image_path: Path,
    *,
    caption_root: Path,
    codex_bin: str,
    model: str,
    prompt: str,
    dry_run: bool,
) -> Path:
    caption_path = caption_path_for_image(image_path, caption_root)
    ensure_dir(caption_path.parent)
    if dry_run:
        return caption_path

    command = [
        codex_bin,
        "exec",
        "--sandbox",
        "read-only",
        "--skip-git-repo-check",
        "--model",
        model,
        "--image",
        str(image_path),
        "-o",
        str(caption_path),
        build_prompt(image_path, prompt),
    ]
    subprocess.run(command, cwd=repo_path("."), check=True, stdin=subprocess.DEVNULL)
    content = caption_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not content:
        raise RuntimeError(f"Codex wrote an empty caption for {relative_to_repo(image_path)}")
    write_text(caption_path, content + "\n")
    return caption_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate image captions with Codex vision for local retrieval indexing.")
    parser.add_argument("--config", help="Path to config TOML file.")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate captions even if they already exist.")
    parser.add_argument("--dry-run", action="store_true", help="List images that would be captioned without calling Codex.")
    parser.add_argument("--limit", type=int, help="Maximum number of images to caption.")
    args = parser.parse_args()

    codex_bin = shutil.which("codex")
    if codex_bin is None and not args.dry_run:
        raise SystemExit("Could not find `codex` on PATH.")

    _, config = resolve_config(args.config)
    cache_cfg = config["cache"]
    caption_cfg = config.get("captioning", {})
    caption_root = repo_path(cache_cfg.get("image_caption_root", "cache/image_captions"))
    max_images = args.limit or int(caption_cfg.get("max_images_per_run", 50))
    overwrite = args.overwrite or bool(caption_cfg.get("overwrite_existing", False))
    model = caption_cfg.get("model", "gpt-5.4")
    prompt = caption_cfg.get(
        "prompt",
        "Write a concise retrieval caption for this course image. Return plain Markdown only.",
    )

    candidates = [
        image_path
        for image_path in iter_image_files(config["materials"])
        if needs_caption(image_path, caption_root, overwrite=overwrite)
    ][:max_images]

    if not candidates:
        print("No image captions needed.")
        return 0

    for image_path in candidates:
        caption_path = caption_one(
            image_path,
            caption_root=caption_root,
            codex_bin=codex_bin or "codex",
            model=model,
            prompt=prompt,
            dry_run=args.dry_run,
        )
        action = "Would caption" if args.dry_run else "Captioned"
        print(f"{action} {relative_to_repo(image_path)} -> {relative_to_repo(caption_path)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
