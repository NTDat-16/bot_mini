import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

DOCS_DIR = Path(__file__).resolve().parent / "docs"
ASSISTANT_NAME = "OptiBot Mini Clone"
SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply."""


def get_client():
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in environment or .env file")

    return OpenAI(api_key=api_key)


def list_markdown_files(docs_dir=DOCS_DIR):
    docs_dir = Path(docs_dir)
    if not docs_dir.exists():
        return []

    return sorted(path for path in docs_dir.glob("*.md") if path.is_file())


def get_or_create_vector_store(client, vector_store_id=None, name="OptiSigns Docs"):
    vector_store_id = vector_store_id or os.getenv("OPENAI_VECTOR_STORE_ID")
    if vector_store_id:
        return client.vector_stores.retrieve(vector_store_id)

    return client.vector_stores.create(name=name)


def upload_files(files, vector_store_id, previous_files=None):
    client = get_client()
    previous_files = previous_files or {}
    uploaded = []

    for path in files:
        path = Path(path)
        previous = previous_files.get(path.name)
        if previous and previous.get("vector_file_id"):
            try:
                client.vector_stores.files.delete(
                    vector_store_id=vector_store_id,
                    file_id=previous["vector_file_id"],
                )
            except Exception:
                pass

        with path.open("rb") as f:
            vector_file = client.vector_stores.files.upload_and_poll(
                vector_store_id=vector_store_id,
                file=f,
            )
        uploaded.append(
            {
                "filename": path.name,
                "path": str(path),
                "vector_file_id": vector_file.id,
                "status": getattr(vector_file, "status", None),
            }
        )

    return uploaded


def upload_all(docs_dir=DOCS_DIR, vector_store_id=None, vector_store_name="OptiSigns Docs"):
    files = list_markdown_files(docs_dir)
    if not files:
        raise RuntimeError(f"No markdown files found in {Path(docs_dir).resolve()}")

    client = get_client()
    vector_store = get_or_create_vector_store(
        client,
        vector_store_id=vector_store_id,
        name=vector_store_name,
    )

    uploaded = upload_files(files, vector_store.id)

    return {
        "vector_store_id": vector_store.id,
        "uploaded": uploaded,
    }


def create_or_update_assistant(vector_store_id, model="gpt-4.1-mini", assistant_id=None):
    client = get_client()
    assistant_id = assistant_id or os.getenv("OPENAI_ASSISTANT_ID")
    payload = {
        "name": ASSISTANT_NAME,
        "instructions": SYSTEM_PROMPT,
        "model": model,
        "tools": [{"type": "file_search"}],
        "tool_resources": {"file_search": {"vector_store_ids": [vector_store_id]}},
    }

    if assistant_id:
        return client.beta.assistants.update(assistant_id, **payload)

    return client.beta.assistants.create(**payload)
