import requests
import json

# Endpoint mặc định của 9Router local
API_URL = "http://127.0.0.1:20128/v1/chat/completions"

# API Key lấy từ Dashboard của 9Router (Next.js server local không bắt buộc API Key hợp lệ, có thể điền bất kỳ chuỗi nào)
API_KEY = "9router-local-key"

# Định nghĩa header
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Chọn model bạn muốn dùng (Ví dụ thông qua Kiro AI hoặc OpenCode Free)
# Nếu bạn chưa cấu hình Provider nào, hãy truy cập http://localhost:20128 để kết nối Kiro AI / OpenCode Free trước nhé!
payload = {
    "model": "kr/claude-sonnet-4.5",  # Tên model qua Kiro AI
    "messages": [
        {"role": "user", "content": "Xin chào! Bạn là mô hình AI nào đang chạy qua 9Router?"}
    ],
    "temperature": 0.7
}

print("=== Đang gửi yêu cầu test đến 9Router ===")
try:
    response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    if response.status_code == 200:
        result = response.json()
        print("\n[Kết quả từ AI]:")
        print(result["choices"][0]["message"]["content"])
    else:
        print(f"Lỗi: HTTP {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Lỗi kết nối đến 9Router: {e}")
    print("Vui lòng đảm bảo 9Router đã được khởi chạy và bạn đã kết nối Provider trong Dashboard (http://localhost:20128)")
