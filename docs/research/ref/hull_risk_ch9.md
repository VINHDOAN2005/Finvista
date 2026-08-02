# Chương 9: Rủi ro Lãi suất (Interest Rate Risk)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Quản lý Thu nhập Lãi thuần (Net Interest Income - NII)
*   **Net Interest Margin (NIM):** Là tỷ lệ giữa NII (lãi nhận được trừ lãi phải trả) trên tổng tài sản sinh lời.
*   **Asset-Liability Management (ALM):** Nhiệm vụ của bộ phận ALM là đảm bảo NIM ổn định bất kể biến động lãi suất.
*   **Liquidity Preference Theory (Thuyết ưu tiên thanh khoản):** Giải thích tại sao lãi suất dài hạn thường cao hơn lãi suất ngắn hạn do nhà đầu tư yêu cầu phần bù cho việc bị đọng vốn lâu.

## 2. Các loại Lãi suất Quan trọng
1.  **Treasury Rates (Lãi suất trái phiếu chính phủ):** Được xem là lãi suất phi rủi ro thực tế (risk-free rates) nhưng thường quá thấp do ưu đãi thuế và quy định vốn.
2.  **LIBOR (London Interbank Offered Rate):** Lãi suất cho vay không tài sản đảm bảo giữa các ngân hàng xếp hạng AA. Hiện nay đang dần bị thay thế.
3.  **OIS Rates (Overnight Indexed Swap):** Lãi suất hoán đổi dựa trên lãi suất qua đêm (như Fed Funds rate). Sau 2008, OIS được coi là thước đo lãi suất phi rủi ro chính xác hơn LIBOR.
4.  **Repo Rates (Lãi suất mua lại):** Lãi suất cho vay có tài sản đảm bảo (thường là trái phiếu chính phủ). Đây là lãi suất thấp nhất trên thị trường.

## 3. Thời lượng (Duration)
*   **Macaulay’s Duration:** Trung bình trọng số thời gian nhận được các dòng tiền từ một trái phiếu.
*   **Modified Duration:** Đo lường độ nhạy của giá trái phiếu khi lãi suất thay đổi.
*   **Công thức:** $\Delta B \approx -D \cdot B \cdot \Delta y$
    *   Trong đó $D$ là Modified Duration, $B$ là giá trái phiếu, $\Delta y$ là mức thay đổi lợi suất.

## 4. Độ lồi (Convexity)
*   Duration chỉ là một ước lượng tuyến tính. Khi lãi suất thay đổi lớn, Duration không còn chính xác.
*   **Convexity ($C$):** Đo lường độ cong của mối quan hệ giá-lợi suất.
*   **Công thức cải tiến:** $\frac{\Delta B}{B} \approx -D \cdot \Delta y + \frac{1}{2} C \cdot (\Delta y)^2$
*   Một danh mục có Convexity dương sẽ tăng giá nhanh hơn khi lãi suất giảm và giảm giá chậm hơn khi lãi suất tăng (đây là đặc tính có lợi).

## 5. Các biến động của Đường cong Lợi suất (Yield Curve)
*   **Parallel Shift:** Tất cả các kỳ hạn tăng/giảm cùng một lượng. Duration và Convexity xử lý tốt trường hợp này.
*   **Non-parallel Shifts:** Đường cong lợi suất có thể xoay (twist) hoặc cong (bowing).
*   **Partial Duration (Thời lượng bộ phận):** Chia đường cong thành các đoạn (buckets) và tính độ nhạy cho từng đoạn riêng lẻ.

## 6. Phân tích Thành phần Chính (Principal Components Analysis - PCA)
Để quản lý rủi ro từ các biến động phức tạp của đường cong lợi suất, PCA xác định các "nhân tố" chính:
1.  **PC1 (Level):** Dịch chuyển song song (giải thích ~90% biến động).
2.  **PC2 (Slope):** Thay đổi độ dốc/xoay đường cong.
3.  **PC3 (Curvature):** Thay đổi độ cong.
*   Phương pháp này giúp giảm số lượng biến số cần theo dõi (từ 10-15 loại lãi suất xuống còn 2-3 nhân tố chính).

---
**Ghi chú quan trọng:**
*   **Immunization (Miễn dịch danh mục):** Thiết lập Duration của tài sản bằng Duration của nợ phải trả để bảo vệ giá trị vốn chủ sở hữu trước biến động lãi suất.
*   **LIBOR-OIS Spread:** Thước đo căng thẳng trên thị trường tài chính. Spread tăng cao cho thấy các ngân hàng đang lo ngại về rủi ro vỡ nợ của nhau.
