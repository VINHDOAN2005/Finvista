# Chương 8: Cách các Trader Quản trị Rủi ro (How Traders Manage Their Risks)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Giới thiệu về các Chữ cái Hy Lạp (The Greeks)
Trong một ngân hàng, Front Office (Bộ phận giao dịch) có trách nhiệm phòng vệ (hedge) các rủi ro cụ thể, trong khi Middle Office gom các rủi ro đó lại để quản lý tổng thể. Các chỉ số Greeks đo lường các khía cạnh rủi ro khác nhau của một danh mục phái sinh.

## 2. Delta ($\Delta$)
*   **Định nghĩa:** Là tốc độ thay đổi giá của phái sinh so với sự thay đổi giá của tài sản cơ sở.
*   **Công thức:** $\Delta = \frac{\partial P}{\partial S}$ (trong đó $P$ là giá phái sinh, $S$ là giá tài sản cơ sở).
*   **Delta Hedging:** Để triệt tiêu rủi ro biến động giá tài sản cơ sở, trader tạo ra một danh mục **Delta-neutral** ($\Delta = 0$).
*   **Đặc điểm:** Với các sản phẩm tuyến tính (như hợp đồng kỳ hạn), Delta là hằng số. Với quyền chọn, Delta thay đổi liên tục khi giá tài sản cơ sở thay đổi.

## 3. Gamma ($\Gamma$)
*   **Định nghĩa:** Là tốc độ thay đổi của Delta so với sự thay đổi giá của tài sản cơ sở. Đây là đạo hàm bậc hai của giá phái sinh theo giá tài sản cơ sở.
*   **Công thức:** $\Gamma = \frac{\partial^2 P}{\partial S^2}$
*   **Ý nghĩa:** Gamma đo lường **độ cong** của mối quan hệ giữa giá phái sinh và giá tài sản.
    *   Nếu Gamma nhỏ: Delta thay đổi chậm, việc điều chỉnh vị thế phòng vệ không cần quá thường xuyên.
    *   Nếu Gamma lớn: Delta thay đổi rất nhanh, danh mục Delta-neutral sẽ gặp rủi ro lớn nếu giá tài sản cơ sở biến động mạnh.

## 4. Vega ($V$)
*   **Định nghĩa:** Tốc độ thay đổi giá của danh mục so với sự thay đổi của **biến động (volatility - $\sigma$)** của tài sản cơ sở.
*   **Công thức:** $V = \frac{\partial P}{\partial \sigma}$
*   **Ý nghĩa:** Nếu Vega cao, giá trị danh mục cực kỳ nhạy cảm với việc thị trường trở nên bất ổn hơn hoặc ổn định hơn.

## 5. Theta ($\Theta$)
*   **Định nghĩa:** Tốc độ thay đổi giá của danh mục theo **thời gian** trôi qua (còn gọi là "hao mòn thời gian").
*   **Công thức:** $\Theta = \frac{\partial P}{\partial t}$
*   **Đặc điểm:** Đối với quyền chọn, Theta thường âm (giá trị quyền chọn giảm dần khi tiến gần ngày đáo hạn). Khác với các Greeks khác, Theta không phải là rủi ro ngẫu nhiên vì thời gian luôn trôi đi một cách chắc chắn.

## 6. Rho ($\rho$)
*   **Định nghĩa:** Tốc độ thay đổi giá của danh mục so với sự thay đổi của **lãi suất**.
*   **Công thức:** $\rho = \frac{\partial P}{\partial r}$

## 7. Khai triển Chuỗi Taylor (Taylor Series Expansion)
Trader sử dụng chuỗi Taylor để ước lượng tổng thay đổi giá trị danh mục ($\Delta P$):
$$\Delta P \approx \Delta \cdot \Delta S + \frac{1}{2} \Gamma \cdot (\Delta S)^2 + V \cdot \Delta \sigma + \Theta \cdot \Delta t$$
Công thức này cho thấy cách các Greeks kết hợp lại để phản ánh biến động tổng thể.

## 8. Thực tế của việc phòng vệ (The Realities of Hedging)
*   **Dynamic Hedging (Phòng vệ động):** Trader phải tái cân bằng danh mục định kỳ (hàng ngày hoặc khi giá biến động mạnh) để duy trì trạng thái Delta-neutral.
*   **Chi phí giao dịch:** Việc tái cân bằng quá thường xuyên sẽ tốn phí giao dịch, nhưng nếu quá thưa thớt sẽ bị lệch Delta.
*   **Static Options Replication:** Một kỹ thuật thay thế cho các quyền chọn kỳ lạ (exotic options), bằng cách thiết lập một danh mục các quyền chọn thông thường để mô phỏng giá trị của quyền chọn kỳ lạ tại các ranh giới nhất định.

---
**Ghi chú quan trọng:**
*   Phòng vệ Delta chỉ bảo vệ danh mục trước những thay đổi **nhỏ** của giá tài sản.
*   Để bảo vệ danh mục trước những thay đổi **lớn**, trader cần quản lý cả Gamma và Vega.
*   Các ngân hàng lớn có lợi thế quy mô (economies of scale) vì họ có thể bù trừ (offset) rủi ro từ hàng ngàn khách hàng khác nhau trước khi thực hiện giao dịch phòng vệ ra thị trường bên ngoài.
