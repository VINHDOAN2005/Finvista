# Chương 16: Basel II.5, Basel III và Các thay đổi Hậu Khủng hoảng
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Basel II.5 (Thực thi cuối 2011)
Nhận thấy Basel II đánh giá quá thấp rủi ro trong "Trading Book", Ủy ban Basel đã đưa ra các bổ sung (gọi là Basel II.5) làm tăng mạnh yêu cầu vốn:
*   **Stressed VaR:** Yêu cầu tính thêm VaR trong một chu kỳ 250 ngày "căng thẳng nhất" đối với danh mục hiện tại. Vốn = Vốn (VaR bình thường) + Vốn (Stressed VaR). Việc này khiến vốn yêu cầu cho rủi ro thị trường tăng gấp đôi hoặc gấp ba.
*   **Incremental Risk Charge (IRC):** Tính vốn dựa trên VaR 99.9% 1 năm cho rủi ro vỡ nợ (default) và giảm hạng tín nhiệm (migration) của các tài sản trong Trading Book, xóa bỏ lợi thế "trọng tài quy định" (Regulatory Arbitrage) giữa Banking Book và Trading Book.
*   **Comprehensive Risk Measure (CRM):** Mức vốn riêng cho các sản phẩm phụ thuộc vào tương quan tín dụng (như ABS CDO).

## 2. Basel III (Được thống nhất năm 2010, áp dụng dần đến 2019)
Một cuộc đại tu toàn diện để tăng cường khả năng chịu sốc của hệ thống ngân hàng.

### 2.1. Định nghĩa và Yêu cầu Vốn chặt chẽ hơn
*   **Vốn cấp 1 nòng cốt (CET1 - Common Equity Tier 1):** Tăng yêu cầu tối thiểu từ 2% lên **4.5%**. Vốn phải thực chất hơn (loại trừ lợi thế thương mại, tài sản thuế hoãn lại).
*   **Tier 1 Capital:** Tăng từ 4% lên **6%**.
*   **Tổng Vốn (Total Capital):** Giữ nguyên mức **8%**.

### 2.2. Các Đệm Vốn (Capital Buffers)
*   **Capital Conservation Buffer (Đệm bảo toàn vốn):** Yêu cầu giữ thêm **2.5%** CET1 trong thời kỳ bình thường. Nếu vốn rơi vào vùng đệm này, ngân hàng sẽ bị hạn chế trả cổ tức và tiền thưởng.
*   **Countercyclical Buffer (Đệm ngược chu kỳ):** Yêu cầu giữ thêm từ **0% - 2.5%** tùy theo chu kỳ kinh tế do cơ quan quản lý quốc gia quyết định, nhằm ngăn chặn việc cho vay quá đà khi nền kinh tế bùng nổ.

### 2.3. Tỷ lệ Đòn bẩy (Leverage Ratio)
Để tránh việc các ngân hàng lạm dụng mô hình nội bộ để tính RWA (Tài sản có rủi ro trọng số) quá thấp, Basel III áp đặt một ngưỡng tối thiểu: **Vốn Tier 1 / Tổng tài sản (không điều chỉnh rủi ro) $\ge$ 3%**. (Một số nước như Mỹ, Anh yêu cầu tỷ lệ cao hơn).

### 2.4. Rủi ro Thanh khoản (Liquidity Risk)
Khủng hoảng 2008 là một cuộc khủng hoảng thanh khoản. Lần đầu tiên, Basel đưa ra yêu cầu về thanh khoản:
*   **LCR (Liquidity Coverage Ratio):** Tỷ lệ bao phủ thanh khoản. Yêu cầu ngân hàng phải có đủ "Tài sản thanh khoản chất lượng cao" (HQLA) để sống sót qua một kịch bản căng thẳng kéo dài **30 ngày**. ($LCR \ge 100\%$).
*   **NSFR (Net Stable Funding Ratio):** Tỷ lệ nguồn vốn tài trợ ổn định thuần. Đảm bảo các tài sản dài hạn phải được tài trợ bằng nguồn vốn dài hạn và ổn định trong vòng **1 năm**, hạn chế việc lấy vốn vay bán buôn ngắn hạn (wholesale funding) đi cho vay dài hạn.

### 2.5. Counterparty Credit Risk (Rủi ro Tín dụng Đối tác - CVA)
*   Bắt buộc tính vốn cho rủi ro **CVA (Credit Value Adjustment)** - rủi ro tổn thất do chênh lệch tín dụng (credit spread) của đối tác giao dịch phái sinh OTC tăng lên (ngay cả khi đối tác chưa vỡ nợ).

### 2.6. G-SIBs (Ngân hàng có tầm quan trọng hệ thống toàn cầu)
*   Nhóm ngân hàng "quá lớn để sụp đổ" (Too big to fail) như JPMorgan, HSBC, v.v., sẽ phải chịu thêm mức phụ phí vốn (surcharge) từ **1% đến 3.5%** CET1.
*   Yêu cầu về **TLAC (Total Loss-Absorbing Capacity)**: Phải có đủ vốn và nợ có thể chuyển đổi thành cổ phần (bail-in) để tự cứu mình mà không cần dùng tiền thuế của dân.

## 3. Trái phiếu Chuyển đổi Dự phòng (CoCo Bonds)
*   Một sáng tạo tài chính hậu khủng hoảng. Đây là trái phiếu tự động chuyển thành cổ phiếu khi tỷ lệ vốn của ngân hàng giảm xuống dưới một "trigger" nhất định (ví dụ: CET1 < 7%).
*   Giúp ngân hàng tự động tăng vốn cổ phần trong lúc nguy cấp (Bail-in) thay vì chờ chính phủ cứu trợ (Bail-out).

## 4. Đạo luật Dodd-Frank (Mỹ)
Đạo luật sâu rộng của Mỹ nhằm bảo vệ người tiêu dùng và giám sát rủi ro hệ thống:
*   **Volcker Rule:** Cấm các ngân hàng nhận tiền gửi tham gia vào "Proprietary Trading" (Giao dịch tự doanh - dùng tiền của ngân hàng để đầu cơ) và hạn chế đầu tư vào quỹ đầu cơ.
*   Yêu cầu phần lớn phái sinh OTC phải được thanh toán qua trung tâm bù trừ (CCPs) và giao dịch trên các nền tảng minh bạch (SEFs).
*   Yêu cầu các ngân hàng lớn phải lập "Living Wills" (Di chúc sống) phác thảo cách họ có thể bị thanh lý một cách trật tự nếu phá sản.
*   Buộc tổ chức phát hành chứng khoán hóa (Securitization) phải giữ lại 5% rủi ro (Skin in the game).

---
**Ghi chú:** Kỷ nguyên hậu 2008 chứng kiến sự chuyển dịch từ việc chỉ tập trung vào vốn (Solvency) sang việc kiểm soát chặt chẽ cả thanh khoản (Liquidity) và cấu trúc hệ thống (Systemic Risk).
