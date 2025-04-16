import google.generativeai as genai

def generate_image(prompt):
    model = genai.GenerativeModel("gemini-pro-vision")
    response = model.generate_content(prompt)
    return response.text  # Gemini image URL or description (需視 API 回傳內容調整)
