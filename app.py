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
seen_events_lock = threading.Lock()
greeted_users = set()

logging.basicConfig(level=logging.INFO)

# 日誌中記錄所有請求
@app.before_request
def log_all_requests():
    logging.info(f"[REQ] {request.method} {request.path}")

# 根路由避免 404
@app.route("/", methods=["GET"])
def root():
    return "✅ Slack Gemini Bot is running!", 200

# 健康檢查
@app.route("/healthz", methods=["GET"])
def health_check():
    return "OK", 200

# 初始化 Gemini 模型與 Slack client
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
client = WebClient(token=SLACK_BOT_TOKEN)

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.get_json()
    logging.info(f"[EVENT] 收到 Slack events：{data}")

    # Slack 驗證
    if "challenge" in data:
        return data["challenge"], 200, {"Content-Type": "text/plain"}

    event = data.get("event", {})
    event_id = data.get("event_id")
    event_type = event.get("type")

    # 避免重複處理事件
    with seen_events_lock:
        if event_id in seen_events:
            logging.info(f"[SKIP] 已處理過事件 {event_id}")
            return "", 200
        seen_events.add(event_id)

    # 忽略 bot 自己
    if event.get("bot_id"):
        return "", 200

    if event_type == "app_mention":
        user = event["user"]
        text = event["text"]
        channel = event["channel"]
        thread_ts = event.get("thread_ts", event["ts"])
        threading.Thread(target=handle_reply_async, args=(user, text, channel, thread_ts)).start()

    elif event_type == "message" and event.get("channel_type") == "im":
        user = event["user"]
        text = event.get("text", "")
        channel = event["channel"]

        if user not in greeted_users:
            greeted_users.add(user)
            client.chat_postMessage(channel=channel, text="你好！有什麼可以幫忙的嗎？")
        else:
            threading.Thread(target=handle_reply_async, args=(user, text, channel, None)).start()

    return "", 200

def handle_reply_async(user, text, channel, thread_ts=None):
    try:
        history = memory.get(user)
        history.append({"role": "user", "parts": [text]})
        response = model.generate_content(history)
        memory.update(user, {"role": "model", "parts": [response.text]})
        reply = response.text
    except Exception as e:
        logging.exception("[ERROR] Gemini 回應錯誤")
        reply = f"⚠️ Gemini 回覆失敗：{str(e)}"

    client.chat_postMessage(channel=channel, text=reply, thread_ts=thread_ts)

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
    try:
        result = generate_image(prompt)
        requests.post(response_url, json={"text": f"🎨 這是你要的圖：{result}"})
    except Exception as e:
        logging.exception("[ERROR] 生成圖片失敗")
        requests.post(response_url, json={"text": f"⚠️ 生成圖片失敗：{str(e)}"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
