# Chương 10: Biến động (Volatility)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Định nghĩa Biến động (Definition of Volatility)
*   **Volatility ($\sigma$):** Là độ lệch chuẩn của tỷ suất sinh lời (return) của tài sản trong một đơn vị thời gian.
*   Trong định giá quyền chọn, đơn vị thời gian thường là 1 năm. Trong quản trị rủi ro, đơn vị thường là 1 ngày.
*   **Quy tắc căn bậc hai của thời gian:** Biến động trong $T$ ngày bằng biến động 1 ngày nhân với $\sqrt{T}$.
    *   $\sigma_{năm} = \sigma_{ngày} \cdot \sqrt{252}$ (Giả định có 252 ngày giao dịch mỗi năm).

## 2. Biến động Hàm ý và Chỉ số VIX (Implied Volatilities)
*   **Implied Volatility:** Là mức biến động được tính ngược từ giá thị trường của quyền chọn thông qua mô hình Black-Scholes-Merton. Nó phản ánh kỳ vọng của thị trường về rủi ro trong tương lai.
*   **VIX Index:** Chỉ số đo lường biến động hàm ý của các quyền chọn chỉ số S&P 500 trong thời hạn 30 ngày tới. Đây được gọi là "Chỉ số sợ hãi" của thị trường.

## 3. Bản chất của Lợi nhuận Tài sản (Nature of Returns)
*   **Không phân phối chuẩn:** Thực tế cho thấy các biến số tài chính có hiện tượng **"Đuôi béo" (Heavy Tails / Fat Tails)**. Các biến động cực đại (như 3-6 lần độ lệch chuẩn) xảy ra thường xuyên hơn nhiều so với dự đoán của phân phối chuẩn.
*   **The Power Law (Quy luật lũy thừa):** Một phương pháp thay thế để mô tả các biến động cực đoan ở phần đuôi của phân phối.

## 4. Các Mô hình Giám sát Biến động Hàng ngày
Nguyên tắc: Dữ liệu gần đây quan trọng hơn dữ liệu cũ.
### 4.1. EWMA (Exponentially Weighted Moving Average)
*   Trọng số giảm dần theo cấp số nhân khi lùi sâu về quá khứ.
*   **Công thức:** $\sigma_n^2 = \lambda \sigma_{n-1}^2 + (1-\lambda) u_{n-1}^2$
    *   Trong đó $\lambda$ thường được chọn là 0.94 (theo chuẩn RiskMetrics của JPMorgan).
    *   Ưu điểm: Lưu trữ dữ liệu ít (chỉ cần biến động ngày hôm qua và lợi nhuận mới nhất).

### 4.2. GARCH(1,1) Model
*   Là mở rộng của EWMA, bổ sung thêm yếu tố **"Biến động dài hạn" (Long-run average variance - $V_L$)**.
*   **Công thức:** $\sigma_n^2 = \omega + \alpha u_{n-1}^2 + \beta \sigma_{n-1}^2$
    *   Trong đó $\alpha + \beta < 1$ để đảm bảo mô hình ổn định.
*   **Mean Reversion:** Điểm khác biệt lớn nhất của GARCH so với EWMA là nó giả định biến động sẽ có xu hướng quay về mức trung bình dài hạn theo thời gian.

## 5. Phương pháp Ước lượng Tham số (Maximum Likelihood Methods)
*   Để tìm ra các tham số tối ưu ($\omega, \alpha, \beta$) cho mô hình GARCH từ dữ liệu lịch sử, các nhà toán học sử dụng phương pháp **Maximum Likelihood (Hàm hợp lý tối đa)**.
*   Mục tiêu là tìm các tham số sao cho xác suất xảy ra bộ dữ liệu quan sát được là cao nhất.

## 6. Dự báo Biến động tương lai
*   Mô hình GARCH(1,1) cho phép dự báo biến động cho ngày $n+t$. Khi $t$ càng lớn, dự báo sẽ tiến dần về mức biến động dài hạn $V_L$.
*   **Cấu trúc kỳ hạn của biến động (Volatility Term Structure):** Giải thích tại sao biến động hàm ý cho các quyền chọn ngắn hạn thường thay đổi mạnh hơn các quyền chọn dài hạn.

---
**Ghi chú quan trọng:**
*   **Volatility Clustering (Gom cụm biến động):** Biến động có xu hướng duy trì. Nếu hôm nay thị trường biến động mạnh, xác suất ngày mai tiếp tục biến động mạnh là rất cao.
*   **GARCH vs EWMA:** GARCH phù hợp hơn khi bạn tin rằng rủi ro sẽ quay về mức trung bình. EWMA thực chất là một trường hợp đặc biệt của GARCH khi mức trung bình dài hạn không tồn tại.
*   Trong dự án **Finvista** của bạn, việc cài đặt mô hình GARCH(1,1) sẽ giúp đánh giá rủi ro CW (Chứng quyền có bảo đảm) chính xác hơn nhiều so với việc chỉ dùng độ lệch chuẩn đơn giản.
