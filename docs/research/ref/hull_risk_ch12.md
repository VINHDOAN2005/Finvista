# Chương 12: Giá trị chịu rủi ro và Mức thiếu hụt dự kiến (Value at Risk and Expected Shortfall)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Value at Risk (VaR)
VaR là thước đo rủi ro nhằm trả lời một câu hỏi đơn giản cho ban lãnh đạo: "Điều tồi tệ nhất có thể xảy ra ở một mức độ tin cậy nhất định là gì?".
*   **Định nghĩa:** "Chúng ta chắc chắn $X\%$ rằng tổn thất sẽ không vượt quá $V$ đô la trong khoảng thời gian $T$ ngày tới". Giá trị $V$ chính là VaR.
*   Ví dụ: VaR 1 ngày ở mức tin cậy 99% là 10 triệu USD. Nghĩa là có 99% xác suất lỗ trong ngày mai không vượt quá 10 triệu USD (hoặc có 1% xác suất lỗ từ 10 triệu USD trở lên).
*   **Nhược điểm của VaR:**
    *   VaR không cho biết **khi tổn thất vượt quá ngưỡng VaR thì nó sẽ tồi tệ đến mức nào**. Tổn thất ở phân vị 1% có thể là 11 triệu USD hoặc 500 triệu USD, VaR không phân biệt được.
    *   VaR có thể tạo ra hệ thống khuyến khích sai lệch cho trader: Trader có thể thiết kế một danh mục để thỏa mãn giới hạn VaR nhưng lại chịu rủi ro sụp đổ khổng lồ (blow-up risk) ở phần đuôi.

## 2. Expected Shortfall (ES)
Expected Shortfall (hay còn gọi là Conditional VaR, Expected Tail Loss) giải quyết nhược điểm của VaR.
*   **Định nghĩa:** "Nếu điều tồi tệ xảy ra (tổn thất vượt quá VaR), thì trung bình chúng ta sẽ mất bao nhiêu?". Nó là **giá trị trung bình của các khoản lỗ nằm ở phần đuôi** vượt quá VaR.
*   **Ví dụ:** Nếu VaR 1 ngày ở mức 99% là 10 triệu USD, thì ES là trung bình của 1% các khoản lỗ tồi tệ nhất đó (có thể là 15 triệu USD).
*   ES cung cấp cái nhìn toàn diện hơn về rủi ro đuôi (tail risk) và đang dần thay thế VaR trong các quy định của Basel (Ví dụ: FRTB chuyển từ dùng VaR 99% sang ES 97.5%).

## 3. Coherent Risk Measures (Thước đo rủi ro chặt chẽ)
Một thước đo rủi ro được coi là "Coherent" (chặt chẽ, hợp lý về mặt toán học) nếu nó thỏa mãn 4 điều kiện của Artzner et al. (1999):
1.  **Monotonicity (Tính đơn điệu):** Danh mục rủi ro hơn phải có thước đo lớn hơn.
2.  **Translation Invariance (Bất biến tịnh tiến):** Thêm $K$ tiền mặt vào danh mục sẽ làm giảm rủi ro đúng $K$.
3.  **Homogeneity (Tính thuần nhất):** Nhân quy mô danh mục lên $\lambda$ lần thì rủi ro tăng $\lambda$ lần.
4.  **Subadditivity (Tính dưới cộng):** Rủi ro của danh mục gộp không bao giờ được lớn hơn tổng rủi ro của từng danh mục lẻ ($Risk(A+B) \le Risk(A) + Risk(B)$). Tính chất này phản ánh lợi ích của việc đa dạng hóa.
*   **Kết luận quan trọng:** **ES là một Coherent Risk Measure, trong khi VaR thì KHÔNG.** VaR vi phạm tính Subadditivity trong một số trường hợp (khi rủi ro phân phối không chuẩn, đặc biệt là với rủi ro tín dụng).

## 4. Các Thông số của VaR và ES
*   **Thời gian ($T$):** Dựa trên tính thanh khoản. Nếu tài sản dễ bán, $T$ ngắn (1 ngày). Nếu tài sản khó bán, $T$ dài hơn (10 ngày, 1 năm).
*   **Chuyển đổi thời gian:** Nếu lợi nhuận theo ngày là độc lập và phân phối chuẩn, ta có thể quy đổi:
    $$VaR_{T-ngày} = VaR_{1-ngày} \cdot \sqrt{T}$$
*   **Tự tương quan (Autocorrelation):** Nếu thị trường có xu hướng duy trì (lợi nhuận ngày hôm nay có tương quan dương với ngày hôm qua), quy tắc $\sqrt{T}$ sẽ đánh giá thấp rủi ro thực tế.

## 5. Marginal, Incremental, và Component VaR
Khi phân bổ rủi ro cho các phòng ban/trader:
*   **Marginal VaR:** Tốc độ thay đổi của VaR khi ta thêm một đơn vị tài sản vào danh mục (đạo hàm riêng).
*   **Incremental VaR:** Lượng VaR thay đổi khi ta loại bỏ/thêm hẳn một vị thế lớn.
*   **Component VaR:** Phần VaR đóng góp bởi một vị thế cụ thể. Component VaR = Marginal VaR * Quy mô vị thế.

## 6. Định lý Euler (Euler's Theorem)
*   Do VaR và ES thường tuân theo tính thuần nhất (Homogeneity), Định lý Euler cho phép phân rã rủi ro rất đẹp: **Tổng các Component VaR của mọi vị thế sẽ bằng đúng Tổng VaR của cả danh mục.**
*   Điều này giúp ngân hàng phân bổ vốn kinh tế (Economic Capital) chính xác cho từng đơn vị kinh doanh (Risk Budgeting).

## 7. Back-Testing (Kiểm định quá khứ)
*   Là quá trình kiểm tra xem mô hình VaR có hoạt động tốt trong quá khứ hay không.
*   Nếu tính VaR 99% 1 ngày trong 1 năm (250 ngày giao dịch), ta kỳ vọng có khoảng $2.5$ ngày (1% của 250) số lỗ thực tế vượt quá VaR (gọi là **Exceptions**).
*   Nếu số lần vượt quá quá cao (vd: 10 lần), mô hình đang đánh giá thấp rủi ro và cơ quan quản lý sẽ phạt ngân hàng bằng cách tăng yêu cầu vốn (tăng hệ số nhân).
*   ES khó back-test hơn VaR rất nhiều, đây là lý do các cơ quan quản lý trước đây ngần ngại chuyển sang dùng ES.

---
**Ghi chú:** Khái niệm Component VaR và Định lý Euler là nền tảng để xây dựng hệ thống RAROC (Risk-Adjusted Return on Capital) mà các định chế tài chính dùng để đo lường hiệu quả hoạt động thực sự của từng bộ phận.
