# Chương 23: Rủi ro Hoạt động (Operational Risk)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Định nghĩa Rủi ro Hoạt động (Operational Risk)
*   **Định nghĩa của Basel:** Là rủi ro tổn thất phát sinh từ sự yếu kém hoặc thất bại của các quy trình nội bộ, con người, hệ thống, hoặc từ các sự kiện bên ngoài.
*   **Bao gồm:** Rủi ro pháp lý (legal risk), gian lận nội bộ (nhân viên lừa đảo), tin tặc (cyber risk), thảm họa thiên nhiên.
*   **Loại trừ:** Rủi ro chiến lược (Strategic risk) và rủi ro danh tiếng (Reputational risk).

## 2. Phân loại Tổn thất
Ủy ban Basel chia rủi ro hoạt động thành 7 loại sự kiện (Event Types):
1.  Gian lận nội bộ (Internal Fraud) - Ví dụ: Jerome Kerviel (SocGen).
2.  Gian lận bên ngoài (External Fraud) - Ví dụ: Hacker đánh cắp tiền.
3.  Thực hành Tuyển dụng và An toàn lao động (Employment Practices & Workplace Safety).
4.  Khách hàng, Sản phẩm và Thực tiễn Kinh doanh (Clients, Products, & Business Practices) - Ví dụ: Bán sai sản phẩm (misselling).
5.  Thiệt hại Tài sản vật chất (Damage to Physical Assets).
6.  Gián đoạn kinh doanh và Lỗi hệ thống (Business Disruption & System Failures).
7.  Thực thi, Giao hàng và Quản lý quy trình (Execution, Delivery, & Process Management).

## 3. Tính toán Vốn cho Rủi ro Hoạt động
Như đã đề cập ở Chương 15 (Basel II), có 3 phương pháp. Phương pháp nâng cao nhất là **AMA (Advanced Measurement Approach)**:
*   Yêu cầu ngân hàng dùng mô hình nội bộ để tính **VaR 99.9% 1 năm** cho rủi ro hoạt động.
*   **Loss Distribution Approach (LDA - Phương pháp Phân phối Tổn thất):** Là phương pháp phổ biến nhất trong AMA. Nó mô phỏng hai biến số độc lập:
    *   **Loss Frequency (Tần suất tổn thất):** Số lần xảy ra sự kiện trong 1 năm. Thường mô phỏng bằng **Phân phối Poisson**.
    *   **Loss Severity (Mức độ nghiêm trọng):** Thiệt hại của mỗi lần xảy ra. Thường dùng **Phân phối Lognormal** hoặc dùng **Lý thuyết giá trị cực đoan (EVT)** để mô phỏng phần đuôi (các khoản lỗ khổng lồ hiếm gặp).
*   **Mô phỏng Monte Carlo:** Kết hợp Tần suất và Mức độ để vẽ ra phân phối tổn thất tổng thể và tìm điểm VaR 99.9%.

## 4. Quản trị Rủi ro Hoạt động Thực tế
Khác với rủi ro thị trường (có thể hedge bằng phái sinh), rủi ro hoạt động khó phòng vệ hơn nhiều.
*   **RCSA (Risk and Control Self-Assessment):** Tự đánh giá rủi ro và kiểm soát. Các phòng ban tự chấm điểm rủi ro của mình.
*   **KRI (Key Risk Indicators):** Các chỉ số cảnh báo sớm (Ví dụ: tỷ lệ nhân viên nghỉ việc đột ngột, số lượng lỗi giao dịch hàng ngày, số giờ hệ thống IT bị down).
*   **Phân bổ vốn (Allocation):** Để khuyến khích các bộ phận giảm thiểu rủi ro hoạt động, ngân hàng phải tính toán và trừ thẳng phí "Vốn rủi ro hoạt động" vào lợi nhuận của từng bộ phận.

## 5. Bảo hiểm (Insurance)
*   Ngân hàng có thể mua bảo hiểm cho một số rủi ro hoạt động (như hỏa hoạn, gian lận nhân viên).
*   Tuy nhiên, rủi ro "Rogue Trader" (trader giấu lỗ) cực kỳ khó mua bảo hiểm vì tính chất rủi ro đạo đức (Moral Hazard).

---
**Ghi chú:** Rủi ro hoạt động là "kẻ thù vô hình". Các mô hình toán học (như LDA) có thể cho ra con số, nhưng chìa khóa thực sự nằm ở **Văn hóa Rủi ro (Risk Culture)** mạnh mẽ, nơi nhân viên được khuyến khích báo cáo sai sót thay vì che giấu chúng.
