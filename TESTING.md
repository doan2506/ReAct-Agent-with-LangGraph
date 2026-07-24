# Hướng Dẫn Test Agent

## 📋 1. Chuẩn Bị Tệp Cấu Hình (Prerequisites)

Trước khi chạy test, hãy đảm bảo các file sau đã sẵn sàng trong thư mục gốc của project:

1. **`credentials.json`**: File OAuth client secrets tải từ Google Cloud Console (*Desktop App*).
2. **`token.json`**: File lưu OAuth refresh token.
   - Nếu chưa có, chạy lệnh sau 1 lần duy nhất để đăng nhập trình duyệt:
     ```bash
     python authorize_gmail.py
     ```
3. **`.env`**: Điền API key cho LLM trong file `.env`:
   ```env
   GOOGLE_API_KEY=your_gemini_api_key
   ```
   *(Nếu dùng OpenAI: set `OPENAI_API_KEY=...` và thêm `MODEL=openai/gpt-4o-mini`)*

---

## 🧪 2. Bước 1: Chạy Automated Unit Tests

Kiểm tra xem toàn bộ các component (`State`, `Context`, `utils`, `tools`) có hoạt động chuẩn xác hay không:

```bash
pytest tests/unit_tests/
```

- **Kết quả mong đợi**: Tất cả các unit test đều `PASSED`.

---

## 🚀 3. Bước 2: Test Agent Qua CLI (`run_agent.py`)

Chạy agent bằng script CLI tích hợp sẵn:

```bash
# 1. Chạy câu lệnh mặc định (Tổng hợp email chưa đọc)
python run_agent.py

# 2. Chạy với câu hỏi tùy chỉnh
python run_agent.py "Có email nào từ sếp hoặc cảnh báo bảo mật không?"
```

- **Kết quả mong đợi**: Agent gọi công cụ Gmail `search_emails`, đọc các thư trong hộp thư inbox, phân loại theo nhóm (Bảo mật, Công việc, Khuyến mãi, Mạng xã hội) và đưa ra danh sách **Cần chú ý ngay** ở cuối.

---

## 🛠️ Các Cải Tiến Đã Được Thêm Vào Branch Này

1. **`src/react_agent/state.py`**: Bổ sung các thuộc tính mở rộng cho state (`retrieved_emails`, `email_summary`, `error`).
2. **`src/react_agent/tools.py`**:
   - Thêm hàm `_get_context()` an toàn, không bị crash nếu runtime context là `None`.
   - Bổ sung xử lý ngoại lệ `try-except` cho `search_emails`, `get_email`, `get_thread` để trả về thông báo lỗi thân thiện thay vì làm đứt đoạn luồng graph.
   - Trả về thông báo rõ ràng khi kết quả tìm kiếm rỗng (`No emails found`).
3. **`src/react_agent/graph.py`**:
   - Cập nhật `call_model` để trích xuất `context` an toàn với `getattr(runtime, "context", None)`.
   - Thay thế định dạng prompt an toàn với `.replace("{system_time}", ...)` tránh lỗi khi prompt chứa dấu ngoặc nhọn `{}`.
4. **`run_agent.py`**:
   - Tự động cấu hình chuẩn UTF-8 stdout cho terminal Windows.
