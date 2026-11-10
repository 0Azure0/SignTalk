# SignTalk

SignTalk nhận diện một số ký hiệu bằng MediaPipe và mô hình phân loại SVM đã huấn luyện. Giao diện mới dùng React, TypeScript, Vite, Tailwind CSS và Lucide React. Flask tiếp tục cung cấp API nhận diện; mô hình và xử lý ảnh không đổi.

## Chạy trong môi trường phát triển

Yêu cầu Python 3.9–3.11 và Node.js 20.19+ (hoặc 22.12+).

1. Dùng Python 3.9–3.11. Nếu chưa có môi trường ảo, tạo bằng Python 3.11:

   ```powershell
   py -3.11 -m venv .venv
   ```

2. Cài thư viện và khởi chạy Flask bằng cùng môi trường Python:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe main.py
   ```

   Có thể dùng `run.bat` để khởi chạy Flask nếu đã thiết lập `.venv`.

3. Trong terminal thứ hai, cài và chạy giao diện:

   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```

4. Mở URL Vite hiển thị trong terminal (mặc định `http://localhost:5173`). Vite chuyển tiếp `/api` đến Flask tại `http://127.0.0.1:5000`.

## Build giao diện và chạy qua Flask

```powershell
cd frontend
npm ci
npm run build
cd ..
.\.venv\Scripts\python.exe main.py
```

Sau khi build, Flask phục vụ giao diện React tại `http://127.0.0.1:5000`. Nếu chưa có bản build, Flask giữ trang HTML cũ làm dự phòng.

Camera chỉ hoạt động trong ngữ cảnh an toàn (localhost hoặc HTTPS). Khung hình JPEG được gửi đến máy chủ SignTalk đang chạy để phân tích. Để MediaPipe bắt tay ổn định, dùng ánh sáng đủ rõ, tránh ngược sáng và giữ bàn tay trọn trong khung hình. Ứng dụng yêu cầu camera tối đa 1280×720 nếu thiết bị hỗ trợ; trình duyệt có thể chọn độ phân giải thấp hơn theo khả năng camera.

## Nhận diện từng động tác

Sau khi bật camera, thực hiện trọn một ký hiệu. SignTalk ghi nhận các khung hình có bàn tay và tổng hợp dự đoán trong cả lượt; từ chỉ hiện khi tay rời khung hình hoặc động tác dừng ổn định. Sau khi hiện kết quả, hệ thống tạm dừng. Bấm **Tiếp tục quét** để bắt đầu lượt kế tiếp. Mỗi lượt có giới hạn 10 giây.

Giao diện không tuyên bố dịch toàn bộ ngôn ngữ ký hiệu; hãy kiểm tra kết quả trước khi dùng trong giao tiếp quan trọng.

## Ký hiệu được hỗ trợ

Các nhãn được cấu hình trong `utils/strings.py`; tập dữ liệu hiện có gồm địa chỉ, ghen tị, nhập khẩu, tham ăn và xin lỗi. Độ chính xác phụ thuộc vào mô hình trong thư mục `models/` và điều kiện camera.

## Thu thập dữ liệu và huấn luyện

Để thêm dữ liệu video, tạo một thư mục cho mỗi ký hiệu trong `videos/`. Tên thư mục phải khớp với tên lớp, không gồm phần mở rộng `.npy`:

```text
videos/
├── Dia_chi/
│   ├── 01.mp4
│   ├── 02.mp4
│   └── 03.mp4
├── Ghen_ti/
│   ├── 01.mp4
│   └── 02.mp4
└── Xin_loi/
    └── 01.mp4
```

Mỗi video nên ghi một lần thực hiện riêng của đúng một ký hiệu. Đặt tên `01.mp4`, `02.mp4`, `03.mp4`... **bên trong thư mục ký hiệu tương ứng**; không dùng lại tên file trong cùng thư mục vì file mới có thể ghi đè file cũ. Tên file không quyết định nhãn, tên thư mục mới là nhãn. Nên quay đa dạng người thực hiện, khoảng cách, ánh sáng và nền.

Huấn luyện sẽ tự đọc tất cả video trong `videos/<tên_lớp>/`, lấy mẫu khung hình và chỉ giữ khung hình MediaPipe phát hiện được bàn tay. Nếu một lớp có video, video là nguồn dữ liệu cho lớp đó; file `.npy` cùng tên được bỏ qua để tránh đếm trùng. Các lớp không có video tiếp tục dùng `.npy` trong `data/`.

Chạy:

```bash
python scripts/train.py --model_name vsl_model
```

Mặc định xử lý mỗi khung hình thứ hai; có thể chỉnh bằng `--step 1` (mọi khung hình) hoặc `--step 3`. Quy trình train chuẩn hóa kích thước/vị trí bàn tay, cân bằng trọng số các lớp và đánh giá bằng 5-fold chia theo đoạn của từng video. Đây là phân loại theo từng khung hình, chưa học chuỗi chuyển động; ký hiệu cần phân biệt theo chuyển động có thể cần nâng cấp mô hình theo chuỗi thời gian.