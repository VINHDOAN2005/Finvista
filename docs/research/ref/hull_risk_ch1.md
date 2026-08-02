# Chương 1: Giới thiệu (Introduction)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Tầm nhìn của Giám đốc Quản trị Rủi ro (CRO)
*   **Nhiệm vụ cốt lõi:** Khi xem xét một dự án mới, CRO không chỉ nhìn vào các chỉ số sinh lời (như NPV) mà phải đánh giá dự án đó khớp như thế nào vào **danh mục rủi ro tổng thể** của công ty.
*   **Các câu hỏi then chốt:**
    *   Hiệu quả của dự án mới có tương quan (correlation) như thế nào với các mảng kinh doanh hiện tại?
    *   Nó sẽ làm tăng hay giảm biến động (dampening the ups and downs) của toàn doanh nghiệp?
*   **Bài học từ thực tế:** Các vụ thua lỗ chấn động từ "trader lừa đảo" (rogue trader) tại Barings Bank (1995), Allied Irish Bank (2002), SocGen (2007), và UBS (2011) cho thấy hệ thống thu thập dữ liệu giao dịch yếu kém có thể dẫn đến thảm họa.

## 2. Quan hệ Rủi ro và Lợi nhuận (Risk vs. Return)
### 2.1. Lợi nhuận kỳ vọng (Expected Return)
*   Trong thống kê, lợi nhuận kỳ vọng là **giá trị trung bình (mean)**, tính bằng trung bình trọng số của các kết quả có thể xảy ra theo xác suất.
*   Công thức: $E(R) = \sum_{i=1}^{n} p_i R_i$

### 2.2. Định lượng rủi ro
*   Thước đo phổ biến nhất là **Độ lệch chuẩn (Standard Deviation)** của lợi nhuận trong một năm.
*   Công thức: $\sigma = \sqrt{E(R^2) - [E(R)]^2}$

### 2.3. Cơ hội đầu tư và Đa dạng hóa
*   Khi kết hợp các tài sản, nhà đầu tư hướng tới việc di chuyển về phía **"Tây Bắc"** trên đồ thị (tăng lợi nhuận kỳ vọng, giảm độ lệch chuẩn).
*   Công thức độ lệch chuẩn danh mục 2 tài sản:
    $$\sigma_P = \sqrt{w_1^2\sigma_1^2 + w_2^2\sigma_2^2 + 2\rho w_1 w_2 \sigma_1 \sigma_2}$$
    *(Trong đó $\rho$ là hệ số tương quan giữa hai tài sản)*

## 3. Các Mô hình Lý thuyết Nền tảng
### 3.1. Đường biên hiệu quả (Efficient Frontier)
*   Tập hợp các danh mục không bị lấn át bởi bất kỳ danh mục nào khác (không có danh mục nào cùng rủi ro mà lợi nhuận cao hơn, hoặc cùng lợi nhuận mà rủi ro thấp hơn).
*   Khi có **tài sản phi rủi ro ($R_F$)**, đường biên hiệu quả trở thành một đường thẳng (line FJ) đi qua $R_F$ và tiếp tuyến với đường biên rủi ro tại điểm $M$ (Danh mục thị trường - Market Portfolio).

### 3.2. Mô hình CAPM (Capital Asset Pricing Model)
*   **Rủi ro hệ thống (Systematic Risk):** Rủi ro không thể đa dạng hóa, gắn liền với toàn bộ thị trường.
*   **Rủi ro phi hệ thống (Nonsystematic Risk):** Rủi ro riêng biệt của tài sản, có thể loại bỏ bằng đa dạng hóa.
*   **Công thức CAPM:** $E(R) = R_F + \beta(E(R_M) - R_F)$
    *   $\beta$ (Beta) đo lường độ nhạy của tài sản với thị trường: $\beta = \frac{\rho \sigma}{\sigma_M}$

### 3.3. Alpha ($\alpha$) và Hiệu quả đầu tư
*   **Alpha:** Phần lợi nhuận thực tế vượt quá mức lợi nhuận kỳ vọng dựa trên rủi ro hệ thống ($\beta$).
*   $\alpha = R_P - [R_F + \beta(R_M - R_F)]$
*   Trong một thị trường hiệu quả, trung bình cộng Alpha của tất cả nhà đầu tư phải bằng 0.

### 3.4. Thuyết Định giá Kinh doanh chênh lệch (APT)
*   Là mở rộng của CAPM, giả định lợi nhuận phụ thuộc vào **nhiều yếu tố** rủi ro hệ thống thay vì chỉ một (như GDP, lãi suất, lạm phát...).

## 4. Tại sao doanh nghiệp phải quản trị tổng rủi ro?
Mặc dù lý thuyết cho rằng cổ đông có thể tự đa dạng hóa rủi ro phi hệ thống, doanh nghiệp (đặc biệt là định chế tài chính) vẫn phải quản lý nó vì:
1.  **Chi phí phá sản (Bankruptcy Costs):** Quá trình phá sản làm tiêu tốn giá trị tài sản thực tế (phí luật sư, mất khách hàng, hủy hoại uy tín). Ví dụ: Lehman Brothers tốn gần 2 tỷ USD chỉ riêng phí pháp lý và kế toán.
2.  **Định chế tài chính sống bằng niềm tin:** Nếu thị trường nghi ngờ ngân hàng rủi ro, nguồn vốn (wholesale deposits) sẽ cạn kiệt ngay lập tức, dẫn đến sụp đổ thanh khoản (Northern Rock).
3.  **Quy định (Regulation):** Các cơ quan chính phủ yêu cầu ngân hàng phải giữ đủ vốn để giảm xác suất phá sản xuống mức cực thấp (ví dụ: chỉ 0.1% trong 1 năm).

## 5. Chiến lược Quản trị Rủi ro của Định chế tài chính
*   **Risk Decomposition (Phân rã rủi ro):** Quản lý từng rủi ro riêng lẻ (thường ở Front Office/Trading Room). Mỗi trader chịu trách nhiệm cho một biến số (ví dụ: tỷ giá USD/Yen).
*   **Risk Aggregation (Tổng hợp rủi ro):** Tính toán tổng rủi ro từ tất cả các biến số thị trường (thường ở Middle Office).

## 6. Xếp hạng Tín dụng (Credit Ratings)
*   Ba tổ chức lớn: **Moody’s, S&P, và Fitch**.
*   **Investment Grade (Hạng đầu tư):** Từ BBB- (S&P) hoặc Baa3 (Moody's) trở lên.
*   **Speculative Grade / Junk Bonds (Hạng đầu cơ):** Các mức xếp hạng thấp hơn, rủi ro vỡ nợ cao hơn.

---
**Ghi chú từ Business Snapshot 1.1:** Một công ty thâu tóm công ty khác trị giá 1 tỷ USD bằng nợ, kỳ vọng sức mạnh cộng hưởng nhưng thất bại. Chi phí phá sản sau đó làm cổ đông mất trắng, trong khi các ngân hàng và chủ nợ nắm giữ toàn bộ phần tài sản còn lại. Quản trị rủi ro kém trong việc thâu tóm là nguyên nhân hàng đầu gây sụp đổ doanh nghiệp.
