import google.generativeai as genai

def generate_image(prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text  # Gemini 回傳可能是一段描述
    except Exception as e:
        return f"⚠️ 圖片生成失敗：{str(e)}"
