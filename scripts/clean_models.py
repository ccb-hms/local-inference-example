"""Deletes the Hugging Face models this project downloads, freeing disk space.

Only removes cache entries matching MODEL_SIZES in model.py (Phi-3.5-*-instruct)
- it won't touch unrelated models in your shared Hugging Face cache.

Usage: uv run python scripts/clean_models.py [--yes]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from huggingface_hub import scan_cache_dir

from local_inference_example.model import MODEL_SIZES

TARGET_REPOS = set(MODEL_SIZES.values())


def main() -> None:
    auto_confirm = "--yes" in sys.argv[1:]

    cache_info = scan_cache_dir()
    matches = [repo for repo in cache_info.repos if repo.repo_id in TARGET_REPOS]

    if not matches:
        print("No cached copies of this project's models found.")
        return

    revisions = [rev for repo in matches for rev in repo.revisions]
    total_size = sum(repo.size_on_disk for repo in matches)

    print("Found cached models:")
    for repo in matches:
        print(f"  {repo.repo_id}  ({repo.size_on_disk_str})")

    if not auto_confirm:
        reply = input(f"\nDelete these ({total_size / 1e9:.2f} GB total)? [y/N] ")
        if reply.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return

    strategy = cache_info.delete_revisions(*(rev.commit_hash for rev in revisions))
    strategy.execute()
    print(f"Freed {strategy.expected_freed_size_str}.")


if __name__ == "__main__":
    main()
