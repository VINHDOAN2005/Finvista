# CHƯƠNG 5: PHÂN TÍCH VÀ THẨM ĐỊNH TÀI CHÍNH DỰ ÁN

## 5.1. Ước tính Tổng mức đầu tư ban đầu (CAPEX)
Dự án Finvista được phát triển theo mô hình SaaS (Software-as-a-Service) tinh gọn, giảm thiểu tối đa việc mua sắm tài sản cố định vật lý. Tổng vốn đầu tư ban đầu tập trung vào phát triển hệ thống cốt lõi và quỹ dự phòng vận hành giai đoạn đầu.

**Bảng 5.1: Chi tiết vốn đầu tư ban đầu (Đơn vị: VNĐ)**

| STT | Hạng mục đầu tư | Chi phí dự kiến | Diễn giải chi tiết |
| :--- | :--- | :--- | :--- |
| **I** | **Tài sản cố định vô hình & Máy móc thiết bị** | **180.000.000** | |
| 1 | Trang thiết bị văn phòng lõi (Laptops, Router mạng chuyên dụng) | 80.000.000 | Trang bị cho nhóm 5 nhân sự ban đầu. |
| 2 | Chi phí đăng ký bản quyền, SHTT & Thuật toán | 30.000.000 | Đăng ký bản quyền phần mềm và bảo hộ nhãn hiệu. |
| 3 | Chi phí thành lập doanh nghiệp & Giấy phép phụ | 20.000.000 | Giấy phép trang thông tin điện tử/Dịch vụ tài chính. |
| 4 | Chi phí thiết lập server và bản quyền phần mềm gốc | 50.000.000 | Bản quyền Windows Server, Database license ban đầu. |
| **II** | **Chi phí khởi tạo thị trường (Marketing & Launching)** | **120.000.000** | Chiến dịch chạy thử nghiệm, kết nối KOLs. |
| **III** | **Vốn lưu động dự phòng tối thiểu (6 tháng đầu)** | **1.500.000.000** | Đảm bảo quỹ lương và vận hành khi chưa có doanh thu. |
| | **TỔNG MỨC ĐẦU TƯ BAN ĐẦU (CAPEX)** | **1.800.000.000** | **Một tỷ tám trăm triệu đồng.** |

---

## 5.2. Ước tính Chi phí vận hành hàng năm (OPEX)
Chi phí vận hành hàng năm được cấu thành chính từ quỹ lương (đã cộng BHXH 21.5% theo Chương 4), chi phí thuê văn phòng hạng A tại Deutsches Haus Tower, chi phí hạ tầng Cloud (AWS/GCP), và chi phí mua feed dữ liệu giao dịch real-time chuyên sâu.

**Bảng 5.2: Dự báo Chi phí vận hành hàng năm (Năm 1 - Năm 3) (Đơn vị: VNĐ)**

| STT | Khoản mục chi phí | Chi phí Tháng | Chi phí Năm 1 | Chi phí Năm 2 (Tăng 10%) | Chi phí Năm 3 (Tăng 10%) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Quỹ lương nhân sự lõi (gồm 21.5% BHXH) | 219.915.000 | 2.638.980.000 | 2.902.878.000 | 3.193.165.800 |
| 2 | Thuê văn phòng (UPGen Deutsches Haus) | 35.000.000 | 420.000.000 | 462.000.000 | 508.200.000 |
| 3 | Phí mua Data Feed giao dịch (Vietcap/Fiin) | 15.000.000 | 180.000.000 | 198.000.000 | 217.800.000 |
| 4 | Hạ tầng máy chủ Cloud (AWS/GCP) & Bảo mật | 8.000.000 | 96.000.000 | 105.600.000 | 116.160.000 |
| 5 | Chi phí Tiếp thị số & Chăm sóc khách hàng | 25.000.000 | 300.000.000 | 330.000.000 | 363.000.000 |
| 6 | Chi phí hành chính và dự phòng phát sinh | 5.000.000 | 60.000.000 | 66.000.000 | 72.600.000 |
| | **TỔNG CHI PHÍ VẬN HÀNH (OPEX)** | **307.915.000** | **3.694.980.000** | **4.064.478.000** | **4.470.925.800** |

---

## 5.3. Chiến lược Giá và Dự báo Doanh thu
Finvista triển khai chiến lược định giá linh hoạt theo phân khúc người dùng nhằm tối ưu hóa doanh thu:
* **Gói Finvista Basic (Nhà đầu tư cá nhân nhỏ lẻ):** 199.000 VNĐ/tháng. Cung cấp Greeks cơ bản và bảng tính toán IV.
* **Gói Finvista Pro (Traders chuyên nghiệp & Môi giới):** 399.000 VNĐ/tháng. Tích hợp ma trận kịch bản 2D, cảnh báo tự động qua Telegram/Zalo, bộ lọc nâng cao.
* **Gói Doanh nghiệp (B2B - Định chế tài chính):** Cung cấp API tích hợp trực tiếp hoặc giải pháp Nhãn trắng (White-label). Giá trung bình: 10.000.000 VNĐ/tháng.

**Bảng 5.3: Dự báo tăng trưởng Khách hàng và Doanh thu (Năm 1 - Năm 3)**

| Chỉ tiêu tài chính | Năm 1 | Năm 2 | Năm 3 |
| :--- | :--- | :--- | :--- |
| Số lượng thuê bao trả phí Basic bình quân/tháng | 1.200 | 2.500 | 4.000 |
| Số lượng thuê bao trả phí Pro bình quân/tháng | 500 | 1.200 | 2.200 |
| Số lượng đối tác doanh nghiệp B2B (API) | 2 | 4 | 7 |
| **Tổng Doanh thu gói Basic (VNĐ/năm)** | 2.865.600.000 | 5.970.000.000 | 9.552.000.000 |
| **Tổng Doanh thu gói Pro (VNĐ/năm)** | 2.394.000.000 | 5.745.600.000 | 10.533.600.000 |
| **Tổng Doanh thu B2B (VNĐ/năm)** | 240.000.000 | 480.000.000 | 840.000.000 |
| **TỔNG DOANH THU DỰ BÁO (VNĐ/năm)** | **5.499.600.000** | **12.195.600.000** | **20.925.600.000** |

---

## 5.4. Đánh giá Hiệu quả Tài chính dự án
Giả định thuế suất Thuế thu nhập doanh nghiệp (CIT) là **20%**. Tỷ suất chiết khấu (WACC) được xác định ở mức **12%** (phù hợp với mức bù rủi ro cho một dự án khởi nghiệp công nghệ tài chính tại Việt Nam).

**Bảng 5.4: Dự toán Dòng tiền và các chỉ số tài chính (Năm 0 - Năm 3) (Đơn vị: VNĐ)**

| Chỉ tiêu dòng tiền | Năm 0 | Năm 1 | Năm 2 | Năm 3 |
| :--- | :--- | :--- | :--- | :--- |
| **Doanh thu** | | 5.499.600.000 | 12.195.600.000 | 20.925.600.000 |
| **Chi phí vận hành (OPEX)** | | (3.694.980.000) | (4.064.478.000) | (4.470.925.800) |
| **Khấu hao tài sản** | | (45.000.000) | (45.000.000) | (45.000.000) |
| **Lợi nhuận trước thuế (EBT)** | | 1.759.620.000 | 8.086.122.000 | 16.409.674.200 |
| **Thuế TNDN (20% CIT)** | | (351.924.000) | (1.617.224.400) | (3.281.934.840) |
| **Lợi nhuận sau thuế (EAT)** | | 1.407.696.000 | 6.468.897.600 | 13.127.739.360 |
| Cộng ngược Khấu hao | | 45.000.000 | 45.000.000 | 45.000.000 |
| **Dòng tiền thuần (Free Cash Flow)** | **(1.800.000.000)** | **1.452.696.000** | **6.513.897.600** | **13.172.739.360** |
| Dòng tiền tích lũy | (1.800.000.000) | (347.304.000) | 6.166.593.600 | 19.339.332.960 |
| **Dòng tiền chiết khấu (tại WACC=12%)**| (1.800.000.000) | 1.297.050.000 | 5.192.839.298 | 8.379.622.753 |

### 📊 Tính toán các chỉ số thẩm định cốt lõi:
1. **NPV (Net Present Value - Giá trị hiện tại ròng):**
   $$\text{NPV} = -1.800.000.000 + 1.297.050.000 + 5.192.839.298 + 8.379.622.753 = \mathbf{13.069.512.051 \text{ VNĐ}}$$
2. **IRR (Internal Rate of Return - Tỷ suất sinh lời nội bộ):**
   $$\text{IRR} = \mathbf{195.4\%}$$
3. **Thời gian hoàn vốn có chiết khấu (Discounted Payback Period):**
   * **Thời gian hoàn vốn chính xác:** **1.38 năm (Khoảng 1 năm và 4 tháng).**

---

## 5.5. Phân tích điểm hòa vốn (Break-even Analysis)
* **Định phí bình quân tháng:** $307.915.000$ VNĐ/tháng.
* **Biến phí bình quân trên mỗi người dùng:** 10.000 VNĐ/người/tháng.
* **Doanh thu bình quân trên một thuê bao hỗn hợp (Weighted average ARPU):**
  $$\text{ARPU} = \frac{199.000 \times 1.200 + 399.000 \times 500}{1.700} \approx \mathbf{257.823 \text{ VNĐ/người/tháng}}$$

* **Điểm hòa vốn số lượng người dùng:**
  $$\text{Sản lượng hòa vốn} = \frac{\text{Định phí}}{\text{ARPU} - \text{Biến phí}} = \frac{307.915.000}{257.823 - 10.000} \approx \mathbf{1.242 \text{ người dùng}}$$

---

## 5.6. Phân tích độ nhạy của dự án (Sensitivity Analysis)
Để phòng ngừa các rủi ro biến động thị trường chứng khoán (chu kỳ sụt giảm thanh khoản), dự án tiến hành phân tích các kịch bản ảnh hưởng đến chỉ số NPV và IRR:

**Bảng 5.5: Kết quả phân tích độ nhạy NPV và IRR theo Kịch bản Doanh thu**

| Kịch bản phân tích | Doanh thu | NPV (VNĐ) | IRR (%) | Khả năng hoàn vốn |
| :--- | :--- | :--- | :--- | :--- |
| **Kịch bản Tốt (Thị trường Up-trend)** | Tăng 20% | 16.083.414.461 | 227.3% | 1.15 năm (Cực nhanh) |
| **Kịch bản Cơ sở (Kế hoạch)** | Giữ nguyên | **13.069.512.051** | **195.4%** | **1.38 năm** |
| **Kịch bản Xấu (Thị trường Down-trend)** | Giảm 30% | 8.548.658.436 | 147.2% | 1.76 năm (An toàn) |
