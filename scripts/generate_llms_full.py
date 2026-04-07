"""Generate docs/llms-full.txt by concatenating documentation Markdown files."""
from __future__ import annotations

import pathlib

# Ordered list of doc files to include (exclude README.md, agent-playbook.md)
DOC_FILES: list[str] = [
    "index.md",
    "installation.md",
    "quickstart.md",
    "connection.md",
    "api.md",
    "types.md",
    "errors.md",
    "architecture.md",
    "testing.md",
    "faq.md",
]


def main() -> None:
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    docs_dir = repo_root / "docs"
    output = docs_dir / "llms-full.txt"

    sections: list[str] = []
    for filename in DOC_FILES:
        filepath = docs_dir / filename
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8").strip()
            sections.append(content)

    _ = output.write_text("\n\n---\n\n".join(sections) + "\n", encoding="utf-8")
    print(f"Generated {output} ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
