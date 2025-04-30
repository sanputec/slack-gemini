# draw.py

def generate_image(prompt: str) -> str:
    # 利用 fakeimg.pl 做出一張帶文字的假圖片
    # 適合 Slack Bot 測試與展示
    encoded = prompt.replace(" ", "+")
    return f"https://fakeimg.pl/600x400/?text={encoded}&font=noto"
