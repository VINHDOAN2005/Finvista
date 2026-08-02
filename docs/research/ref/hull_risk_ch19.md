# Chương 19: Ước lượng Xác suất Vỡ nợ (Estimating Default Probabilities)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Xếp hạng Tín dụng (Credit Ratings)
*   Được cung cấp bởi các tổ chức như Moody’s, S&P, Fitch.
*   Họ thường đánh giá **"through the cycle" (xuyên suốt chu kỳ)**, nghĩa là xếp hạng của họ ít biến động và không phản ứng ngay lập tức với các thay đổi ngắn hạn của thị trường.
*   **Chỉ số Z-Score của Altman (1968):** Một mô hình kinh điển dùng các tỷ số tài chính kế toán (như Vốn lưu động/Tổng tài sản, Lợi nhuận giữ lại/Tổng tài sản...) để dự báo nguy cơ phá sản.

## 2. Xác suất Vỡ nợ Lịch sử (Historical Default Probabilities)
*   **Xác suất vô điều kiện (Unconditional):** Xác suất một công ty vỡ nợ vào năm thứ $t$ nhìn từ thời điểm hiện tại.
*   **Tỷ lệ rủi ro (Hazard Rate / Default Intensity - $\lambda$):** Tốc độ vỡ nợ tại một thời điểm $t$, với điều kiện công ty chưa vỡ nợ trước đó.
*   **Công thức:** Xác suất vỡ nợ lũy kế đến năm $T$ là $Q(T) = 1 - e^{-\bar{\lambda}T}$, trong đó $\bar{\lambda}$ là hazard rate trung bình.

## 3. Tỷ lệ Thu hồi (Recovery Rates - $R$)
*   Là phần trăm mệnh giá trái phiếu mà nhà đầu tư lấy lại được sau khi công ty vỡ nợ (ví dụ: 40%).
*   **Tương quan nghịch:** Trong những năm nền kinh tế suy thoái, tỷ lệ vỡ nợ tăng lên thì tỷ lệ thu hồi lại giảm xuống. Điều này làm rủi ro tín dụng tồi tệ hơn gấp bội.

## 4. Hợp đồng Hoán đổi Rủi ro Tín dụng (Credit Default Swaps - CDS)
*   Là một dạng bảo hiểm rủi ro vỡ nợ. Người mua CDS trả một khoản phí định kỳ (CDS Spread) cho người bán. Nếu công ty tham chiếu (Reference Entity) vỡ nợ, người bán bồi thường cho người mua.
*   **CDS Spread:** Được báo giá dưới dạng điểm cơ bản (basis points) trên mệnh giá.
*   **Sự cố thanh toán (Credit Event):** Gồm phá sản, không trả được nợ, hoặc tái cấu trúc nợ.
*   Có thể thanh toán bằng tiền mặt (cash settlement) thông qua một cuộc đấu giá để xác định giá của trái phiếu rẻ nhất có thể giao giao (cheapest-to-deliver bond).

## 5. Ước lượng Xác suất Vỡ nợ từ Credit Spreads
*   **Credit Spread ($s$):** Là phần bù rủi ro (lợi suất trái phiếu doanh nghiệp trừ đi lãi suất phi rủi ro). CDS spread là một thước đo trực tiếp của credit spread.
*   **Công thức ước lượng nhanh:** Hazard rate $\lambda = \frac{s}{1-R}$
    *   *Ví dụ:* Nếu CDS spread = 200 bps (2%) và Recovery Rate = 40%, thì xác suất vỡ nợ mỗi năm $\lambda = \frac{0.02}{1-0.4} = 3.33\%$.

## 6. Real-World vs. Risk-Neutral Probabilities (Thế giới thực vs. Rủi ro trung tính)
Đây là một sự phân biệt mang tính quyết định:
*   **Risk-Neutral PD (Xác suất rủi ro trung tính):** Được trích xuất từ **Credit Spreads / CDS prices**. Được sử dụng để **Định giá (Valuation)** các sản phẩm phái sinh tín dụng.
*   **Real-World PD (Xác suất thế giới thực):** Được tính từ **Dữ liệu lịch sử (Historical data)**. Được sử dụng để tính **VaR, Expected Shortfall** và Phân tích kịch bản.
*   **So sánh:** Risk-neutral PD **luôn lớn hơn rất nhiều** so với Real-world PD. Điều này là do Credit Spread không chỉ bù đắp cho rủi ro vỡ nợ thực tế, mà còn bao gồm **phần bù rủi ro (Risk Premium)** cho tính thanh khoản kém và rủi ro hệ thống (systemic risk - các công ty có xu hướng vỡ nợ cùng lúc).

## 7. Ước lượng bằng Giá Cổ phiếu: Mô hình Merton (1974)
Thay vì chờ đợi các tổ chức xếp hạng phản ứng chậm chạp, ta có thể dùng giá cổ phiếu để dự báo xác suất vỡ nợ.
*   **Nguyên lý:** Vốn chủ sở hữu của một công ty có thể được coi là một **Quyền chọn mua (Call Option)** trên tổng tài sản của công ty đó, với giá thực hiện (Strike Price) chính là tổng Nợ ($D$).
    *   Năm đáo hạn nợ, nếu Giá trị Tài sản > Nợ: Cổ đông trả nợ và giữ phần dư (Thực hiện quyền).
    *   Nếu Giá trị Tài sản < Nợ: Công ty vỡ nợ, cổ đông bỏ đi, giá trị vốn chủ = 0 (Bỏ quyền).
*   Sử dụng công thức Black-Scholes-Merton kết hợp với giá trị và biến động của vốn chủ sở hữu, ta có thể giải hệ phương trình để tìm ra Giá trị Tài sản và Biến động Tài sản.
*   **Distance to Default (Khoảng cách đến vỡ nợ):** Chỉ số cho biết giá trị tài sản phải giảm bao nhiêu độ lệch chuẩn thì công ty mới chạm ngưỡng vỡ nợ. Mô hình KMV của Moody's dựa trên nguyên lý này để chuyển đổi từ mô hình Merton sang Real-world PD.

---
**Ghi chú:** Việc nhầm lẫn giữa xác suất thế giới thực và xác suất rủi ro trung tính là một lỗi rất phổ biến. Định giá (Pricing) thì dùng dữ liệu thị trường (Risk-neutral), còn Quản trị rủi ro (Risk Management) thì dùng dữ liệu thực tế (Real-world).
