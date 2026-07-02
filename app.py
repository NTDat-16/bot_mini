import os

from flask import Flask, jsonify, render_template_string, request

from bot_mini.uploader import get_client
from bot_mini.constants import OPENAI_VECTOR_STORE_ID_ENV, SYSTEM_PROMPT

app = Flask(__name__)

HTML_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>OptiBot Mini Chat</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f4f6fb; color: #111; }
      .app { max-width: 760px; margin: 40px auto; padding: 24px; background: white; border-radius: 16px; box-shadow: 0 16px 48px rgba(0,0,0,.08); }
      h1 { margin: 0 0 16px; font-size: 28px; }
      textarea { width: 100%; min-height: 140px; border: 1px solid #d3d6dc; border-radius: 10px; padding: 12px; font-size: 16px; }
      button { margin-top: 12px; padding: 12px 20px; font-size: 16px; border: none; border-radius: 10px; background: #2563eb; color: white; cursor: pointer; }
      button:disabled { opacity: .6; cursor: not-allowed; }
      .answer { margin-top: 24px; white-space: pre-wrap; background: #f5f7ff; border-radius: 12px; padding: 18px; border: 1px solid #d8e0f6; }
      .footer { margin-top: 22px; color: #555; font-size: 14px; }
    </style>
  </head>
  <body>
    <div class="app">
      <h1>OptiBot Mini Chat</h1>
      <p>Ask a question and OptiBot will answer using the uploaded OptiSigns docs.</p>
      <textarea id="question" placeholder="How do I add a YouTube video?">How do I add a YouTube video?</textarea>
      <button id="send">Send</button>
      <div class="answer" id="answer">Enter a question and click Send.</div>
      <div class="footer">Requires <code>{OPENAI_VECTOR_STORE_ID_ENV}</code> in environment.</div>
    </div>
    <script>
      const send = document.getElementById('send');
      const question = document.getElementById('question');
      const answer = document.getElementById('answer');

      send.onclick = async () => {
        send.disabled = true;
        answer.textContent = 'Loading...';
        try {
          const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question.value.trim() }),
          });
          const payload = await response.json();
          if (response.ok) {
            answer.textContent = payload.answer;
          } else {
            answer.textContent = payload.error || 'Unexpected error';
          }
        } catch (err) {
          answer.textContent = err.message || 'Request failed';
        } finally {
          send.disabled = false;
        }
      };
    </script>
  </body>
</html>"""


def ask_question(question: str, vector_store_id: str) -> str:
    if not question:
        raise ValueError("Question is required")
    client = get_client()
    response = client.responses.create(
        model="gpt-4.1-mini",
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


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(force=True)
    vector_store_id = os.getenv(OPENAI_VECTOR_STORE_ID_ENV)
    if not vector_store_id:
        return jsonify({"error": f"Missing environment variable {OPENAI_VECTOR_STORE_ID_ENV}"}), 400

    try:
        answer = ask_question(data.get('question', ''), vector_store_id)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({"answer": answer})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
