# Chương 20: CVA và DVA (Credit Value Adjustment and Debit Value Adjustment)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Dư nợ Tín dụng trên Công cụ Phái sinh (Credit Exposure on Derivatives)
Rủi ro tín dụng trong giao dịch phái sinh phức tạp hơn nhiều so với cho vay thông thường vì **dư nợ (exposure) trong tương lai là không chắc chắn**.
*   Nếu bạn cho vay 10 triệu USD, dư nợ luôn là ~10 triệu USD.
*   Nhưng nếu bạn ký một hợp đồng Swap, giá trị của Swap có thể dương (bạn có rủi ro nếu đối tác vỡ nợ) hoặc âm (bạn không có rủi ro tín dụng, mà đối tác mới là người chịu rủi ro).
*   **Netting (Bù trừ):** Khi có nhiều giao dịch với cùng một đối tác, dư nợ tổng bằng $max(V, 0)$, với $V$ là giá trị ròng của tất cả các giao dịch.

## 2. CVA (Credit Value Adjustment)
*   **Định nghĩa:** CVA là giá trị hiện tại của tổn thất kỳ vọng do khả năng đối tác vỡ nợ trong tương lai. Nó làm giảm giá trị của tài sản phái sinh trên bảng cân đối kế toán.
*   $Giá\_trị\_thực = Giá\_trị\_không\_rủi\_ro - CVA$
*   **Công thức tính toán:** CVA được tính bằng cách chia thời gian sống của giao dịch thành nhiều khoảng nhỏ. Tại mỗi khoảng, tính:
    $$CVA = \sum_{i=1}^{n} (1-R) \cdot q_i \cdot v_i$$
    *   $R$: Tỷ lệ thu hồi (Recovery rate).
    *   $q_i$: Xác suất vỡ nợ (Risk-neutral) của đối tác trong khoảng thời gian $i$.
    *   $v_i$: Giá trị hiện tại của **Expected Exposure** (Dư nợ kỳ vọng) tại thời điểm $i$. Thường phải dùng mô phỏng Monte Carlo để tính vì $v_i$ phụ thuộc vào biến động thị trường.

## 3. Tác động của Ký quỹ (Collateral) và Cure Period
*   **Ký quỹ:** Làm giảm Exposure. $E = max(V - C, 0)$ với $C$ là giá trị tài sản thế chấp mà đối tác đã nộp.
*   **Cure Period (Margin Period of Risk):** Là khoảng thời gian từ khi đối tác ngừng nộp ký quỹ cho đến khi vị thế bị đóng hoàn toàn (thường là 10-20 ngày). Rủi ro lớn nhất nằm ở chỗ thị trường có thể biến động rất mạnh chống lại ngân hàng trong khoảng thời gian "không được bảo vệ" này.

## 4. Tác động của Giao dịch mới (The Impact of a New Transaction)
*   Khi ký thêm một giao dịch mới với cùng một đối tác, CVA không nhất thiết tăng lên.
*   Nếu giao dịch mới có tương quan âm với các giao dịch cũ (ví dụ: giao dịch cũ bạn đang lãi, giao dịch mới dự kiến bạn sẽ lỗ), nhờ cơ chế Netting, CVA tổng thể có thể **giảm**. Điều này giải thích tại sao ngân hàng thường chào giá tốt hơn cho các khách hàng đã có sẵn vị thế đối nghịch với họ.

## 5. Rủi ro CVA (CVA Risk)
*   Bản thân CVA là một công cụ phái sinh cực kỳ phức tạp (phụ thuộc vào giá trị của toàn bộ danh mục).
*   Khi credit spread của đối tác tăng, CVA tăng, ngân hàng phải ghi nhận khoản lỗ (Mark-to-Market loss) ngay cả khi đối tác chưa vỡ nợ.
*   Ngân hàng phải phòng vệ rủi ro CVA bằng cách tính các Greeks cho CVA và mua CDS của đối tác. Basel III bắt buộc ngân hàng giữ vốn cho CVA Risk.

## 6. Rủi ro sai hướng (Wrong-Way Risk)
*   **Wrong-Way Risk:** Là rủi ro tồi tệ nhất khi xác suất vỡ nợ của đối tác tăng lên cùng lúc với dư nợ của bạn đối với họ tăng lên.
    *   *Ví dụ:* Bạn mua CDS bảo vệ vỡ nợ quốc gia từ một công ty trong chính quốc gia đó. Nếu quốc gia vỡ nợ, công ty kia cũng vỡ nợ, và bạn không thu được đồng nào.
*   **Right-Way Risk:** Ngược lại, xác suất vỡ nợ cao khi dư nợ thấp (có lợi cho ngân hàng).
*   Basel yêu cầu nhân hệ số Alpha (thường là 1.4) vào Expected Exposure để bù đắp cho Wrong-Way Risk nếu ngân hàng không có mô hình nội bộ tốt.

## 7. DVA (Debit/Debt Value Adjustment)
*   **Định nghĩa:** Là hình ảnh phản chiếu của CVA. DVA là phần giá trị ngân hàng có được do... chính ngân hàng có thể vỡ nợ (vì nếu vỡ nợ, ngân hàng không phải trả các khoản đang nợ đối tác).
*   $Giá\_trị\_thực = Giá\_trị\_không\_rủi\_ro - CVA + DVA$
*   **Nghịch lý DVA:** Khi sức khỏe tài chính của ngân hàng xấu đi (credit spread của chính ngân hàng tăng), DVA tăng lên. Về mặt kế toán, điều này được ghi nhận là một khoản **lợi nhuận khổng lồ** trên báo cáo kết quả kinh doanh. Điều này rất kỳ cục và Basel III đã cấm các ngân hàng đưa lợi nhuận từ DVA vào tính toán vốn tự có (CET1).

---
**Ghi chú:** Tính toán CVA là một trong những bài toán tốn kém năng lực điện toán nhất trong ngân hàng hiện đại vì phải chạy Monte Carlo trên toàn bộ danh mục của từng đối tác.
