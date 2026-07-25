# Gmail Summarizer - ReAct Agent with LangGraph

Dự án này là một **ReAct Agent** (Reasoning + Acting) được xây dựng bằng **LangGraph**, hỗ trợ kết nối với **Gmail API** ở chế độ chỉ đọc (read-only) để tự động tìm kiếm, đọc và tổng hợp thông tin email chưa đọc.

---

## 🚀 Tính năng chính

- **ReAct Architecture**: Agent tự suy luận, chọn tool và xử lý dữ liệu qua vòng lặp ReAct của LangGraph.
- **Gmail Tools (Read-only)**:
  - `search_emails`: Tìm kiếm email với cú pháp tìm kiếm chuẩn của Gmail (ví dụ: `is:unread`, `newer_than:2d`).
  - `get_email`: Đọc nội dung đầy đủ của một email theo ID.
  - `get_thread`: Đọc toàn bộ luồng hội thoại theo Thread ID.
- **Dễ dàng mở rộng**: Hỗ trợ nhiều Provider LLM khác nhau (Google Gemini, OpenAI, Anthropic,...).
- **Chạy trực tiếp qua CLI**: Không bắt buộc phải cài đặt ứng dụng LangGraph Studio.

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

*(Nếu muốn dùng OpenAI hoặc Anthropic, hãy điền `OPENAI_API_KEY` hoặc `ANTHROPIC_API_KEY` tương ứng và cập nhật biến `MODEL` trong `.env`)*.

---

### 3. Cấu hình xác thực Gmail (OAuth)

1. **Lấy `credentials.json`**:
   - Truy cập [Google Cloud Console](https://console.cloud.google.com/) và tạo/chọn 1 Project.
   - Bật **Gmail API** tại mục **APIs & Services → Library**.
   - Thiết lập **OAuth consent screen** (Loại External, nhớ thêm email của bạn vào danh sách **Test users**).
   - Tạo **OAuth client ID** (Loại **Desktop app**), tải file JSON về, đổi tên thành `credentials.json` và đặt vào thư mục gốc của dự án.

2. **Xác thực quyền đăng nhập (chỉ làm 1 lần)**:
   ```bash
   python src/authorize_gmail.py
   ```
   Trình duyệt sẽ tự động mở ra. Bạn tiến hành đăng nhập và chấp nhận cấp quyền đọc Gmail, tạo Draft và Calendar. Sau khi thành công, file `token.json` sẽ tự động được lưu.

---

### 4. Chạy Agent

Sau khi cài đặt xong, bạn có thể chạy Agent trực tiếp từ Command Line bằng file `run_agent.py`:

```bash
# Chạy với câu hỏi mặc định ("Tổng hợp giúp tôi các email chưa đọc...")
python run_agent.py

# Hoặc truyền câu hỏi tùy chỉnh
python run_agent.py "Tóm tắt các email chưa đọc trong 2 ngày qua"
python run_agent.py "Có email nào quan trọng liên quan đến hợp đồng không?"
```

---

## 🧪 Kiểm thử (Testing)

Dự án đi kèm bộ unit tests sử dụng `pytest`. Để chạy kiểm thử:

```bash
pytest tests/unit_tests
```

---

## 📂 Cấu trúc thư mục

```text
ReAct-Agent-with-LangGraph/
├── src/
│   ├── authorize_gmail.py # Script kích hoạt OAuth Gmail & Calendar 1 lần
│   └── react_agent/
│       ├── graph.py       # Định nghĩa luồng ReAct (nodes & edges)
│       ├── tools.py       # Gmail & Calendar tools
│       ├── context.py     # Cấu hình runtime context & tham số
│       ├── state.py       # Định nghĩa State và InputState
│       └── utils.py       # Helper functions cho LLM và xử lý tin nhắn
├── tests/                 # Unit tests & integration tests
├── run_agent.py           # Script chính để chạy Agent từ CLI
├── .env.example           # File mẫu biến môi trường
└── pyproject.toml         # Cấu hình dự án & dependencies
```
