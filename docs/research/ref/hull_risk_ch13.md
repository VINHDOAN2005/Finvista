# Chương 13: Mô phỏng Lịch sử và Lý thuyết Giá trị Cực đoan (Historical Simulation and Extreme Value Theory)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Phương pháp Mô phỏng Lịch sử (Historical Simulation)
Đây là cách phổ biến nhất mà các định chế tài chính dùng để tính VaR và ES cho rủi ro thị trường.
*   **Nguyên lý:** Giả định rằng những gì đã xảy ra trong quá khứ gần đây (ví dụ: 500 ngày qua) là một chỉ dẫn tốt cho những gì có thể xảy ra vào ngày mai.
*   **Các bước thực hiện:**
    1.  Xác định các biến số rủi ro (risk factors) ảnh hưởng đến danh mục.
    2.  Thu thập dữ liệu biến động phần trăm hàng ngày của các biến này trong quá khứ (ví dụ 501 ngày để có 500 kịch bản).
    3.  Tạo ra 500 kịch bản cho ngày mai bằng cách áp dụng các biến động phần trăm trong quá khứ lên giá trị hiện tại của các biến.
    4.  Tính toán lại giá trị của danh mục ở hiện tại và cho 500 kịch bản đó. Tính ra khoản lỗ/lãi cho từng kịch bản.
    5.  Sắp xếp 500 khoản lỗ từ cao đến thấp. VaR 99% (1 ngày) chính là khoản lỗ ở phân vị thứ 99 (khoản lỗ tồi tệ thứ 5 trong 500 ngày). ES là trung bình của các khoản lỗ tồi tệ hơn VaR (4 khoản lỗ đầu tiên).

## 2. Các biến thể và Cải tiến (Extensions)
Mô phỏng lịch sử cơ bản coi mọi ngày trong quá khứ đều có trọng số như nhau. Điều này có nhược điểm vì thị trường liên tục thay đổi (nonstationary). Để khắc phục:
*   **Weighting of Observations (Đánh trọng số):** Áp dụng cấp số nhân giống mô hình EWMA. Dữ liệu càng gần hiện tại thì trọng số càng cao. Điều này giúp VaR phản ứng nhanh hơn với các điều kiện thị trường hiện tại.
*   **Volatility Scaling (Điều chỉnh theo Biến động - Phương pháp Hull-White):**
    *   Cập nhật biến động hàng ngày bằng mô hình EWMA hoặc GARCH(1,1).
    *   Khi tính toán kịch bản dựa trên ngày quá khứ $i$, ta nhân biến động phần trăm của ngày đó với tỷ số: $\frac{\sigma_{hiện\_tại}}{\sigma_{ngày\_i}}$
    *   Phương pháp này rất hiệu quả. Nó không chỉ cập nhật thông tin mới nhất vào mô hình mà còn cho phép tạo ra các kịch bản lỗ còn lớn hơn cả những gì đã từng xảy ra trong lịch sử (nếu biến động hiện tại đang rất cao).

## 3. Lý thuyết Giá trị Cực đoan (Extreme Value Theory - EVT)
Mô phỏng lịch sử có một điểm yếu chết người: Khi tính VaR ở mức tin cậy rất cao (như 99.9% hay 99.97%), ta không có đủ dữ liệu ở phần đuôi để đưa ra kết quả chính xác (dữ liệu thưa thớt). EVT ra đời để giải quyết bài toán này.
*   **Nguyên lý:** EVT là một nhánh của toán học thống kê chuyên nghiên cứu về **phần đuôi (tails)** của các phân phối. Nó giúp làm mượt và ngoại suy (extrapolate) phần đuôi từ dữ liệu thực tế.
*   **Định lý Gnedenko:** Bất kể phân phối gốc là gì, phần đuôi (vượt qua một ngưỡng $u$ đủ lớn) sẽ hội tụ về một **Phân phối Pareto Tống quát (Generalized Pareto Distribution - GPD)**.
*   **Tham số của GPD:**
    *   $\xi$ (Shape parameter): Quyết định độ "béo" của đuôi. Đuôi càng béo, $\xi$ càng lớn.
    *   $\beta$ (Scale parameter): Thang đo.
*   **Ước lượng:** Các tham số này được ước lượng bằng phương pháp **Maximum Likelihood**.
*   **Ứng dụng:** Nhờ EVT, từ 500 ngày dữ liệu, ta vẫn có thể dùng công thức toán học để tính ra VaR ở mức 99.9% một cách đáng tin cậy.

## 4. Stressed VaR và Stressed ES
*   Như đã giới thiệu, VaR thông thường mang tính "nhìn lại" (backward looking). Trong thời kỳ thị trường bình yên kéo dài (2003-2006), VaR tính ra sẽ rất thấp.
*   Basel II.5 và FRTB yêu cầu ngân hàng phải tính toán thêm các chỉ số **Stressed**.
*   Thay vì dùng 250 hay 500 ngày gần nhất, ngân hàng phải lội ngược dòng lịch sử, tìm ra một chu kỳ 250 ngày "tồi tệ nhất" (ví dụ: giai đoạn khủng hoảng 2008) đối với danh mục hiện tại của mình, và dùng bộ dữ liệu đó để chạy Historical Simulation.

## 5. Vấn đề Tính toán (Computational Issues)
*   Chạy mô phỏng lịch sử cho một ngân hàng lớn có hàng ngàn sản phẩm phái sinh đòi hỏi năng lực tính toán cực lớn (phải định giá lại toàn bộ danh mục 500 lần).
*   Đặc biệt, nếu trong danh mục có các quyền chọn kỳ lạ phải định giá bằng Monte Carlo, ta sẽ đối mặt với bài toán "Mô phỏng lồng trong mô phỏng".
*   **Giải pháp:** Sử dụng **Delta-Gamma Approximation** (Phương pháp xấp xỉ dùng chuỗi Taylor ở Chương 8). Thay vì định giá lại hoàn toàn bằng mô hình phức tạp, ta dùng Delta và Gamma để ước tính nhanh khoản lỗ/lãi.

---
**Ghi chú:** Phương pháp Mô phỏng lịch sử cực kỳ dễ hiểu đối với ban giám đốc (vì nó dựa vào "những gì thực sự đã xảy ra") và nắm bắt hoàn hảo các tương quan thực tế (bao gồm cả tương quan trong lúc hoảng loạn) mà không cần phải giả định phân phối chuẩn phức tạp. Việc kết hợp nó với Volatility Scaling và EVT biến nó thành một công cụ cực mạnh.
