# Chương 7: Định giá và Phân tích Kịch bản (Valuation and Scenario Analysis)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Sự khác biệt giữa Định giá và Phân tích Kịch bản
*   **Valuation (Định giá):** Tập trung vào việc tính toán giá trị hiện tại của dòng tiền **trung bình** trong tương lai. Sử dụng thế giới **Risk-Neutral (Rủi ro trung tính)**.
*   **Scenario Analysis (Phân tích kịch bản):** Tập trung vào việc trả lời câu hỏi "Điều tồi tệ nhất có thể xảy ra là gì?" (How bad can things get?). Tập trung vào các kết quả **cực đoan**. Sử dụng thế giới **Real-World (Thế giới thực)**.

## 2. Biến động và Giá tài sản (Volatility & Asset Prices)
*   **Phân phối Lognormal:** Giả định rằng lợi nhuận của tài sản tuân theo phân phối chuẩn, dẫn đến giá tài sản tuân theo phân phối lognormal (giá không bao giờ âm).
*   **Xác suất giá thấp hơn một ngưỡng V:** Được tính toán dựa trên các tham số tăng trưởng ($\mu$) và biến động ($\sigma$).

## 3. Định giá Rủi ro Trung tính (Risk-Neutral Valuation)
Đây là công cụ quan trọng nhất trong định giá phái sinh:
*   **Định nghĩa:** Một thế giới giả tưởng nơi nhà đầu tư không yêu cầu thêm lợi nhuận cho việc chấp nhận rủi ro. Mọi tài sản đều có lợi nhuận kỳ vọng bằng **lãi suất phi rủi ro ($R_F$)**.
*   **Nguyên lý:** Chúng ta có thể định giá bất kỳ sản phẩm phái sinh nào bằng cách giả định thế giới là rủi ro trung tính. Kết quả nhận được sẽ đúng trong cả thế giới thực.
*   **Các bước thực hiện:**
    1.  Giả định lợi nhuận tài sản cơ sở là $R_F$.
    2.  Tính toán giá trị chi trả (payoff) kỳ vọng của phái sinh.
    3.  Chiết khấu giá trị kỳ vọng đó về hiện tại bằng lãi suất $R_F$.

## 4. Phân tích Kịch bản (Scenario Analysis)
*   Trong phân tích rủi ro, chúng ta quan tâm đến thực tế (Thế giới thực).
*   Lợi nhuận kỳ vọng trong thế giới thực ($\mu$) thường cao hơn lãi suất phi rủi ro vì nhà đầu tư yêu cầu phần bù rủi ro (risk premium).
*   Ví dụ: Để tính **VaR (Value at Risk)**, chúng ta phải dùng tỷ suất sinh lời thực tế để xem khả năng giá rơi xuống các mức thấp là bao nhiêu.

## 5. Định lý Girsanov (Girsanov's Theorem)
*   Định lý này giải thích cách chuyển đổi giữa thế giới thực và thế giới rủi ro trung tính.
*   **Điểm mấu chốt:** Khi chuyển đổi giữa hai thế giới, **tốc độ tăng trưởng kỳ vọng thay đổi**, nhưng **biến động (volatility) vẫn giữ nguyên**.

## 6. Khi nào cần sử dụng cả hai thế giới?
Trong các bài toán quản trị rủi ro phức tạp (như tính giá trị danh mục phái sinh sau 6 tháng):
1.  **Bước 1:** Dùng thế giới thực để mô phỏng giá tài sản cơ sở sau 6 tháng (tạo ra các kịch bản thực tế).
2.  **Bước 2:** Tại mỗi kịch bản đó, dùng thế giới rủi ro trung tính để định giá lại (revalue) các hợp đồng phái sinh còn lại trong danh mục.

## 7. Ước lượng các quy trình trong thế giới thực
*   Việc xác định lợi nhuận kỳ vọng trong thế giới thực rất khó vì cần lượng dữ liệu khổng lồ.
*   Cách tiếp cận phổ biến: Sử dụng mô hình CAPM để ước tính lợi nhuận thực tế dựa trên Beta của tài sản và phần bù rủi ro thị trường.

---
**Ghi chú quan trọng:**
*   **Định giá** dùng lãi suất phi rủi ro để chiết khấu dòng tiền kỳ vọng.
*   **Quản trị rủi ro (VaR, Stress Testing)** dùng lợi nhuận thực tế để đánh giá các khả năng xấu có thể xảy ra.
*   Nhà quản trị rủi ro cần phân biệt rõ khi nào đang ở trong "thế giới" nào để tránh sai lầm trong tính toán.
