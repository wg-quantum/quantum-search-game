#!/usr/bin/env python3
"""Publish this repo to a Hugging Face Docker Space (free CPU tier).

    HF_TOKEN=hf_... python deploy/hf_space.py <owner>/<space-name>

The upload is staged into a temporary directory first, holding exactly what the
Dockerfile needs plus the Space-flavoured README that carries the YAML
frontmatter Spaces requires. Everything else — .venv, node_modules, dist,
.env — never leaves the machine, and no token is ever written to a git remote.

Pass IBM_QUANTUM_TOKEN as well to store it as a Space secret in the same run,
which is what turns 実機モード on for the deployed instance.
"""

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The Dockerfile builds the frontend from source, so frontend/ ships too.
INCLUDE = (
    "Dockerfile",
    ".dockerignore",
    "backend/requirements.txt",
    "backend/app",
    "backend/data",
    "frontend/package.json",
    "frontend/pnpm-lock.yaml",
    "frontend/index.html",
    "frontend/vite.config.ts",
    "frontend/tsconfig.json",
    "frontend/tsconfig.app.json",
    "frontend/tsconfig.node.json",
    "frontend/src",
    "frontend/public",
)

# Build artefacts and environments only. Frontend test files ship even though
# the image does not run them, so that `pnpm build` in the Space sees exactly
# the tree that was verified locally.
EXCLUDE_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "node_modules",
    "dist",
    ".DS_Store",
    "static",  # the frontend build gets copied in by the Dockerfile
}
EXCLUDE_SUFFIXES = (".pyc",)


def _ignore(directory: str, names: list[str]) -> set[str]:
    del directory
    return {
        name
        for name in names
        if name in EXCLUDE_NAMES or name.endswith(EXCLUDE_SUFFIXES)
    }


def stage(destination: Path) -> list[str]:
    """Copy the deployable subset of the repo into destination."""
    copied: list[str] = []
    for relative in INCLUDE:
        source = ROOT / relative
        if not source.exists():
            raise SystemExit(f"missing from the repo: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, ignore=_ignore)
        else:
            shutil.copy2(source, target)
        copied.append(relative)

    # Spaces read configuration from README.md frontmatter, so the project
    # README is replaced rather than shipped.
    shutil.copy2(ROOT / "deploy" / "space-README.md", destination / "README.md")
    copied.append("README.md (from deploy/space-README.md)")
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("space", help="target Space, e.g. yourname/quantum-wordle")
    parser.add_argument(
        "--private", action="store_true", help="create the Space as private"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="stage the upload and list it without contacting Hugging Face",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="hf-space-") as tmp:
        staging = Path(tmp)
        for entry in stage(staging):
            print(f"  staged {entry}")

        if args.dry_run:
            total = sum(f.stat().st_size for f in staging.rglob("*") if f.is_file())
            print(f"\ndry run: {total / 1024:.0f} KiB would be uploaded to {args.space}")
            return 0

        token = os.environ.get("HF_TOKEN", "").strip()
        if not token:
            print(
                "HF_TOKEN is not set. Create one with write access at "
                "https://huggingface.co/settings/tokens",
                file=sys.stderr,
            )
            return 2

        try:
            from huggingface_hub import HfApi
        except ImportError:
            print("pip install huggingface_hub", file=sys.stderr)
            return 2

        api = HfApi(token=token)
        api.create_repo(
            repo_id=args.space,
            repo_type="space",
            space_sdk="docker",
            private=args.private,
            exist_ok=True,
        )

        ibm_token = os.environ.get("IBM_QUANTUM_TOKEN", "").strip()
        if ibm_token:
            for key in (
                "IBM_QUANTUM_INSTANCE",
                "IBM_QUANTUM_CHANNEL",
                "IBM_QUANTUM_BACKEND",
                "IBM_QUANTUM_SHOTS",
                "IBM_QUANTUM_MAX_JOBS_PER_HOUR",
                "IBM_QUANTUM_MAX_JOBS_PER_DAY",
            ):
                value = os.environ.get(key, "").strip()
                if value:
                    api.add_space_variable(repo_id=args.space, key=key, value=value)
            api.add_space_secret(
                repo_id=args.space, key="IBM_QUANTUM_TOKEN", value=ibm_token
            )
            print("  stored IBM_QUANTUM_TOKEN as a Space secret")
        else:
            print("  IBM_QUANTUM_TOKEN not set: deploying simulator-only")

        api.upload_folder(
            folder_path=str(staging),
            repo_id=args.space,
            repo_type="space",
            commit_message="deploy quantum-wordle",
            delete_patterns=["*"],  # mirror: drop remote files we no longer ship
        )
        print(f"\nhttps://huggingface.co/spaces/{args.space}")
        print("The Space builds the Docker image now; watch its Logs tab.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
