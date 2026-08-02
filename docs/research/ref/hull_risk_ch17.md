# Chương 17: Quản lý Thị trường Phái sinh OTC (Regulation of the OTC Derivatives Market)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Thanh toán trên thị trường OTC (Clearing in OTC Markets)
Trước 2008, thị trường OTC chủ yếu thanh toán song phương (bilateral clearing) và rất lỏng lẻo. Sau 2008, mọi thứ thay đổi.
*   **Bilateral Clearing (Thanh toán song phương):** Hai bên tự giao dịch và ký quỹ theo thỏa thuận ISDA Master Agreement.
*   **Central Clearing (Thanh toán tập trung - CCP):** Một đối tác trung tâm (Central Counterparty - CCP) chen vào giữa hai bên (trở thành người mua của người bán và người bán của người mua). CCP loại bỏ rủi ro đối tác giữa hai bên.

## 2. Ký quỹ (Margin)
*   **Variation Margin (Ký quỹ biến đổi):** Phản ánh sự thay đổi giá trị hàng ngày của danh mục. Nếu giá trị phái sinh tăng với bên A và giảm với bên B, bên B phải nộp Variation Margin cho bên A. Thường thanh toán bằng tiền mặt.
*   **Initial Margin (Ký quỹ ban đầu):** Là khoản đệm bổ sung phòng trường hợp đối tác vỡ nợ không nộp Variation Margin trong những ngày sau cùng (Margin Period of Risk / Cure Period). Trước 2008, giao dịch OTC hiếm khi có Initial Margin. Nay thì bắt buộc.

## 3. Những thay đổi Hậu khủng hoảng (Post-Crisis Regulatory Changes)
Tại Hội nghị G20 năm 2009 ở Pittsburgh, các nhà lãnh đạo đã thống nhất 3 yêu cầu cốt lõi cho thị trường OTC:
1.  **Thanh toán qua CCP:** Tất cả các phái sinh OTC được chuẩn hóa (standardized) phải được thanh toán qua CCP để giảm rủi ro hệ thống (Systemic Risk).
2.  **Giao dịch trên nền tảng điện tử:** Các sản phẩm chuẩn hóa phải giao dịch trên SEFs (Mỹ) hoặc OTFs (Châu Âu) để tăng tính minh bạch giá.
3.  **Báo cáo cho Trade Repositories:** Mọi giao dịch OTC phải báo cáo cho kho dữ liệu trung tâm để cơ quan quản lý nắm được tổng rủi ro của từng định chế (Tránh lặp lại vụ AIG).

## 4. Quy định cho Giao dịch Không qua CCP (Uncleared Trades)
Đối với các phái sinh quá phức tạp không thể thanh toán qua CCP, hai bên ngân hàng vẫn giao dịch song phương nhưng chịu quy định khắt khe hơn:
*   Phải nộp **cả Variation Margin và Initial Margin**.
*   Initial Margin không được bù trừ (như Variation Margin) mà phải được giữ ở một bên thứ ba (Trust) để bảo vệ.
*   **SIMM (Standard Initial Margin Model):** Do ISDA phát triển. Thay vì tính Initial Margin gộp thô (rất cao), SIMM dùng phương pháp Model-Building (xem Chương 14) với các trọng số rủi ro và độ nhạy do cơ quan quản lý chỉ định để tính Initial Margin hợp lý hơn, có xét đến đa dạng hóa rủi ro.

## 5. Tác động của các Thay đổi (Impact of the Changes)
*   **Tăng yêu cầu Ký quỹ:** Rất nhiều tiền mặt và tài sản an toàn (trái phiếu chính phủ) bị "nhốt" vào các tài khoản ký quỹ tại CCP hoặc bên thứ 3.
*   **Rủi ro Thanh khoản (Liquidity Risk):** Các ngân hàng chịu áp lực khổng lồ phải luôn có sẵn tài sản thanh khoản (HQLA) để đáp ứng Margin Calls ngay lập tức khi thị trường biến động.
*   **Hạn chế Rehypothecation (Tái thế chấp):** Trước khủng hoảng, bên A nhận tài sản thế chấp từ bên B có thể mang tài sản đó đi thế chấp cho bên C. Vụ Lehman phá sản khiến nhiều bên mất tài sản vì Rehypothecation. Hiện nay thực hành này bị cấm hoặc hạn chế nghiêm ngặt.
*   **Phá vỡ Netting (Bù trừ):** Trước đây, một ngân hàng có thể bù trừ mọi giao dịch (chuẩn và không chuẩn) với một đối tác. Nay, giao dịch chuẩn đưa vào CCP, giao dịch không chuẩn nằm ngoài, làm giảm hiệu quả bù trừ tổng thể, đẩy yêu cầu ký quỹ lên cao hơn nữa.

## 6. Rủi ro từ chính các CCP
*   Bằng cách chuyển rủi ro từ các "Ngân hàng quá lớn để sụp đổ" sang các CCP, hệ thống có thể tạo ra các "CCP quá lớn để sụp đổ".
*   Tuy nhiên, CCP dễ quản lý hơn ngân hàng vì mô hình kinh doanh của họ đơn giản (chỉ đứng giữa thanh toán, không cho vay, không tự doanh).

---
**Ghi chú:** Thị trường OTC và thị trường niêm yết (Exchange-traded) đang dần hội tụ. Giao dịch OTC ngày nay an toàn hơn nhiều nhưng chi phí vốn và thanh khoản mà các ngân hàng phải bỏ ra là rất lớn.
