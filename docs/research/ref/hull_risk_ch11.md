# Chương 11: Tương quan và Copulas (Correlations and Copulas)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Tương quan vs. Phụ thuộc (Correlation vs. Dependence)
*   **Correlation (Tương quan - $\rho$):** Chỉ đo lường sự phụ thuộc **tuyến tính** giữa hai biến. Hệ số tương quan bằng 0 không có nghĩa là hai biến hoàn toàn độc lập (chúng có thể phụ thuộc theo hình chữ V hoặc phi tuyến tính).
*   **Tương quan trong điều kiện căng thẳng:** Thực tế chứng minh, khi thị trường sụp đổ, mức độ tương quan giữa các tài sản tăng vọt (mọi thứ cùng giảm). Việc chỉ dựa vào hệ số tương quan tuyến tính tĩnh là một sai lầm lớn.

## 2. Giám sát Tương quan (Monitoring Correlation)
*   Tương tự như biến động (Volatility), Hiệp phương sai (Covariance) giữa hai biến số cũng thay đổi theo thời gian.
*   **Mô hình EWMA cho Hiệp phương sai:**
    $$cov_n = \lambda cov_{n-1} + (1-\lambda)x_{n-1}y_{n-1}$$
*   **Mô hình GARCH(1,1) cho Hiệp phương sai:**
    $$cov_n = \omega + \alpha x_{n-1}y_{n-1} + \beta cov_{n-1}$$
    *(Trong đó $x$ và $y$ là lợi nhuận hàng ngày của hai tài sản).*

## 3. Ma trận Tương quan và Hiệp phương sai (Matrices)
*   Trong quản trị rủi ro, chúng ta thường làm việc với hàng trăm biến số, dẫn đến một ma trận hiệp phương sai khổng lồ.
*   **Điều kiện Positive-semidefinite:** Để ma trận hợp lệ (không tạo ra phương sai danh mục âm), nó phải thỏa mãn điều kiện positive-semidefinite. Việc điều chỉnh tùy tiện một vài hệ số tương quan trong ma trận lớn thường sẽ phá vỡ cấu trúc này.

## 4. Mô hình Nhân tố (Factor Models)
*   Giúp đơn giản hóa ma trận tương quan. Thay vì tính tương quan giữa từng cặp tài sản (cần hàng ngàn phép tính), ta giả định mọi tài sản đều phản ứng với một hoặc nhiều "nhân tố" chung (như GDP, chỉ số thị trường).
*   Ví dụ: CAPM là một mô hình 1 nhân tố.

## 5. Copulas (Hàm liên kết)
Đây là công cụ toán học đột phá giúp xây dựng phân phối đồng thời (joint distribution) của nhiều biến số khi ta chỉ biết phân phối riêng lẻ (marginal distribution) của từng biến.
*   **Quy trình của Copula:**
    1.  Chuyển đổi phân phối thực tế của từng biến (có thể là đuôi béo, bất đối xứng) sang **phân phối chuẩn tắc** thông qua phương pháp khớp phân vị (percentile-to-percentile).
    2.  Áp dụng tương quan trên các biến chuẩn tắc mới này (tạo ra Multivariate Normal Distribution).
*   **Gaussian Copula:** Dùng phân phối chuẩn để liên kết.
*   **Student's t-Copula:** Dùng phân phối t-Student. Nó mô tả hiện tượng **Tail Dependence** (Sự phụ thuộc ở phần đuôi) tốt hơn Gaussian Copula. Nghĩa là xác suất hai tài sản cùng sụp đổ cùng lúc cao hơn.

## 6. Ứng dụng: Mô hình Vasicek cho Danh mục Cho vay
*   Mô hình Gaussian Copula một nhân tố của Vasicek (1987) là nền tảng cốt lõi cho quy định vốn **Basel II (IRB Approach)**.
*   Mô hình này tính toán **Worst Case Default Rate (WCDR)** – tỷ lệ vỡ nợ tồi tệ nhất trong danh mục cho vay tại một mức độ tin cậy nhất định (ví dụ 99.9%).
*   **Công thức Vasicek:**
    $$WCDR = N\left( \frac{N^{-1}(PD) + \sqrt{\rho}N^{-1}(X)}{\sqrt{1-\rho}} \right)$$
    *   Trong đó: $PD$ là xác suất vỡ nợ trung bình, $\rho$ là tương quan copula, $X$ là mức độ tin cậy (như 0.999), $N$ là hàm phân phối chuẩn tích lũy.

---
**Ghi chú quan trọng:**
*   **Copulas** là con dao hai lưỡi. Chúng giúp các ngân hàng định giá được CDO một cách dễ dàng, nhưng việc lạm dụng quá mức **Gaussian Copula** (đánh giá thấp rủi ro tương quan đuôi - Tail Dependence) đã đóng góp một phần không nhỏ vào sự sụp đổ của thị trường năm 2008. Tạp chí Wired từng gọi công thức Gaussian Copula của David Li là "Công thức giết chết Phố Wall".
