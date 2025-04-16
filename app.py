import os
import json
from flask import Flask, request, jsonify
from memory import Memory
from draw.py import generate_image
import google.generativeai as genai

app = Flask(__name__)
memory = Memory()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-pro")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})
    
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
    text = request.form.get("text", "")
    command = request.form.get("command")
    user_id = request.form.get("user_id")
    channel_id = request.form.get("channel_id")

    if command == "/reset":
        memory.clear(user_id)
        return jsonify({"text": "✅ 記憶已重設"})

    elif command == "/draw":
        image_url = generate_image(text)
        return jsonify({"text": f"🎨 這是你要的圖：{image_url}"})

    return jsonify({"text": "未知指令"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
