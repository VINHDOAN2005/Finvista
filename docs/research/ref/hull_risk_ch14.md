# Chương 14: Phương pháp Xây dựng Mô hình (Model-Building Approach)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Phương pháp luận cơ bản (The Basic Methodology)
*   **Tên gọi khác:** Phương pháp Phương sai - Hiệp phương sai (Variance-Covariance Approach) hoặc Phương pháp tham số (Parametric Approach).
*   **Nguyên lý:** Giả định rằng biến động phần trăm hàng ngày của các biến số thị trường tuân theo **phân phối chuẩn nhiều chiều (multivariate normal distribution)**.
*   **Trường hợp tuyến tính:** Nếu danh mục chỉ bao gồm các sản phẩm tuyến tính (như cổ phiếu, hợp đồng kỳ hạn), thì sự thay đổi giá trị của toàn bộ danh mục cũng sẽ tuân theo phân phối chuẩn.
*   **Quy trình tính VaR:**
    1. Tính độ lệch chuẩn ($\sigma$) của sự thay đổi giá trị danh mục dựa trên Delta của các tài sản, biến động ($\sigma$) của từng tài sản và hệ số tương quan ($\rho$) giữa chúng.
    2. Lấy $\sigma$ nhân với hệ số phân vị của phân phối chuẩn (ví dụ: $2.326$ cho mức 99%) để ra VaR 1 ngày.
    3. Nhân với $\sqrt{T}$ để ra VaR cho $T$ ngày.

## 2. Tổng quát hóa bằng Đại số Ma trận (Generalization)
Sự thay đổi giá trị danh mục ($\Delta P$) được biểu diễn qua ma trận:
$$\sigma_P^2 = \delta^T C \delta$$
*   Trong đó: $\delta$ là vector cột các giá trị Delta (độ nhạy của danh mục với từng biến số), $C$ là ma trận hiệp phương sai (Variance-Covariance matrix), và $\delta^T$ là ma trận chuyển vị của $\delta$.
*   Phương pháp này có nguồn gốc từ Lý thuyết Danh mục đầu tư của Markowitz.

## 3. Xử lý Cấu trúc Kỳ hạn (Handling Term Structures)
Các biến số như lãi suất không phải là một con số duy nhất mà là một đường cong (Yield Curve).
*   **Vấn đề:** Nếu dùng mỗi điểm trên đường cong làm một biến số rủi ro thì ma trận tương quan sẽ quá lớn và phức tạp.
*   **Giải pháp 1 - PCA (Phân tích thành phần chính):** Dùng PCA để giảm số lượng biến số xuống còn 2-3 nhân tố chính (Dịch chuyển song song, Thay đổi độ dốc, Thay đổi độ cong) như đã học ở Chương 9.
*   **Giải pháp 2 - Multiple Vertices Approach:** Định nghĩa đường cong bằng một số điểm neo (node). Tính Delta cho từng điểm neo này (Node Deltas). Phương pháp này được các cơ quan quản lý và các dealer ưa chuộng.

## 4. Rủi ro phi tuyến tính và Gamma (Handling Non-Linearity)
Điểm yếu chí mạng của phương pháp Model-Building là khi danh mục có chứa quyền chọn (options), mối quan hệ giữa giá trị danh mục và tài sản cơ sở là phi tuyến tính. Phân phối của danh mục không còn là phân phối chuẩn (nó bị lệch - skewed).
*   **Gamma dương:** Làm phân phối lệch phải (ít rủi ro ở đuôi trái hơn so với phân phối chuẩn). Nếu dùng phân phối chuẩn, VaR sẽ bị ước lượng **quá cao**.
*   **Gamma âm:** Làm phân phối lệch trái (rủi ro đuôi rất lớn). Nếu dùng phân phối chuẩn, VaR sẽ bị ước lượng **quá thấp** (rất nguy hiểm).

### Cách xử lý:
1.  **Mô phỏng Monte Carlo (Monte Carlo Simulation):** Tạo ra hàng ngàn đường dẫn ngẫu nhiên cho các biến số thị trường dựa trên ma trận hiệp phương sai (dùng phân tích Cholesky). Sau đó định giá lại danh mục. (Cách này chính xác nhưng mất đi ưu thế tốc độ của Model-Building).
2.  **Khai triển Cornish-Fisher:** Tính toán không chỉ phương sai (bậc 2), mà cả độ lệch (skewness - bậc 3) và độ nhọn (kurtosis - bậc 4) của phân phối danh mục bằng định lý Isserlis. Sau đó dùng công thức Cornish-Fisher để điều chỉnh hệ số phân vị ($Z$-score) của phân phối chuẩn, từ đó tính ra VaR chính xác hơn mà không cần mô phỏng.

## 5. So sánh: Model-Building vs. Historical Simulation
*   **Model-Building:** Rất nhanh, lý thuyết đẹp, dễ dàng kết hợp với các mô hình cập nhật biến động liên tục (như EWMA, GARCH). Rất phù hợp cho danh mục đầu tư (investment portfolios) chủ yếu là cổ phiếu/trái phiếu.
*   **Historical Simulation:** Chậm hơn, nhưng bắt được hoàn hảo các rủi ro đuôi béo (fat tails) và rủi ro phi tuyến tính (options) mà không cần giả định phân phối chuẩn khó nhằn. Phù hợp cho danh mục giao dịch (trading books) phức tạp của các ngân hàng.

---
**Lưu ý quan trọng cho FRTB (Basel mới):** Trong Phương pháp Tiêu chuẩn (Standardized Approach) của FRTB (sẽ học ở Chương 18), Basel yêu cầu sử dụng các **Risk Weights (Trọng số rủi ro)** và **Weighted Sensitivities (Độ nhạy có trọng số)**. Đây chính là một sự áp dụng trực tiếp của phương pháp Model-Building này.
