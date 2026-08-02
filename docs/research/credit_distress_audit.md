# 🎯 FINVISTA: CHIẾN LƯỢC ĐỊNH GIÁ RỦI RO TÍN DỤNG & KIỆT QUÊ TÀI CHÍNH (AUDIT)
> **Tác giả:** Finvista Quant Team  
> **Khung lý thuyết:** Bodie (Investments), Cochrane (Asset Pricing), Elton & Gruber (MPT).
> **Ngày cập nhật:** 08/06/2026

---

## 🏗️ 1. Kiến trúc Layer (Architectural Layers)
Hệ thống được tổ chức thành 4 lớp cốt lõi, đảm bảo tính module hóa và khả năng mở rộng:

1.  **Ingestion Layer (Dữ liệu thô):** Thu thập BCTC, giá chứng khoán, và chỉ số vĩ mô toàn cầu.
2.  **Feature Engineering Layer (Chế biến chỉ số):** Tính toán ROAA, ROAE, Altman Z-Score, và các biến tương đối so với ngành (Industry-Adjusted).
3.  **Intelligence Layer (Máy học):** Huấn luyện mô hình XGBoost, LightGBM và Stacking Ensemble để học các mẫu rủi ro trong quá khứ.
4.  **Application Layer (Thực thi & Cảnh báo):** Xuất báo cáo "Traffic Light" (Xanh/Vàng/Đỏ) và gửi cảnh báo tự động qua Telegram.

---

## 🚀 2. Quy trình 8 Bước Tiêu chuẩn (The 8-Step Pipeline)
Dành cho người mới bắt đầu, đây là hành trình của dữ liệu từ con số thô đến quyết định đầu tư:

| Bước | Tên gọi | Nhiệm vụ chính |
| :--- | :--- | :--- |
| **Step 1** | **Filter** | Lọc danh sách doanh nghiệp niêm yết (loại bỏ ngân hàng/bảo hiểm do đặc thù BCTC riêng). |
| **Step 2** | **Crawl** | Thu thập dữ liệu lịch sử 5-10 năm để máy có đủ "trải nghiệm" về các kỳ khủng hoảng. |
| **Step 3** | **Compute** | Tính toán **ROAA, ROAE, Debt Ratio** và so sánh với trung bình ngành (Industry Alpha). |
| **Step 4** | **Label** | Gán nhãn "Kiệt quệ" dựa trên luật kinh tế (Âm vốn chủ, lỗ lũy kế, dòng tiền âm). |
| **Step 5** | **Export** | Làm sạch lần cuối, xử lý dữ liệu nhiễu (Outliers) và chuẩn bị tập huấn luyện. |
| **Step 6** | **Train** | Huấn luyện tịnh tiến: So sánh các model đơn lẻ -> Kích hoạt **Stacking Ensemble**. |
| **Step 7** | **Evaluate** | Quét toàn bộ thị trường hiện tại. Áp dụng **Macro Overlay** (Lạm phát, Lãi suất). |
| **Step 8** | **Contagion** | Đánh giá rủi ro lây lan (Network Effect) giữa các doanh nghiệp trong hệ sinh thái. |

---

## 📊 3. Kết quả Hiệu năng (Performance Benchmarks)
Sau khi nâng cấp, mô hình đạt được các chỉ số thực chiến ấn tượng:
*   **Accuracy (Độ chính xác tổng):** **~80%**
*   **Recall (Khả năng phát hiện lỗi):** **84% - 92%** (Mô hình cực kỳ nhạy trong việc "đánh hơi" rủi ro trước khi nó xảy ra).
*   **F1-Score:** **74%** (Đạt trạng thái cân bằng tốt nhất giữa báo động đúng và báo động nhầm).

---

## 💡 4. Nghiên cứu So sánh & Đề xuất Tối ưu (Advanced Research)

### **Thị trường đang làm gì?**
*   **Moody’s (RiskCalc):** Làm giống chúng ta (Accounting-based ML).
*   **Bloomberg (DRS):** Dùng giá cổ phiếu để tính xác suất vỡ nợ (Market-based).

### **Đề xuất "Finvista 2.0" (The Golden Architecture):**
Để tối ưu hơn nữa, chúng ta sẽ hướng tới kiến trúc **Engine Kép (Dual-Engine)**:

1.  **Fundamental Engine (Layer hiện tại):** Rất tốt cho rủi ro dài hạn.
2.  **Structural Market Layer (Merton Model):** *Cần thêm.* Sử dụng biến động giá cổ phiếu để dự báo rủi ro tức thời (Real-time).
3.  **Alternative NLP Layer:** *Cần thêm.* Dùng AI đọc tin tức để phát hiện các dấu hiệu "chậm trả nợ" trước khi nó lên BCTC.
4.  **Temporal Decay:** Ưu tiên dữ liệu mới nhất để nhạy bén với các cú sốc thị trường (như sự kiện tỷ giá, lãi suất đột ngột).

---

## 📌 5. Ghi chú về các trường hợp đặc biệt (như VIC, VHM)
Mô hình Finvista không "phạt oan" các mã nợ cao nhưng quy mô lớn nhờ:
*   **Variable: Company Size:** DN càng lớn, ngưỡng chịu đựng nợ càng cao.
*   **Variable: Altman X4:** Nếu thị trường vẫn định giá Vốn hóa cao -> DN vẫn có khả năng huy động vốn tốt.
*   **Variable: ICR (Interest Coverage):** Chỉ cần dòng tiền trả được lãi vay, nợ cao không phải là vấn đề chí mạng.
