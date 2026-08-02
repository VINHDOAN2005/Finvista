# Chương 22: Phân tích Kịch bản và Kiểm tra Sức chịu đựng (Scenario Analysis and Stress Testing)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Tại sao phải Stress Testing?
*   **Điểm yếu của VaR/ES:** Các mô hình này thường mang tính "nhìn lại quá khứ" (backward-looking). Nếu một sự kiện chưa từng xảy ra trong bộ dữ liệu lịch sử, mô hình sẽ coi xác suất xảy ra của nó bằng 0.
*   **Mục đích của Stress Testing:** Đánh giá tác động của các kịch bản **cực đoan nhưng có thể xảy ra (extreme but plausible)** mà các mô hình VaR/ES có thể bỏ sót. 
*   **Bài học từ khủng hoảng 2008:** Sự phụ thuộc quá mức vào VaR một cách máy móc (mechanistic application) là một sai lầm. Cần phải tập trung nhiều hơn vào Stress Testing.

## 2. Cách tạo ra Kịch bản (Generating the Scenarios)
Có nhiều cách để xây dựng kịch bản căng thẳng:
1.  **Gây sốc cho từng biến số độc lập (Stressing Individual Variables):** Ví dụ: Lãi suất tăng 100 bps, thị trường chứng khoán giảm 10%, biến động (volatility) tăng 50%.
2.  **Sử dụng các kịch bản lịch sử (Historical Scenarios):** Lấy dữ liệu từ những đợt khủng hoảng thực tế. Ví dụ: Ngày Thứ Hai Đen tối (Tháng 10/1987), Khủng hoảng tài chính Châu Á (1997), Vụ vỡ nợ của Nga (1998), Khủng hoảng dưới chuẩn (2007-2008). Khuyết điểm của phương pháp này là "lịch sử không bao giờ lặp lại chính xác 100%".
3.  **Kịch bản do Ban lãnh đạo tạo ra (Management-generated Scenarios):** Đây là cách tốt nhất. Một ủy ban gồm các nhà quản lý cấp cao và chuyên gia kinh tế sẽ họp để "động não" (brainstorm) trả lời câu hỏi: "Điều gì có thể đi sai hướng?". Sự tham gia của ban giám đốc (Board) là bắt buộc để đảm bảo kết quả của Stress Test thực sự được đưa vào quá trình ra quyết định chiến lược.
4.  **Kiểm tra sức chịu đựng ngược (Reverse Stress Testing):** Thay vì hỏi "Kịch bản X sẽ gây thiệt hại bao nhiêu?", ngân hàng sẽ dùng thuật toán để hỏi ngược lại: **"Kịch bản nào sẽ khiến ngân hàng phá sản?"**. Từ đó, ngân hàng tìm ra những rủi ro tiềm ẩn lớn nhất của mình.

## 3. Tính Toàn diện của Kịch bản (Making Scenarios Complete)
*   Một kịch bản tốt không chỉ đánh giá tác động tức thời (immediate effect) mà còn phải tính đến **hiệu ứng dây chuyền (knock-on effects)**.
*   *Ví dụ vụ LTCM (1998):* LTCM đã làm Stress Test cho sự kiện "chuyến bay đến chất lượng" (flight to quality), nhưng họ không ngờ rằng khi thị trường sụp đổ, hàng loạt quỹ đầu cơ khác cũng bị "margin call" và phải bán tháo tài sản giống hệt họ, khiến thanh khoản cạn kiệt hoàn toàn và đẩy giá đi xa hơn nhiều so với dự kiến.

## 4. Vai trò của Quy định (Regulation)
Sau năm 2008, các cơ quan quản lý không còn tin tưởng vào việc ngân hàng tự làm Stress Test (vì ngân hàng luôn có xu hướng làm nhẹ các kịch bản để giảm yêu cầu vốn). Cơ quan quản lý hiện nay tự thiết kế các kịch bản và bắt ngân hàng phải chạy bài kiểm tra.
*   **Tại Mỹ:** 
    *   **CCAR (Comprehensive Capital Analysis and Review):** Áp dụng cho các ngân hàng lớn (trên 50 tỷ USD tài sản). Cục Dự trữ Liên bang (Fed) đưa ra các kịch bản suy thoái nặng nề (bao gồm thất nghiệp tăng, giá nhà giảm). Ngân hàng phải chứng minh có đủ vốn để vượt qua, nếu không sẽ bị **cấm trả cổ tức/mua lại cổ phiếu**.
    *   **DFAST (Dodd-Frank Act Stress Test):** Tương tự CCAR nhưng áp dụng rộng hơn và không yêu cầu đệ trình kế hoạch phân bổ vốn.
*   **Tại Châu Âu / Anh:** Ngân hàng Trung ương Châu Âu (ECB) và Ngân hàng Trung ương Anh (BoE) cũng thực hiện các đợt Stress Test định kỳ cực kỳ nghiêm ngặt.

## 5. Làm gì với kết quả Stress Test?
*   Vấn đề lớn nhất là nhiều ngân hàng chạy Stress Test chỉ để "nộp cho có" và bị ban lãnh đạo phớt lờ ("Chuyện đó xác suất quá thấp, không đáng lo").
*   **Hành động đúng:** Ban lãnh đạo phải xem xét: "Rủi ro từ kịch bản này có nằm trong khẩu vị rủi ro (Risk Appetite) của chúng ta không? Nếu không, phải cắt giảm vị thế hoặc mua bảo hiểm (hedging) ở đâu?".

## 6. Tích hợp Stress Testing và VaR
Để Stress Testing được coi trọng hơn, một số nhà nghiên cứu (như Berkowitz, 2000) đề xuất gán một **xác suất chủ quan (subjective probability)** cho các kịch bản cực đoan và trộn chúng vào chung với bộ dữ liệu lịch sử để tính VaR tổng hợp. Tuy nhiên, việc gán xác suất chủ quan thường gặp khó khăn do các **thành kiến nhận thức (cognitive biases)** của con người.

---
**Ghi chú quan trọng:** Stress Testing không phải là một công cụ toán học thuần túy, mà là một quy trình quản trị rủi ro mang tính chiến lược, đòi hỏi tư duy đa chiều và sự tham gia trực tiếp của ban lãnh đạo cấp cao.
