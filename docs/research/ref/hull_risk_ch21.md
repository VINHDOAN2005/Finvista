# Chương 21: Giá trị Chịu Rủi ro Tín dụng (Credit Value at Risk)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Credit VaR là gì?
Tương tự như Market VaR, **Credit VaR** là khoản lỗ tín dụng sẽ không bị vượt quá trong một khoảng thời gian nhất định với một độ tin cậy nhất định.
*   **Mục đích:** Dùng để tính toán Vốn quy định (Regulatory Capital - theo chuẩn Basel) và Vốn kinh tế (Economic Capital - do ngân hàng tự tính).
*   **Thời gian (Horizon):** Thường là 1 năm (dài hơn nhiều so với 1-10 ngày của Market VaR).
*   **Xác suất:** Sử dụng **Xác suất Thế giới thực (Real-world probabilities)** vì đây là bài toán phân tích kịch bản (Scenario Analysis), không phải bài toán định giá (Valuation).

## 2. Ma trận Chuyển đổi Hạng Tín nhiệm (Ratings Transition Matrices)
Để tính toán tổn thất tín dụng, các ngân hàng cần biết xác suất một khoản vay bị giảm hạng (downgrade) hoặc vỡ nợ (default).
*   **Transition Matrix:** Bảng thể hiện xác suất một công ty chuyển từ hạng tín nhiệm hiện tại sang một hạng khác (hoặc vỡ nợ) trong một khoảng thời gian (ví dụ: 1 năm). Được cung cấp bởi các tổ chức như Moody's, S&P, hoặc dữ liệu nội bộ.
*   **Tính chất:** Nếu giả định sự thay đổi hạng tín nhiệm giữa các kỳ là độc lập (thường không hoàn toàn đúng trong thực tế do có hiện tượng "quán tính" - rating momentum), ta có thể tính ma trận chuyển đổi cho $m$ năm bằng cách lấy ma trận 1 năm mũ $m$ ($A^m$).

## 3. Mô hình của Vasicek (Vasicek's Model)
Đây là mô hình nền tảng cho phương pháp IRB trong Basel II (đã học ở Chương 15).
*   Dựa trên mô hình **Gaussian Copula một nhân tố** để đánh giá tương quan vỡ nợ giữa các khoản vay. Nhân tố duy nhất ở đây ($F$) đại diện cho tình hình kinh tế vĩ mô.
*   **Công thức tính Tỷ lệ vỡ nợ tồi tệ nhất (WCDR - Worst Case Default Rate):**
    $$WCDR(T, X) = N\left( \frac{N^{-1}(PD) + \sqrt{\rho}N^{-1}(X)}{\sqrt{1-\rho}} \right)$$
    *   $PD$: Xác suất vỡ nợ trung bình 1 năm.
    *   $\rho$: Tương quan Copula (Copula correlation).
    *   $X$: Mức độ tin cậy (Ví dụ: 99.9%).
*   Từ WCDR, ngân hàng tính được tổn thất đuôi: $\sum (EAD_i \times LGD_i \times WCDR_i)$. Phần vượt quá tổn thất kỳ vọng (Expected Loss) chính là Vốn yêu cầu (Capital).

## 4. Mô hình Credit Risk Plus
Được phát triển bởi Credit Suisse (1997), mô hình này mượn ý tưởng từ ngành bảo hiểm.
*   **Nguyên lý:** Nó chỉ quan tâm đến **tổn thất do vỡ nợ (defaults)**, KHÔNG quan tâm đến tổn thất do giảm hạng (downgrades).
*   **Cách tính:** 
    *   Giả định tỷ lệ vỡ nợ trung bình $q$ là một biến ngẫu nhiên tuân theo phân phối Gamma.
    *   Số lượng vỡ nợ thực tế tuân theo phân phối Poisson (nếu $q$ cố định) hoặc phân phối Nhị thức âm (Negative Binomial) (khi $q$ biến thiên).
*   Mô hình này có thể giải quyết bằng các phương pháp giải tích hoặc mô phỏng Monte Carlo.

## 5. Mô hình CreditMetrics
Được phát triển bởi JPMorgan (1997).
*   **Nguyên lý:** Phức tạp và toàn diện hơn Credit Risk Plus vì nó tính toán tổn thất từ **cả vỡ nợ VÀ sự giảm hạng tín nhiệm (downgrades)**.
*   Sử dụng **Ma trận chuyển đổi (Transition Matrix)**.
*   **Quá trình Monte Carlo:**
    1.  Mô phỏng sự thay đổi hạng tín nhiệm của mọi đối tác trong danh mục vào cuối năm thứ 1. Sự thay đổi này được liên kết với nhau bằng một Gaussian Copula (tương quan thường dựa trên tương quan giá cổ phiếu của các công ty).
    2.  Nếu đối tác vỡ nợ: Tổn thất = EAD * LGD.
    3.  Nếu đối tác không vỡ nợ (nhưng bị giảm/tăng hạng): Định giá lại toàn bộ các giao dịch phái sinh/khoản vay với đối tác đó dựa trên đường cong Credit Spread mới (tương ứng với hạng mới). Chênh lệch giá trị chính là khoản lỗ/lãi tín dụng.
    4.  Lặp lại hàng ngàn lần để vẽ ra phân phối tổn thất tín dụng tổng thể và tìm ra VaR 99.9%.

## 6. Rủi ro Chênh lệch Tín dụng (Credit Spread Risk)
Giá trị của các sản phẩm nhạy cảm với tín dụng trong Sổ giao dịch (Trading Book) phụ thuộc mạnh vào Credit Spreads.
*   Để tính VaR cho các sản phẩm này, người ta thường dùng phương pháp **Mô phỏng lịch sử (Historical Simulation)** tương tự như rủi ro thị trường, bằng cách lấy chuỗi dữ liệu thay đổi credit spread trong quá khứ.
*   Cách khác là dùng CreditMetrics, mô phỏng sự chuyển đổi hạng tín nhiệm và định giá lại danh mục.

---
**Ghi chú so sánh:** 
*   **Vasicek & Credit Risk Plus:** Chỉ đánh giá rủi ro Vỡ nợ (Default-only models).
*   **CreditMetrics:** Đánh giá cả rủi ro Vỡ nợ và rủi ro Giảm hạng (Mark-to-market model). CreditMetrics cung cấp một bức tranh toàn diện hơn về rủi ro tín dụng.
