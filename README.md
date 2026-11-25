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

### Truy cập bằng tên miền cố định

`Start_SignTalk_Tunnel.bat` dùng Cloudflare Tunnel đã tạo sẵn để đưa ứng dụng lên `https://signtalk.com.vn`. Tên miền `signtalk.com.vn` cần được thêm vào Cloudflare và nameserver tại nhà đăng ký tên miền cần trỏ về Cloudflare. Cần hoàn tất cấu hình một lần trước khi chạy file BAT:

1. Mở Command Prompt trên máy đã cài `cloudflared` và đăng nhập Cloudflare:

   ```bat
   cloudflared tunnel login
   cloudflared tunnel create signtalk
   cloudflared tunnel route dns signtalk signtalk.com.vn
   ```

   Lệnh `tunnel create` in ra UUID của tunnel và tạo file thông tin xác thực trong `%USERPROFILE%\.cloudflared\`. Ghi lại UUID đó.

2. Tạo file `%USERPROFILE%\.cloudflared\config.yml`, thay `<UUID>` và `<ten-windows>` bằng giá trị tương ứng trên máy:

   ```yaml
   tunnel: <UUID>
   credentials-file: C:\Users\<ten-windows>\.cloudflared\<UUID>.json

   ingress:
     - hostname: signtalk.com.vn
       service: http://127.0.0.1:5000
     - service: http_status:404
   ```

3. Khởi động ứng dụng bằng `run.bat`, sau đó chạy `Start_SignTalk_Tunnel.bat`. Giữ cả hai cửa sổ mở khi sử dụng; địa chỉ truy cập cố định là `https://signtalk.com.vn`.

Tunnel chỉ hoạt động khi máy tính đang bật, có Internet và ứng dụng SignTalk đang chạy. Tên miền công khai cho phép người khác truy cập ứng dụng của bạn.

Camera chỉ hoạt động khi được mở trong ngữ cảnh an toàn (localhost hoặc HTTPS). Khung hình được xử lý bởi ứng dụng SignTalk đang chạy trên máy của bạn.
Để MediaPipe bắt được tay ổn định, dùng ánh sáng đủ rõ, tránh ngược sáng và đưa bàn tay lại gần camera nhưng vẫn nằm trọn trong khung hình. Ứng dụng yêu cầu camera tối đa 1280×720 nếu thiết bị hỗ trợ; trình duyệt có thể chọn độ phân giải thấp hơn theo khả năng camera.

Lần đầu mở ứng dụng, chọn **Đăng ký** để tạo tài khoản với tên hiển thị, tên đăng nhập và mật khẩu (tối thiểu 8 ký tự). Mật khẩu được lưu dưới dạng băm trong `data/users.sqlite3`; các lần sau đăng nhập bằng tên đăng nhập và mật khẩu. Hồ sơ người dùng hiển thị ngay trong giao diện. Đặt biến môi trường `SIGNTALK_SECRET_KEY` thành một giá trị bí mật cố định nếu cần giữ phiên đăng nhập ổn định sau khi khởi động lại ứng dụng.

## Nhận diện theo thời gian thực

Sau khi bật camera, SignTalk cập nhật kết quả ngay khi nhận diện được ký hiệu và tự động tiếp tục quét. Nếu phát hiện khuôn mặt nhưng không thấy bàn tay, ứng dụng theo dõi vị trí khuôn mặt; khi vị trí ổn định khoảng 1,8 giây, kết quả hiển thị **Đứng yên**. Khi người trong khung hình di chuyển, ứng dụng tiếp tục theo dõi và cập nhật trạng thái.

Trong thẻ **Nhận diện ký hiệu**, bật **Đọc kết quả** để phát âm thanh sau khi nhận diện ổn định; không cần đợi kết thúc cử chỉ. Nếu `audio/<nhãn>.mp3` tồn tại, SignTalk phát file thu sẵn đó; nhãn chưa có file sẽ dùng giọng tiếng Việt `vi-VN` của trình duyệt làm dự phòng. Tên file phải khớp với nhãn nội bộ trong `utils/strings.py` (không cần khớp chữ hoa/thường). Tắt tùy chọn để im lặng; trạng thái được lưu riêng theo tài khoản trên trình duyệt hiện tại.

## Hướng dẫn và video mẫu

Chọn **Hướng dẫn sử dụng** trong thanh điều hướng để mở trang hướng dẫn riêng. Thư viện liệt kê các từ vựng trong `utils/strings.py` và tự ghép video từ thư mục con tương ứng trong `Video_mau/`. Có thể tìm từ, lọc từ đã có/chưa có video, thêm nhiều file `.mp4` cho một từ rồi chọn clip muốn xem. Video mẫu luôn phát ở chế độ tắt tiếng. Từ chưa có video sẽ hiện trạng thái **Video mẫu sẽ bổ sung sau**.

## Đánh giá và đóng góp

Trang **Đánh giá** cho phép mỗi tài khoản chấm từ 1 đến 5 sao, gửi nhận xét và cập nhật đánh giá của mình; đánh giá được lưu trong `data/users.sqlite3`. Trang **Đóng góp** ghi nhận mức tiền dự kiến hỗ trợ duy trì dự án. Đây chưa phải giao dịch và ứng dụng chưa nhận tiền; cần cấu hình, công bố phương thức thanh toán trước khi sử dụng để thu nhận đóng góp thực tế.

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

Huấn luyện sẽ tự đọc tất cả video trong `videos/<tên_lớp>/`, lấy mẫu khung hình và chỉ giữ khung hình MediaPipe phát hiện được bàn tay. Video không đọc được hoặc không phát hiện tay ở khung hình nào sẽ bị bỏ qua và ghi log `[SKIP]`; nếu cả lớp không còn video dùng được, lớp đó cũng được loại khỏi lần train. Nếu không còn mẫu nào dùng được, train dừng với lỗi rõ ràng. Nếu một lớp có video, video là nguồn dữ liệu cho lớp đó; file `.npy` cùng tên được bỏ qua để tránh đếm trùng. Các lớp không có video tiếp tục dùng `.npy` trong `data/`.

Chạy:

```bash
python scripts/train.py --model_name vsl_model
```

Mặc định xử lý mỗi khung hình thứ hai; có thể chỉnh bằng `--step 1` (mọi khung hình) hoặc `--step 3`. Quy trình train chuẩn hóa kích thước/vị trí bàn tay, cân bằng trọng số các lớp và đánh giá bằng 5-fold chia theo nhóm. Log hiển thị tiến độ, thời gian, Accuracy và Macro F1 từng fold, cùng báo cáo tổng hợp OOF; sau đó model cuối được train trên toàn bộ dữ liệu. Đây là phân loại theo từng khung hình, chưa học chuỗi chuyển động; ký hiệu cần phân biệt theo chuyển động có thể cần nâng cấp mô hình theo chuỗi thời gian.

Để tránh xử lý video mỗi lần train, chuyển video của từng lớp thành `.npy` một lần. Nếu file đích chưa tồn tại:

```bash
python scripts/video_to_data.py --input "videos/Dia_chi" --pose_name "Dia_chi" --step 2
```

Lặp lại lệnh cho các lớp cần cache. Nếu `data/<tên_lớp>.npy` đã tồn tại và muốn giữ dữ liệu trong đó, thêm `--append` để nối mẫu video vào; công cụ sẽ từ chối ghi đè nếu không chỉ rõ `--append` hoặc `--overwrite`. Chỉ chuyển mỗi video một lần khi dùng `--append`; chạy lại trên cùng video sẽ thêm mẫu trùng lặp. Sau khi cache xong, train chỉ từ `.npy`:

```bash
python scripts/train.py --model_name vsl_model --data_only
```

Khi thêm lớp mới, chỉ cần chuyển video của lớp đó thành `data/<lớp_mới>.npy`, rồi chạy lại lệnh train với `--data_only`. Các `.npy` cũ được dùng lại; không cần trích đặc trưng lại từ video cũ.

Trên Windows, có thể bấm `Cache_Videos_To_NPY.bat` để chuyển các lớp video chưa cache trong `videos/` sang `data/<lớp>.npy`, sau đó bấm `Train_From_NPY.bat` để train chỉ từ `.npy`. File đánh dấu theo từng lớp trong `processed/video_npy_cache/` giúp lần chạy sau bỏ qua các lớp đã cache và xử lý các lớp mới. Nếu thêm video vào một lớp đã cache, cần xóa marker của lớp đó trước khi cache lại; việc này sẽ nối lại toàn bộ video lớp đó nên có thể tạo mẫu trùng lặp.

### Thử nghiệm keypoint chuỗi thời gian

`scripts/train_sequence.py` là trainer độc lập cho các file dạng `(frames, 76, 3)` trong `processed/keypoints_splited/train/` và `processed/keypoints_splited/test/`. Script nội suy mỗi chuỗi về 16 frame, train bộ phân loại tuyến tính riêng và lưu model thử nghiệm tại `models/vsl_test1.pkl`; báo cáo từng lớp nằm ở `models/vsl_test1_report.txt`. Artifact này không tương thích với model 86 đặc trưng đang dùng trong ứng dụng.

```bash
python scripts/train_sequence.py
```