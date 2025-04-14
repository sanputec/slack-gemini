from flask import Flask, request
import os
import requests
import google.generativeai as genai

app = Flask(__name__)

# Gemini Flash
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")

memory_dict = {}
max_context_length = 10
recent_event_ids = set()

def reply_to_slack(channel, text):
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "channel": channel,
        "text": text
    }
    requests.post("https://slack.com/api/chat.postMessage", headers=headers, json=data)

@app.route("/", methods=["POST"])
def slack_events():
    data = request.get_json()

    if data.get("type") == "url_verification":
        return data.get("challenge"), 200, {"Content-Type": "text/plain"}

    event_id = data.get("event_id")
    if event_id in recent_event_ids:
        return "Duplicate event, ignored.", 200
    recent_event_ids.add(event_id)
    if len(recent_event_ids) > 100:
        recent_event_ids.pop()

    if "event" in data:
        event = data["event"]
        if event.get("type") == "message" and event.get("channel_type") == "im" and not event.get("bot_id"):
            user_input = event.get("text")
            channel = event.get("channel")
            user_id = event.get("user")

            if user_input.strip().lower() == "/reset":
                memory_dict[user_id] = []
                reply_to_slack(channel, "記憶已清除 ✅")
                return "OK", 200

            history = memory_dict.get(user_id, [])
            history.append({"role": "user", "parts": [user_input]})

            try:
                convo = model.start_chat(history=history)
                reply = convo.send_message(user_input).text
                history.append({"role": "model", "parts": [reply]})
                reply_to_slack(channel, reply)
            except Exception as e:
                reply_to_slack(channel, f"出錯了：{str(e)}")

            if len(history) > max_context_length:
                history = history[-max_context_length:]
            memory_dict[user_id] = history

    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
