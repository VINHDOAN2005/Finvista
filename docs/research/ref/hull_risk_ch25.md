# Chương 25: Rủi ro Mô hình (Model Risk)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Bản chất của Mô hình trong Tài chính
Trong vật lý, mô hình mô tả thế giới thực một cách chính xác (ví dụ: định luật Newton). Nhưng trong tài chính:
*   Mô hình mô tả hành vi của **con người** và **thị trường**, vốn luôn thay đổi và phi lý trí.
*   **"Tất cả các mô hình đều sai, nhưng một số mô hình có ích" (George Box).** Vấn đề không phải là tìm một mô hình hoàn hảo, mà là hiểu rõ những sai số và giới hạn của mô hình đang dùng.

## 2. Rủi ro Mô hình (Model Risk) là gì?
Là rủi ro xảy ra tổn thất tài chính khi định chế tài chính ra quyết định dựa trên các mô hình có lỗi, bị sử dụng sai mục đích, hoặc bị "đánh bại" bởi sự thay đổi của thực tế.

### Các dạng Rủi ro Mô hình phổ biến:
1.  **Pricing Models (Mô hình Định giá):** Dùng để tính giá trị của phái sinh phức tạp (như Black-Scholes, Monte Carlo). Rủi ro là định giá sai dẫn đến lỗ khi bán lại, hoặc trả thưởng sai cho trader dựa trên lợi nhuận ảo.
2.  **Risk Models (Mô hình Rủi ro):** Dùng để tính VaR, ES. Rủi ro là đánh giá thấp rủi ro thực tế, dẫn đến giữ không đủ vốn đệm.

## 3. Mark-to-Market vs. Mark-to-Model
*   **Mark-to-Market (Đánh giá theo thị trường):** Tài sản được định giá dựa trên giá giao dịch công khai trên thị trường (Ví dụ: Cổ phiếu niêm yết). Rất ít rủi ro mô hình.
*   **Mark-to-Model (Đánh giá theo mô hình):** Áp dụng cho các sản phẩm OTC phức tạp không có giá thị trường (illiquid). Ngân hàng phải dùng mô hình nội bộ để "đoán" giá. Rủi ro mô hình cực cao, dễ bị trader thao túng (nhập tham số giả để làm đẹp báo cáo). Đây từng bị Warren Buffett gọi là "Mark-to-Myth" (Đánh giá theo chuyện thần thoại).

## 4. Các Nguồn gốc của Rủi ro Mô hình
1.  **Lỗi lập trình (Implementation errors):** Code sai, sai sót trong bảng tính Excel (rất phổ biến).
2.  **Sai lầm về Giả định (Model Assumptions):** Ví dụ lớn nhất là việc giả định tương quan bằng 0, hoặc giả định lợi nhuận theo phân phối chuẩn, dẫn đến cuộc khủng hoảng Gaussian Copula.
3.  **Dữ liệu đầu vào sai (Data inputs):** GIGO (Garbage In, Garbage Out). Dữ liệu lịch sử rác sẽ sinh ra mô hình rác.
4.  **Overfitting (Khớp quá mức):** Tạo ra một mô hình cực kỳ phức tạp khớp hoàn hảo với quá khứ nhưng thất bại thảm hại khi dự báo tương lai.

## 5. Quản trị Rủi ro Mô hình (Model Vetting)
Để chống lại rủi ro mô hình, các ngân hàng thiết lập nhóm **Model Validation (Thẩm định Mô hình)** độc lập (thuộc phòng Quản trị rủi ro, tách biệt với Trader). Nhóm này làm các công việc:
*   Đọc và kiểm tra lại toàn bộ logic toán học.
*   Kiểm tra code độc lập.
*   Thực hiện **Stress Test mô hình:** Xem mô hình có vỡ vụn khi đưa các tham số cực đoan vào không.
*   Theo dõi hiệu suất liên tục sau khi triển khai.

## 6. Lời khuyên cho nhà Quản lý
*   Đừng bao giờ tin tưởng mù quáng vào một mô hình phức tạp mà bạn không thể giải thích bằng ngôn ngữ đơn giản.
*   Luôn yêu cầu báo cáo về "Độ nhạy của mô hình" (Model Sensitivity): Kết quả sẽ thay đổi thế nào nếu giả định thay đổi 10%?

---
**Ghi chú:** Trong dự án Finvista, khi bạn xây dựng mô hình định giá Chứng quyền (Pricing Engine) bằng XGBoost hay Heston, việc có một quy trình back-testing nghiêm ngặt và giới hạn biên độ rủi ro là yếu tố sống còn để tránh "Model Risk".
