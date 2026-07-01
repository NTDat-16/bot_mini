# OptiBot Mini Clone

One-shot job that scrapes OptiSigns help articles, normalizes them to Markdown, uploads only changed files to an OpenAI Vector Store, and creates/updates an Assistant named `OptiBot Mini Clone`.

## Setup

```powershell
pip install -r bot_mini/requirements.txt
copy .env.sample .env
```

Set `OPENAI_API_KEY` in `.env`. Optional after first run: set `OPENAI_VECTOR_STORE_ID` and `OPENAI_ASSISTANT_ID` to reuse the same resources.

## Run Locally

```powershell
python bot_mini/main.py --limit 30 --ask "How do I add a YouTube video?"
```

The job writes Markdown to `bot_mini/docs`, state to `bot_mini/logs/state.json`, and the latest run artifact to `bot_mini/logs/last_run.json`. It logs `added`, `updated`, `skipped`, `uploaded`, and `estimated_chunks`.

## Docker

```powershell
docker build -t optibot-mini .
docker run --rm -e OPENAI_API_KEY=sk-... optibot-mini
```

## Chunking

OpenAI File Search handles chunking automatically for uploaded Markdown. The job logs an `estimated_chunks` count using about 800 words per chunk so reviewers can verify ingestion volume from the run artifact.

## Daily Job

Recommended deployment: Render Cron Job, scheduled `0 12 * * *` UTC. Use Docker runtime, add `OPENAI_API_KEY`, and after the first successful run copy the printed `OPENAI_VECTOR_STORE_ID` / `OPENAI_ASSISTANT_ID` into Render environment variables. Last run logs: add your Render run log URL here. Screenshot: add the Playground/Assistant answer screenshot here.
