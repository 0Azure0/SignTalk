class ExpressionHandler:

    MAPPING = {
        # Các class cũ
        "bình_thường": "Ngồi yên",
        "cảm_ơn": "Cảm ơn",
        "xin_chào": "Xin chào",
        "yêu": "Yêu",
        "không": "Không",

        # Các class mới
        "Dia_chi": "Địa chỉ 📍",
        "Ghen_ti": "Ghen tị 😒",
        "Nhap_khau": "Nhập khẩu 🛂",
        "Tham_an": "Tham ăn 🍽️",
        "Xin_loi": "Xin lỗi 🙏",
    }

    def __init__(self):
        # Lưu kết quả nhận diện hiện tại
        self.current_message = ""

    def receive(self, message):
        self.current_message = message

    def get_message(self):
        # Nếu class đã có trong MAPPING
        if self.current_message in ExpressionHandler.MAPPING:
            return ExpressionHandler.MAPPING[self.current_message]

        # Nếu sau này thêm class mới nhưng chưa khai báo
        # thì hiển thị trực tiếp tên class thay vì làm Streamlit crash
        return str(self.current_message)