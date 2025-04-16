import os
import logging
import threading
import requests
from flask import Flask, request, jsonify
from memory import Memory
from draw import generate_image
import google.generativeai as genai
from slack_sdk import WebClient

app = Flask(__name__)
memory = Memory()
seen_events = set()
greeted_users = set()

logging.basicConfig(level=logging.INFO)

@app.before_request
def log_all_requests():
    logging.info(f"[REQ] {request.method} {request.path}")

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-pro")
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
    event_id = data.get("event_id")
    event_type = event.get("type")

    if event_id in seen_events:
        logging.info(f"[SKIP] 已處理過事件 {event_id}")
        return "", 200
    seen_events.add(event_id)

    client = WebClient(token=SLACK_BOT_TOKEN)

    if event_type == "app_mention":
        user = event["user"]
        text = event["text"]
        channel = event["channel"]
        thread_ts = event.get("thread_ts", event["ts"])

        client.chat_postMessage(channel=channel, text="💬 處理中，請稍等...", thread_ts=thread_ts)
        threading.Thread(target=handle_reply_async, args=(user, text, channel, thread_ts)).start()

    elif event_type == "message" and event.get("channel_type") == "im":
        user = event["user"]
        text = event.get("text", "")
        channel = event["channel"]

        if user not in greeted_users:
            greeted_users.add(user)
            reply_text = "你好！有什麼可以幫忙的嗎？"
            client.chat_postMessage(channel=channel, text=reply_text)
        else:
            client.chat_postMessage(channel=channel, text="💬 處理中，請稍等...")
            threading.Thread(target=handle_reply_async, args=(user, text, channel, None)).start()

    return "", 200

def handle_reply_async(user, text, channel, thread_ts=None):
    from slack_sdk import WebClient
    client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

    history = memory.get(user)
    history.append({"role": "user", "parts": [text]})
    response = model.generate_content(history)
    memory.update(user, {"role": "model", "parts": [response.text]})

    client.chat_postMessage(channel=channel, text=response.text, thread_ts=thread_ts)

@app.route("/slack/commands", methods=["POST"])
def slack_commands():
    command = request.form.get("command")
    text = request.form.get("text", "")
    user_id = request.form.get("user_id")
    response_url = request.form.get("response_url")

    if command == "/reset":
        memory.clear(user_id)
        return jsonify({"text": "✅ 記憶已清除"})

    elif command == "/draw":
        if not text:
            return jsonify({"text": "請輸入提示文字，例如 `/draw 一隻柴犬在宇宙中`"})
        threading.Thread(target=handle_draw_async, args=(text, response_url)).start()
        return jsonify({"text": f"🎨 收到指令了，正在生成圖片中..."})

    return jsonify({"text": "❌ 未知指令"})

def handle_draw_async(prompt, response_url):
    result = generate_image(prompt)
    requests.post(response_url, json={"text": f"🎨 這是你要的圖：{result}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
