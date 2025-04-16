import os
import logging
from flask import Flask, request, jsonify
from memory import Memory
from draw import generate_image
import google.generativeai as genai

app = Flask(__name__)
memory = Memory()

logging.basicConfig(level=logging.INFO)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-pro")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

@app.route("/healthz", methods=["GET"])
def health_check():
    return "OK", 200

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.get_json()
    logging.info(f"[EVENT] 收到 Slack events：{data}")

    if "challenge" in data:
        return data["challenge"], 200, {"Content-Type": "text/plain"}

    event = data.get("event", {})
    if event.get("type") == "app_mention":
        user = event["user"]
        text = event["text"]
        thread_ts = event.get("thread_ts", event["ts"])

        history = memory.get(user)
        history.append({"role": "user", "parts": [text]})
        response = model.generate_content(history)
        memory.update(user, {"role": "model", "parts": [response.text]})

        from slack_sdk import WebClient
        client = WebClient(token=SLACK_BOT_TOKEN)
        client.chat_postMessage(
            channel=event["channel"],
            text=response.text,
            thread_ts=thread_ts
        )

    return "", 200

@app.route("/slack/commands", methods=["POST"])
def slack_commands():
    command = request.form.get("command")
    text = request.form.get("text", "")
    user_id = request.form.get("user_id")

    if command == "/reset":
        memory.clear(user_id)
        return jsonify({"text": "✅ 記憶已清除"})

    elif command == "/draw":
        if not text:
            return jsonify({"text": "請輸入提示文字，例如 `/draw 一隻柴犬在宇宙中`"})
        image_url = generate_image(text)
        return jsonify({"text": f"🎨 這是你要的圖：{image_url}"})

    return jsonify({"text": "❌ 未知指令"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
