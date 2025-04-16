import google.generativeai as genai

def generate_image(prompt):
    model = genai.GenerativeModel("gemini-pro-vision")
    response = model.generate_content(prompt)
    return response.text  # 視回傳內容調整
