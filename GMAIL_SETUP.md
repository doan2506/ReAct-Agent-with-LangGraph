# Thiết lập Gmail Agent (read-only)

Agent này đọc và tổng hợp các email **chưa đọc** trong Gmail của bạn. Nó chỉ có
quyền **read-only** — không gửi, không xoá, không đánh dấu đã đọc.

## 1. Cài dependencies

```bash
pip install -e .
# hoặc dùng uv:
uv sync
```

## 2. Tạo OAuth credentials trên Google Cloud

1. Vào <https://console.cloud.google.com/> → tạo một **project** mới (hoặc chọn project sẵn có).
2. Vào **APIs & Services → Library**, tìm **Gmail API** và bấm **Enable**.
3. Vào **APIs & Services → OAuth consent screen**:
   - Chọn **External**, điền tên app, email hỗ trợ.
   - Ở mục **Scopes** có thể để trống (không cần thêm ở bước này).
   - Ở mục **Test users**, thêm chính email Gmail bạn muốn đọc (ví dụ `your-email@gmail.com`).
     Khi app ở chế độ *Testing*, chỉ các test user mới đăng nhập được.
4. Vào **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - **Application type**: chọn **Desktop app**.
   - Bấm **Create**, rồi **Download JSON**.
5. Đổi tên file vừa tải thành `credentials.json` và đặt vào thư mục gốc của project
   (cùng cấp với `pyproject.toml`).

> `credentials.json` và `token.json` đã được thêm vào `.gitignore` — **không commit** chúng.

## 3. Tạo file `.env` và điền API key cho LLM

```bash
cp .env.example .env
```

Model mặc định là `google_genai/gemini-flash-latest`, nên cần **`GOOGLE_API_KEY`**.
Lấy key miễn phí tại <https://aistudio.google.com/app/apikey> rồi điền vào `.env`:

```
GOOGLE_API_KEY=...
```

> `.env` đã nằm trong `.gitignore` — key thật của bạn **không bị commit**.
> Nếu muốn đổi sang model khác (Anthropic/OpenAI...), sửa biến `MODEL` và điền key tương ứng.

## 5. Đăng nhập OAuth (chạy 1 lần)

Chạy script sau, một cửa sổ trình duyệt sẽ mở ra để bạn đăng nhập và cấp quyền
**"Read all resources and their metadata"**:

```bash
python authorize_gmail.py
```

Sau khi đồng ý, file `token.json` được tạo tự động và các lần sau sẽ không cần
đăng nhập lại. (Muốn đăng nhập lại từ đầu: xoá `token.json` rồi chạy lại lệnh trên.)

## 6. Chạy agent

```bash
langgraph dev
```

Mở LangGraph Studio, rồi thử:

- "Tổng hợp giúp tôi các email chưa đọc"
- "Có email nào cần trả lời gấp không?"
- "Tóm tắt email chưa đọc trong 2 ngày qua"

## Cấu hình (tùy chọn)

Có thể chỉnh trong `Context` ([src/react_agent/context.py](src/react_agent/context.py))
hoặc qua biến môi trường:

| Biến môi trường          | Mặc định           | Ý nghĩa                              |
| ------------------------ | ------------------ | ------------------------------------ |
| `GMAIL_CREDENTIALS_FILE` | `credentials.json` | Đường dẫn OAuth client secrets       |
| `GMAIL_TOKEN_FILE`       | `token.json`       | Nơi lưu token sau khi đăng nhập      |
| `MAX_EMAILS`             | `25`               | Số email tối đa lấy về mỗi lần search |
| `MODEL`                  | `google_genai/gemini-flash-latest` | Model LLM dùng cho agent |
