# Chương 26: Vốn Kinh tế và RAROC (Economic Capital and RAROC)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Vốn Kinh tế (Economic Capital) là gì?
*   **Định nghĩa:** Là số vốn mà chính **ngân hàng tự tính toán** (sử dụng các mô hình nội bộ) để đảm bảo rằng xác suất phá sản trong 1 năm tới giảm xuống một mức mục tiêu cực kỳ thấp (ví dụ: 0.03%, tương đương với xếp hạng tín nhiệm AA).
*   **So sánh với Vốn Quy định (Regulatory Capital):**
    *   *Vốn quy định:* Do Ủy ban Basel / Ngân hàng Trung ương ép buộc. Thường dựa trên các công thức chung, cứng nhắc để bảo vệ hệ thống kinh tế.
    *   *Vốn kinh tế:* Phản ánh "khẩu vị rủi ro" thực sự của ngân hàng. Nó thường nhạy bén hơn, bao gồm cả các rủi ro mà Basel có thể chưa tính hết (như rủi ro tập trung, rủi ro kinh doanh).
*   Ngân hàng luôn phải duy trì số vốn thực tế cao hơn *cả* Vốn quy định và Vốn kinh tế.

## 2. Phân bổ Vốn Kinh tế (Allocating Economic Capital)
*   Để tính tổng Vốn Kinh tế, ngân hàng phải tính toán riêng lẻ vốn cho Rủi ro Thị trường, Rủi ro Tín dụng, Rủi ro Hoạt động, sau đó **tổng hợp (aggregate)** chúng lại.
*   **Hiệu ứng Đa dạng hóa (Diversification Benefit):** Tổng vốn kinh tế của toàn ngân hàng sẽ nhỏ hơn tổng của từng bộ phận cộng lại (do rủi ro các bộ phận không hoàn toàn tương quan 100% với nhau).
*   Ngân hàng dùng Định lý Euler (Component VaR) để phân bổ ngược lại phần Vốn kinh tế tổng này cho từng chi nhánh, từng phòng giao dịch.

## 3. RAROC (Risk-Adjusted Return on Capital)
Đây là "chén thánh" trong việc đánh giá hiệu quả hoạt động của các ngân hàng hiện đại.
*   **Công thức:**
    $$RAROC = \frac{Doanh\_thu - Chi\_phí - Tổn\_thất\_Kỳ\_vọng\_(EL)}{Vốn\_Kinh\_tế\_(Economic\_Capital)}$$
*   **Ý nghĩa:** Trước đây, một trader kiếm được 10 triệu USD bằng cách đánh cược rủi ro cực lớn sẽ được thưởng cao hơn một trader kiếm 5 triệu USD an toàn. Với RAROC, trader đầu tiên có thể yêu cầu số Vốn Kinh tế khổng lồ (VD: 100 triệu USD) dẫn đến RAROC = 10%. Trong khi trader thứ hai chỉ cần 20 triệu USD Vốn Kinh tế, dẫn đến RAROC = 25%.
*   Ngân hàng sẽ dồn nguồn lực (capital) cho các đơn vị kinh doanh có RAROC cao nhất, vì chúng tạo ra nhiều giá trị nhất cho mỗi đồng rủi ro phải gánh chịu.

## 4. Giá trị Gia tăng Cổ đông (Shareholder Value Added - SVA)
*   Để một bộ phận thực sự tạo ra giá trị, RAROC của nó phải lớn hơn **Chi phí Vốn (Hurdle Rate / Cost of Capital)** của ngân hàng.
*   $SVA = (RAROC - Hurdle\_Rate) \times Vốn\_Kinh\_tế$

---
**Ghi chú:** RAROC thay đổi hoàn toàn văn hóa ngân hàng. Nó buộc mọi nhân viên, từ tín dụng đến trading, phải luôn cân nhắc câu hỏi: "Lợi nhuận này có xứng đáng với số vốn rủi ro mà ngân hàng phải bỏ ra không?".
