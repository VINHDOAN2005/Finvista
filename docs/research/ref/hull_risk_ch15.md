# Chương 15: Basel I, Basel II, và Solvency II
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Tại sao phải quản lý Ngân hàng?
*   **Systemic Risk (Rủi ro hệ thống):** Sự sụp đổ của một ngân hàng lớn có thể kéo theo sự sụp đổ của các ngân hàng khác do sự liên kết chặt chẽ trên thị trường OTC, dẫn đến tê liệt toàn bộ nền kinh tế (Ví dụ: Lehman Brothers).
*   **Bảo vệ tiền gửi:** Để đảm bảo người dân có niềm tin vào hệ thống ngân hàng.

## 2. Basel I (1988)
*   **Mục tiêu:** Tạo ra một sân chơi bình đẳng (level playing field) về yêu cầu vốn cho các ngân hàng quốc tế, tránh tình trạng ngân hàng ở các nước luật lỏng lẻo có lợi thế cạnh tranh.
*   **Tỷ lệ Cooke (The Cooke Ratio):** Yêu cầu ngân hàng giữ vốn tối thiểu bằng **8%** của **Tài sản có rủi ro trọng số (Risk-Weighted Assets - RWA)**.
*   **Phân bổ trọng số (Risk Weights):**
    *   0% cho trái phiếu chính phủ OECD.
    *   20% cho ngân hàng OECD.
    *   50% cho vay thế chấp nhà ở.
    *   100% cho vay doanh nghiệp.
*   **Xử lý phái sinh OTC:** Tính **Credit Equivalent Amount (CEA)** bằng Current Exposure (Giá trị thị trường hiện tại nếu dương) + Add-on Factor (Dự phòng rủi ro tương lai).

## 3. Netting và Bản sửa đổi 1996 (The 1996 Amendment)
*   **Netting (Bù trừ):** Cho phép ngân hàng gộp các giao dịch lãi và lỗ với cùng một đối tác (có ký ISDA Master Agreement) để giảm CEA, từ đó giảm yêu cầu vốn.
*   **Bản sửa đổi 1996:** Yêu cầu vốn cho **Market Risk (Rủi ro thị trường)**.
    *   Các ngân hàng có thể dùng mô hình nội bộ (Internal Models Approach) để tính VaR (10 ngày, 99%).
    *   Vốn yêu cầu = $max(VaR_{hôm\_qua}, m_c \cdot VaR_{trung\_bình\_60\_ngày})$ + Rủi ro cụ thể (Specific Risk). Trong đó hệ số nhân $m_c \ge 3$ và có thể bị phạt tăng lên nếu **Back-testing** thất bại.

## 4. Basel II (Bắt đầu áp dụng từ ~2007)
Khắc phục điểm yếu của Basel I (đánh giá mọi doanh nghiệp rủi ro 100% như nhau). Basel II dựa trên **3 Trụ cột (Pillars)**:

### Pillar 1: Minimum Capital Requirements (Yêu cầu Vốn Tối thiểu)
Tính vốn cho 3 loại rủi ro:
1.  **Credit Risk (Rủi ro tín dụng):**
    *   **Standardized Approach (Tiêu chuẩn):** Dùng xếp hạng tín nhiệm của các cơ quan bên ngoài (như S&P, Moody's) để gán trọng số rủi ro (từ 20% đến 150%).
    *   **Foundation IRB (Nội bộ cơ bản):** Ngân hàng tự ước lượng PD (Xác suất vỡ nợ), Basel cung cấp LGD (Tỷ trọng tổn thất) và EAD (Dư nợ khi vỡ nợ).
    *   **Advanced IRB (Nội bộ nâng cao):** Ngân hàng tự ước lượng cả PD, LGD, EAD và Đáo hạn (M). *Dựa trên mô hình Vasicek (Gaussian Copula) ở Chương 11.*
2.  **Market Risk:** Giữ nguyên như bản sửa đổi 1996.
3.  **Operational Risk (Rủi ro hoạt động):** Lần đầu tiên bị yêu cầu tính vốn.
    *   **Basic Indicator:** 15% tổng thu nhập gộp.
    *   **Standardized:** Tính theo tỷ lệ khác nhau cho 8 mảng kinh doanh.
    *   **AMA (Advanced Measurement Approach):** Ngân hàng dùng mô hình nội bộ để tính VaR 99.9% 1 năm cho rủi ro hoạt động.

### Pillar 2: Supervisory Review (Đánh giá của Cơ quan giám sát)
Cơ quan quản lý có quyền can thiệp sớm, yêu cầu ngân hàng giữ vốn cao hơn mức tối thiểu (Pillar 1) nếu thấy hệ thống quản trị rủi ro nội bộ yếu kém, hoặc đối mặt với các rủi ro chưa được tính đến (như rủi ro tập trung - concentration risk).

### Pillar 3: Market Discipline (Kỷ luật Thị trường)
Yêu cầu các ngân hàng công bố minh bạch thông tin về rủi ro, phương pháp tính vốn, và chất lượng tài sản để cổ đông và thị trường tự giám sát.

## 5. Solvency II
*   Đây là khung pháp lý quản lý vốn áp dụng cho **các công ty bảo hiểm** tại Châu Âu (có hiệu lực từ 2016).
*   Có cấu trúc 3 Trụ cột (Pillars) rất giống với Basel II.
*   **MCR (Minimum Capital Requirement):** Vốn tối thiểu tuyệt đối. Dưới mức này sẽ bị thanh lý.
*   **SCR (Solvency Capital Requirement):** Vốn mục tiêu (tính theo VaR 99.5% 1 năm). Dưới mức này sẽ bị giám sát chặt chẽ. Đánh giá rủi ro đầu tư, rủi ro thẩm định bảo hiểm (underwriting) và rủi ro hoạt động.

---
**Ghi chú:** Basel II là một bước tiến lớn trong quản trị rủi ro nhưng lại "kém may mắn" khi thời điểm triển khai gần trùng với cuộc khủng hoảng 2008. Việc cho phép các ngân hàng tự dùng mô hình nội bộ (IRB, AMA) dẫn đến tình trạng "trọng tài quy định" (Regulatory Arbitrage), khi ngân hàng tìm cách tối ưu hóa các con số để giảm vốn thay vì giảm rủi ro thực sự.
