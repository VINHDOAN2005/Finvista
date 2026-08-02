# Chương 5: Giao dịch trên Thị trường Tài chính (Trading in Financial Markets)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Các loại Thị trường (The Markets)
Có hai loại thị trường giao dịch chính:
*   **Exchange-Traded (Thị trường niêm yết):** Giao dịch tập trung trên sàn (như NYSE, CBOE). Các hợp đồng được chuẩn hóa, có tính thanh khoản cao và rủi ro tín dụng thấp nhờ Trung tâm bù trừ.
*   **Over-the-Counter (OTC - Thị trường phi tập trung):** Mạng lưới các trader làm việc cho các định chế tài chính, tập đoàn. Hợp đồng có thể tùy chỉnh linh hoạt, nhưng rủi ro đối tác cao hơn (trước khủng hoảng 2008). Sau 2008, thị trường OTC đang dần chuyển sang mô hình thanh toán tập trung.

## 2. Trung tâm bù trừ (Clearing Houses)
*   **Vai trò:** Đứng giữa người mua và người bán. Người bán bán cho sàn, người mua mua từ sàn.
*   **Ký quỹ (Margin):** Là tài sản thế chấp (thường là tiền mặt) để đảm bảo các bên thực hiện nghĩa vụ hợp đồng. Nếu một bên thua lỗ vượt quá mức ký quỹ, sàn sẽ đóng vị thế để bảo vệ hệ thống.
*   **CCPs (Central Counterparties):** Các trung tâm bù trừ tập trung giúp giảm thiểu rủi ro hệ thống bằng cách bù trừ đa phương các giao dịch.

## 3. Vị thế Mua và Bán (Long and Short Positions)
*   **Long Position (Vị thế mua):** Mua tài sản với kỳ vọng giá tăng.
*   **Short Sale (Bán khống):** Mượn tài sản từ người khác để bán ngay lập tức với kỳ vọng giá sẽ giảm, sau đó mua lại để trả. Người bán khống phải trả lại mọi khoản cổ tức/lãi suất phát sinh cho người cho mượn.

## 4. Các sản phẩm Phái sinh Cơ bản (Plain Vanilla Derivatives)
1.  **Forward Contracts (Hợp đồng kỳ hạn):** Thỏa thuận mua/bán tài sản tại một thời điểm trong tương lai với mức giá cố định. Giao dịch OTC.
2.  **Futures Contracts (Hợp đồng tương lai):** Tương tự hợp đồng kỳ hạn nhưng được chuẩn hóa và giao dịch trên sàn. Có cơ chế quyết toán hàng ngày (Daily settlement).
3.  **Swaps (Hợp đồng hoán đổi):** Thỏa thuận trao đổi dòng tiền trong tương lai (Ví dụ: Hoán đổi lãi suất cố định lấy lãi suất thả nổi LIBOR).
4.  **Options (Hợp đồng quyền chọn):**
    *   **Call Option:** Quyền mua (không bắt buộc).
    *   **Put Option:** Quyền bán (không bắt buộc).
    *   **American vs. European:** Quyền chọn Mỹ có thể thực hiện bất kỳ lúc nào trước khi hết hạn; Quyền chọn Châu Âu chỉ được thực hiện vào đúng ngày hết hạn.

## 5. Phái sinh Phi truyền thống (Non-Traditional Derivatives)
Các sản phẩm này giúp doanh nghiệp quản lý các rủi ro phi tài chính:
*   **Weather Derivatives (Phái sinh thời tiết):** Dựa trên các chỉ số như HDD (Heating Degree Days) hoặc CDD (Cooling Degree Days).
*   **Energy Derivatives (Phái sinh năng lượng):** Liên quan đến dầu thô, khí tự nhiên và điện. (Điện là loại hàng hóa khó quản lý nhất vì không thể lưu trữ dễ dàng).

## 6. Quyền chọn Kỳ lạ và Sản phẩm Cấu trúc (Exotic Options & Structured Products)
Các công cụ này thường được các ngân hàng thiết kế riêng cho khách hàng:
*   **Asian Options:** Giá trị dựa trên **giá trung bình** của tài sản trong một giai đoạn.
*   **Barrier Options:** Quyền chọn chỉ xuất hiện (Knock-in) hoặc biến mất (Knock-out) khi giá tài sản chạm một ngưỡng nhất định.
*   **Binary Options:** Chỉ có hai kết quả: nhận một khoản tiền cố định hoặc không nhận được gì.

## 7. Thách thức trong Quản trị Rủi ro (Risk Management Challenges)
*   Sản phẩm phái sinh rất linh hoạt, có thể dùng để phòng vệ (hedge), đầu cơ (speculate) hoặc kinh doanh chênh lệch (arbitrage).
*   **Nguy cơ:** Trader có thể lạm dụng tính linh hoạt này để che giấu các khoản lỗ đầu cơ dưới danh nghĩa phòng vệ. (Ví dụ vụ **Jerome Kerviel** tại SocGen đã tạo ra các giao dịch giả để che giấu vị thế khổng lồ của mình).

---
**Ghi chú quan trọng:** Sự hội tụ giữa thị trường OTC và thị trường niêm yết là xu hướng tất yếu sau khủng hoảng 2008 để tăng cường tính minh bạch và an toàn hệ thống.
