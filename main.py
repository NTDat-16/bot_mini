import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from markdown_converter import (
    DOCS_DIR,
    html_to_markdown,
    save_markdown,
)
from scraper import fetch_articles, get_article_links, scrape_article
from uploader import (
    get_client,
    get_or_create_vector_store,
    upload_all,
    upload_files,
    create_or_update_assistant,
    SYSTEM_PROMPT,
)

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
STATE_PATH = LOGS_DIR / "state.json"
LAST_RUN_PATH = LOGS_DIR / "last_run.json"


def load_state(path=STATE_PATH):
    if not path.exists():
        return {"articles": {}}

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def content_hash(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def estimate_chunks(markdown, chunk_words=800):
    words = markdown.split()
    return max(1, (len(words) + chunk_words - 1) // chunk_words)


def crawl(limit):
    try:
        articles = fetch_articles(limit=limit)
    except Exception:
        links = get_article_links(limit=limit)
        articles = []
        for url in links:
            title, html = scrape_article(url)
            articles.append({"title": title, "url": url, "html": html, "updated_at": None})

    saved = []

    for index, article in enumerate(articles, start=1):
        print(f"[{index}/{len(articles)}] Scraping {article['url']}")
        md = html_to_markdown(article["html"])
        path = save_markdown(article["title"], md, source_url=article["url"])
        saved.append(
            {
                "title": article["title"],
                "url": article["url"],
                "updated_at": article.get("updated_at"),
                "path": path,
                "hash": content_hash(path.read_text(encoding="utf-8")),
                "estimated_chunks": estimate_chunks(path.read_text(encoding="utf-8")),
            }
        )

    return saved


def ask(vector_store_id, question, model):
    client = get_client()
    response = client.responses.create(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=question,
        max_output_tokens=600,
        tools=[
            {
                "type": "file_search",
                "vector_store_ids": [vector_store_id],
            }
        ],
    )
    return response.output_text


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape OptiSigns support docs and upload them to an OpenAI Vector Store."
    )
    parser.add_argument("--limit", type=int, default=30, help="Maximum articles to scrape")
    parser.add_argument("--skip-crawl", action="store_true", help="Only upload existing docs")
    parser.add_argument("--skip-upload", action="store_true", help="Only scrape docs")
    parser.add_argument("--ask", help="Ask a question after uploading")
    parser.add_argument("--model", default="gpt-4.1-mini", help="Model used for assistant and --ask")
    parser.add_argument("--vector-store-id", help="Reuse an existing OpenAI Vector Store")
    parser.add_argument("--assistant-id", help="Update an existing assistant instead of creating one")
    parser.add_argument("--no-assistant", action="store_true", help="Do not create/update an assistant")
    parser.add_argument("--full-upload", action="store_true", help="Upload every Markdown file")
    return parser.parse_args()


def main():
    args = parse_args()
    state = load_state()
    run_log = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "limit": args.limit,
        "added": 0,
        "updated": 0,
        "skipped": 0,
        "uploaded": 0,
        "estimated_chunks": 0,
        "files": [],
    }

    if not args.skip_crawl:
        crawled = crawl(args.limit)
        print(f"Saved {len(crawled)} markdown files to {DOCS_DIR}")
    else:
        crawled = []
        for path in sorted(DOCS_DIR.glob("*.md")):
            crawled.append(
                {
                    "title": path.stem.replace("_", " "),
                    "url": None,
                    "updated_at": None,
                    "path": path,
                    "hash": content_hash(path.read_text(encoding="utf-8")),
                    "estimated_chunks": estimate_chunks(path.read_text(encoding="utf-8")),
                }
            )

    if args.skip_upload:
        save_json(LAST_RUN_PATH, run_log)
        return

    client = get_client()
    vector_store = get_or_create_vector_store(
        client,
        vector_store_id=args.vector_store_id or state.get("vector_store_id"),
        name="OptiSigns Docs",
    )

    previous_articles = state.setdefault("articles", {})
    changed_paths = []
    previous_files = {}

    for item in crawled:
        path = Path(item["path"])
        previous = previous_articles.get(path.name)
        previous_files[path.name] = previous or {}
        status = "skipped"

        if args.full_upload or previous is None:
            status = "added"
            changed_paths.append(path)
            run_log["added"] += 1
        elif previous.get("hash") != item["hash"]:
            status = "updated"
            changed_paths.append(path)
            run_log["updated"] += 1
        else:
            run_log["skipped"] += 1

        run_log["estimated_chunks"] += item["estimated_chunks"]
        run_log["files"].append(
            {
                "filename": path.name,
                "status": status,
                "hash": item["hash"],
                "estimated_chunks": item["estimated_chunks"],
                "article_url": item["url"],
            }
        )

    uploaded = upload_files(changed_paths, vector_store.id, previous_files=previous_files)
    uploaded_by_name = {item["filename"]: item for item in uploaded}

    for item in crawled:
        path = Path(item["path"])
        existing = previous_articles.get(path.name, {})
        uploaded_item = uploaded_by_name.get(path.name)
        previous_articles[path.name] = {
            "hash": item["hash"],
            "article_url": item["url"] or existing.get("article_url"),
            "updated_at": item["updated_at"] or existing.get("updated_at"),
            "vector_file_id": (
                uploaded_item["vector_file_id"]
                if uploaded_item
                else existing.get("vector_file_id")
            ),
        }

    assistant = None
    if not args.no_assistant:
        assistant = create_or_update_assistant(
            vector_store.id,
            model=args.model,
            assistant_id=args.assistant_id or state.get("assistant_id"),
        )
        state["assistant_id"] = assistant.id

    state["vector_store_id"] = vector_store.id
    run_log["vector_store_id"] = vector_store.id
    run_log["assistant_id"] = assistant.id if assistant else state.get("assistant_id")
    run_log["uploaded"] = len(uploaded)
    run_log["completed_at"] = datetime.now(timezone.utc).isoformat()

    save_json(STATE_PATH, state)
    save_json(LAST_RUN_PATH, run_log)

    print(f"Vector store: {vector_store.id}")
    if assistant:
        print(f"Assistant: {assistant.id}")
    print(
        "Delta: "
        f"added={run_log['added']} "
        f"updated={run_log['updated']} "
        f"skipped={run_log['skipped']} "
        f"uploaded={run_log['uploaded']} "
        f"estimated_chunks={run_log['estimated_chunks']}"
    )
    print(f"Run log: {LAST_RUN_PATH}")

    if args.ask:
        print(ask(vector_store.id, args.ask, args.model))


if __name__ == "__main__":
    main()
