import os
import re
from pathlib import Path

from markdownify import markdownify

DOCS_DIR = Path(__file__).resolve().parent / "docs"


def html_to_markdown(html):
    return markdownify(html, heading_style="ATX").strip() + "\n"


def safe_filename(title):
    filename = re.sub(r"[^\w\s.-]", "", title, flags=re.UNICODE)
    filename = re.sub(r"\s+", "_", filename.strip())
    return filename[:120] or "untitled"


def save_markdown(title, markdown, source_url=None, docs_dir=DOCS_DIR):
    docs_dir = Path(docs_dir)
    os.makedirs(docs_dir, exist_ok=True)

    filename = safe_filename(title) + ".md"
    path = docs_dir / filename
    front_matter = f"# {title}\n\n"
    if source_url:
        front_matter += f"Article URL: {source_url}\n\n"

    with path.open("w", encoding="utf-8") as f:
        f.write(front_matter)
        f.write(markdown)

    return path
