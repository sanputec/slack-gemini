import google.generativeai as genai

def generate_image(prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ 圖片生成失敗：{str(e)}"
