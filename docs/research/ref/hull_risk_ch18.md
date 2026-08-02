# Chương 18: Đánh giá Căn bản Sổ Giao dịch (Fundamental Review of the Trading Book - FRTB)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Bối cảnh (Background)
*   Khung FRTB được Ủy ban Basel đưa ra để thay thế hoàn toàn cách tính vốn cho **Rủi ro Thị trường** (Market Risk) của Basel II.5.
*   **Sự thay đổi cốt lõi:** Thay thế **VaR 99%** bằng **Expected Shortfall (ES) 97.5%**. Cả hai đều yêu cầu tính toán dựa trên dữ liệu của một thời kỳ căng thẳng (stressed period). Mặc dù ES 97.5% và VaR 99% cho kết quả gần bằng nhau nếu phân phối chuẩn, nhưng với "đuôi béo", ES sẽ cho kết quả lớn hơn và nắm bắt rủi ro sụp đổ tốt hơn.
*   **Chân trời thanh khoản (Liquidity Horizons):** Thay vì dùng chung một thời gian nắm giữ 10 ngày (10-day horizon) cho mọi tài sản như trước, FRTB phân loại các yếu tố rủi ro (risk factors) thành 5 nhóm thời gian khác nhau tùy thuộc vào tính thanh khoản của chúng: **10 ngày, 20 ngày, 40 ngày, 60 ngày, và 120 ngày**.
    *   Ví dụ: Cổ phiếu vốn hóa lớn (10 ngày), Cổ phiếu vốn hóa nhỏ (20 ngày), Chênh lệch tín dụng (Credit spread) của trái phiếu rác (60 ngày).

## 2. Phương pháp Tiêu chuẩn (Standardized Approach)
Kể từ FRTB, Phương pháp Tiêu chuẩn đóng vai trò cực kỳ quan trọng vì nó tạo ra **mức sàn (floor)** cho vốn yêu cầu (kể cả khi ngân hàng dùng mô hình nội bộ, vốn cũng không được thấp hơn 72.5% mức tính theo chuẩn). Vốn gồm 3 phần:
1.  **Risk Charge dựa trên Độ nhạy (Sensitivities):** 
    *   Dựa trên phương pháp Model-Building (Chương 14).
    *   Chia làm 3 cấu phần: **Delta risk** (biến động giá tuyến tính), **Vega risk** (biến động của volatility), và **Curvature risk** (rủi ro phi tuyến tính / Gamma risk).
    *   Ngân hàng tự tính Delta, Vega, Curvature. Basel áp đặt các **Trọng số rủi ro (Risk Weights)** và **Hệ số tương quan (Correlations)** để tính ra tổng vốn.
2.  **Default Risk Charge:** Rủi ro vỡ nợ (Jump-to-default). Tách biệt rủi ro vỡ nợ khỏi rủi ro chênh lệch tín dụng (credit spread risk).
3.  **Residual Risk Add-on:** Rủi ro thặng dư cho các sản phẩm phức tạp (ví dụ: exotic options) không thể nắm bắt hết bằng Delta/Vega/Curvature.

## 3. Phương pháp Mô hình Nội bộ (Internal Models Approach)
*   Chỉ được áp dụng nếu ngân hàng được phê duyệt ở cấp độ **Từng bàn giao dịch (Desk-by-desk)** chứ không phải toàn ngân hàng. Nếu một Desk trượt bài kiểm tra, Desk đó phải quay về dùng Phương pháp Tiêu chuẩn.
*   **Tính toán ES:** Yêu cầu dùng mô phỏng lịch sử (Historical Simulation) nhưng phức tạp hơn. Phải dùng chu kỳ **10 ngày gối đầu (overlapping 10-day periods)** từ giai đoạn khủng hoảng.
*   **Phương pháp Thác (Cascade Approach):** Do có nhiều mức Liquidity Horizon (10, 20, 40, 60, 120 ngày), việc tính ES phải làm theo dạng lớp (tính ES cho nhóm 10 ngày, rồi cộng thêm chênh lệch ES của nhóm 20 ngày, v.v.).
*   **Bài kiểm tra khắt khe:**
    *   **Back-testing:** Dùng VaR 99% và 97.5% (1 ngày) trên dữ liệu 1 năm qua. Nếu số lần vượt ngưỡng (exceptions) quá nhiều, Desk bị loại. (Chú ý: Back-test bằng VaR, nhưng tính vốn bằng ES).
    *   **P&L Attribution (Phân bổ Lỗ/Lãi):** So sánh Lợi nhuận thực tế (Actual P&L) và Lợi nhuận do mô hình rủi ro dự báo (Hypothetical P&L). Nếu sai lệch quá nhiều, Desk bị loại.

## 4. Trading Book vs. Banking Book (Ranh giới hai sổ)
*   **Vấn đề cũ:** Ngân hàng thường chuyển các tài sản tín dụng rủi ro sang Trading Book để lách luật (giảm vốn) do vốn thị trường thường tính thấp hơn vốn tín dụng.
*   **Quy định mới của FRTB:** Xây dựng ranh giới nghiêm ngặt.
    *   Việc chuyển đổi tài sản qua lại giữa hai sổ sau khi đã ghi nhận là **vô cùng khó khăn**, chỉ xảy ra trong các trường hợp đặc biệt (ví dụ: đóng cửa toàn bộ một Desk).
    *   Bất kỳ khoản giảm vốn nào (capital benefit) sinh ra do việc chuyển sổ đều không được công nhận.

---
**Ghi chú:** FRTB biến việc tính toán vốn rủi ro thị trường trở nên phức tạp và đắt đỏ hơn rất nhiều. Nó phản ánh sự thiếu tin tưởng của Ủy ban Basel vào các mô hình nội bộ của ngân hàng sau khủng hoảng 2008, do đó họ áp đặt nhiều rào cản và quy định chi tiết để ngăn chặn việc lách luật.
