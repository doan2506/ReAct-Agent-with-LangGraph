# Gmail & Google Calendar Assistant - ReAct Agent with LangGraph

Dự án này là một **ReAct Agent** (Reasoning + Acting) hiện đại được xây dựng bằng **LangGraph** và **Flask**, hỗ trợ tích hợp với **Gmail API** và **Google Calendar API** để tự động tìm kiếm, đọc, tổng hợp email chưa đọc, tạo bản thảo email nháp (Draft) cho người dùng duyệt, và tự động đặt lịch họp trên Google Calendar.

---

## 🚀 Tính năng chính

- **ReAct Architecture**: Agent tự suy luận (Thought), lựa chọn công cụ (Action) và xử lý kết quả (Observation) qua vòng lặp ReAct của LangGraph.
- **Gmail & Calendar Tools**:
  - `search_emails`: Tìm kiếm email với cú pháp tìm kiếm chuẩn của Gmail (ví dụ: `is:unread`, `newer_than:2d`).
  - `get_email`: Đọc nội dung đầy đủ của một email theo ID.
  - `get_thread`: Đọc toàn bộ luồng hội thoại theo Thread ID.
  - `create_draft`: **(Mới)** Tạo bản thảo email nháp (Draft) để người dùng duyệt trước khi gửi.
  - `schedule_meeting`: **(Mới)** Tự động đặt lịch họp/sự kiện trên Google Calendar.
- **Flask Web UI Dashboard**: Giao diện Web hiện đại (Dark Theme) hiển thị luồng thực thi ReAct theo thời gian thực dạng từng thẻ riêng biệt (`User`, `Thought`, `Action`, `Observation`, `Output`) qua Server-Sent Events (SSE).
- **Hỗ trợ CLI**: Chạy và tương tác trực tiếp qua Command Line (`python run_agent.py`).
- **Đa dạng Provider LLM**: Dễ dàng chuyển đổi giữa các mô hình như Google Gemini (Flash / Flash Lite), OpenAI (GPT-4o Mini), Anthropic (Claude 3.5 Sonnet).

---

## 🛠️ Cài đặt & Hướng dẫn sử dụng

### 1. Cài đặt môi trường

Yêu cầu Python 3.10+. Clone dự án và cài đặt dependencies:

```bash
# Cài đặt qua pip
pip install -e .

# Hoặc cài đặt qua uv (nếu có)
uv sync
```

### 2. Cấu hình biến môi trường (`.env`)

Tạo file `.env` từ mẫu:

```bash
cp .env.example .env
```

Mở file `.env` và điền API Key cho Model mà bạn chọn sử dụng. Mặc định dự án dùng **Google Gemini**:

```env
GOOGLE_API_KEY=your_actual_google_api_key_here
```

*(Nếu muốn dùng OpenAI hoặc Anthropic, hãy điền `OPENAI_API_KEY` hoặc `ANTHROPIC_API_KEY` tương ứng).*

---

### 3. Cấu hình xác thực Google OAuth (Gmail & Calendar)

1. **Lấy `credentials.json`**:
   - Truy cập [Google Cloud Console](https://console.cloud.google.com/) và tạo/chọn 1 Project.
   - Bật **Gmail API** và **Google Calendar API** tại mục **APIs & Services → Library**.
   - Thiết lập **OAuth consent screen** (Loại External, nhớ thêm email của bạn vào danh sách **Test users**).
   - Tạo **OAuth client ID** (Loại **Desktop app**), tải file JSON về, đổi tên thành `credentials.json` và đặt vào thư mục gốc của dự án.

2. **Xác thực quyền đăng nhập (chỉ làm 1 lần)**:
   ```bash
   python src/authorize_gmail.py
   ```
   Trình duyệt sẽ tự động mở ra. Bạn tiến hành đăng nhập và chấp nhận cấp quyền đọc Gmail, tạo Draft và Calendar Events. Sau khi thành công, file `token.json` sẽ tự động được lưu.

---

### 4. Chạy ứng dụng

#### Option A: Giao diện Web Visualizer (Khuyên dùng)

Khởi động Flask Web Server:

```bash
python src/app.py
```
Truy cập trình duyệt tại **`http://127.0.0.1:5000`** để sử dụng giao diện trực quan.

#### Option B: Chạy qua CLI

Chạy Agent trực tiếp từ Command Line bằng file `run_agent.py`:

```bash
# Chạy với câu hỏi mặc định ("Tổng hợp giúp tôi các email chưa đọc...")
python run_agent.py

# Hoặc truyền câu hỏi tùy chỉnh
python run_agent.py "Tóm tắt các email chưa đọc trong 2 ngày qua"
python run_agent.py "Tạo email nháp trả lời cho alex@example.com nội dung đồng ý lịch họp"
python run_agent.py "Đặt lịch họp 'Thảo luận dự án' vào lúc 10:00 AM ngày mai"
```

---

## 🧪 Kiểm thử (Testing)

Dự án đi kèm bộ unit tests sử dụng `pytest`, `mypy --strict` và `ruff`. Để kiểm thử:

```bash
# Chạy Unit Tests
pytest tests/unit_tests

# Kiểm tra Type Safety với Mypy
python -m mypy --strict src/

# Kiểm tra Linter với Ruff
python -m ruff check .
```

---

## 📂 Cấu trúc thư mục

```text
ReAct-Agent-with-LangGraph/
├── src/
│   ├── app.py             # Flask Web App Server & SSE Event Streamer
│   ├── authorize_gmail.py # Script kích hoạt Google OAuth (Gmail & Calendar)
│   └── react_agent/
│       ├── graph.py       # Định nghĩa luồng ReAct Graph (nodes & edges)
│       ├── tools.py       # Gmail (search, read, draft) & Calendar tools
│       ├── context.py     # Cấu hình runtime context & tham số
│       ├── state.py       # Định nghĩa State và InputState
│       └── utils.py       # Helper functions cho LLM và xử lý tin nhắn
├── static/                # Static assets (CSS, JS) cho Web UI
├── templates/             # HTML Templates (index.html) cho Web UI
├── tests/                 # Unit tests & integration tests
├── run_agent.py           # Script chính để chạy Agent từ CLI
├── .env.example           # File mẫu biến môi trường
└── pyproject.toml         # Cấu hình dự án, linter & dependencies
```
