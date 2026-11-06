# SignTalk

SignTalk nhận diện một số ký hiệu bằng MediaPipe và mô hình phân loại đã huấn luyện. Giao diện web chạy bằng Flask; camera được mở trong trình duyệt và khung hình được gửi tới máy chủ cục bộ để phân tích.

## Chạy ứng dụng

1. Cài Python 3.9–3.11 và tạo môi trường ảo nếu cần.
2. Cài các thư viện:

   ```bash
   pip install -r requirements.txt
   ```

3. Khởi chạy máy chủ:

   ```bash
   python main.py
   ```

   Trên Windows, có thể chạy `run.bat` (yêu cầu môi trường ảo tại `.venv`).

4. Mở `http://127.0.0.1:5000` bằng Chrome hoặc Edge, sau đó chọn **Bật camera** và cấp quyền truy cập.

Camera chỉ hoạt động khi được mở trong ngữ cảnh an toàn (localhost hoặc HTTPS). Khung hình được xử lý bởi ứng dụng SignTalk đang chạy trên máy của bạn.
Để MediaPipe bắt được tay ổn định, dùng ánh sáng đủ rõ, tránh ngược sáng và đưa bàn tay lại gần camera nhưng vẫn nằm trọn trong khung hình. Ứng dụng yêu cầu camera tối đa 1280×720 nếu thiết bị hỗ trợ; trình duyệt có thể chọn độ phân giải thấp hơn theo khả năng camera.

## Nhận diện từng động tác

Sau khi bật camera, thực hiện trọn một ký hiệu. SignTalk ghi nhận các khung hình có bàn tay và tổng hợp dự đoán trong cả lượt; từ chỉ hiện khi tay rời khung hình hoặc động tác dừng ổn định. Sau khi hiện kết quả, hệ thống tạm dừng. Bấm **Tiếp tục quét** để bắt đầu lượt kế tiếp. Mỗi lượt có giới hạn 10 giây.

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