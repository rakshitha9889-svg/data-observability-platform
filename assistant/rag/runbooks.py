from pathlib import Path

RUNBOOK_DIRECTORY = Path(__file__).resolve().parents[2] / "runbooks"


def split_sections(markdown: str) -> list[tuple[str, str]]:
    """Split a runbook into (heading, content) pairs on '## ' headings.

    Lines starting with 'TODO' are dropped, so unfinished template text is
    never indexed. Sections left empty are skipped.
    """
    sections: list[tuple[str, str]] = []
    heading = "Overview"
    lines: list[str] = []

    for line in markdown.splitlines():
        if line.startswith("## "):
            sections.append((heading, "\n".join(lines).strip()))
            heading, lines = line[3:].strip(), []
        elif line.startswith("# ") or line.strip().startswith("TODO"):
            continue
        else:
            lines.append(line)

    sections.append((heading, "\n".join(lines).strip()))

    return [(name, content) for name, content in sections if content]


def load_runbook_chunks(
    directory: Path = RUNBOOK_DIRECTORY,
) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []

    for path in sorted(directory.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue

        text = path.read_text(encoding="utf-8")

        for heading, content in split_sections(text):
            chunks.append(
                {
                    "scenario": path.stem,
                    "source_file": path.name,
                    "heading": heading,
                    "content": f"{path.stem} - {heading}\n{content}",
                }
            )

    return chunks
