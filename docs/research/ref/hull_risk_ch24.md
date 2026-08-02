# Chương 24: Rủi ro Thanh khoản (Liquidity Risk)
**Sách:** Risk Management and Financial Institutions (5th Edition)
**Tác giả:** John C. Hull

---

## 1. Hai Dạng Rủi ro Thanh khoản
Khủng hoảng 2008 cho thấy một ngân hàng có thể có đủ vốn (Solvent) nhưng vẫn phá sản vì thiếu thanh khoản (Liquid).
*   **Trading Liquidity Risk (Rủi ro thanh khoản giao dịch):** Rủi ro không thể bán một tài sản một cách nhanh chóng mà không làm giá giảm sâu. Liên quan đến tính thanh khoản của **Tài sản (Assets)**.
*   **Funding Liquidity Risk (Rủi ro thanh khoản nguồn vốn):** Rủi ro không thể huy động tiền mặt để đáp ứng các nghĩa vụ nợ đến hạn (như bị rút tiền gửi hàng loạt, hoặc đối tác từ chối gia hạn nợ). Liên quan đến tính thanh khoản của **Nguồn vốn (Liabilities)**.

## 2. Trading Liquidity Risk (Thanh khoản Giao dịch)
*   **Bid-Ask Spread:** Thước đo cơ bản nhất của thanh khoản thị trường. Chênh lệch càng lớn, thanh khoản càng kém.
*   **Liquidity-Adjusted VaR (VaR điều chỉnh thanh khoản):** Khi tính VaR, nếu tài sản khó bán, ta không thể dùng VaR 1 ngày. Phải tăng khoảng thời gian (Liquidity Horizon) lên số ngày thực tế cần thiết để xả hàng mà không gây sụp đổ giá.
*   **Cost of Liquidation (Chi phí thanh lý):** Khi bán khối lượng lớn, trader không thể bán được ở giá Mid-market mà sẽ làm giá dịch chuyển về phía bất lợi (Market Impact).

## 3. Funding Liquidity Risk (Thanh khoản Nguồn vốn)
*   **Liquidity Black Holes (Hố đen thanh khoản):** Xảy ra khi thị trường đột nhiên chỉ toàn người bán, không có người mua. Nguyên nhân thường do hành vi bầy đàn (herd behavior), khi mọi người dùng chung một mô hình cắt lỗ (stop-loss) hoặc chịu chung lệnh gọi ký quỹ (margin call).
*   **Vòng lặp phản hồi (Feedback Loops):** 
    *   Thị trường giảm $\rightarrow$ Ngân hàng bị lỗ $\rightarrow$ Margin call $\rightarrow$ Ngân hàng thiếu tiền $\rightarrow$ Phải bán tháo tài sản (Fire sale) $\rightarrow$ Thị trường tiếp tục giảm. 
    *   Đây là vòng lặp chết chóc phá hủy thanh khoản trong năm 2008.

## 4. Quản lý Rủi ro Thanh khoản (Quy định của Basel III)
Như đã nhắc ở Chương 16, Basel III ra đời hai quy định cốt lõi để ép ngân hàng quản trị rủi ro thanh khoản nguồn vốn:
1.  **LCR (Liquidity Coverage Ratio):** 
    $$LCR = \frac{Tài\_sản\_thanh\_khoản\_chất\_lượng\_cao\_(HQLA)}{Dòng\_tiền\_ra\_thuần\_trong\_30\_ngày\_căng\_thẳng} \ge 100\%$$
    *   Đảm bảo ngân hàng có đủ "đạn dược" (như tiền mặt, trái phiếu chính phủ) để sống sót qua một cơn hoảng loạn ngắn hạn.
2.  **NSFR (Net Stable Funding Ratio):** 
    $$NSFR = \frac{Nguồn\_vốn\_tài\_trợ\_ổn\_định\_hiện\_có}{Nguồn\_vốn\_tài\_trợ\_ổn\_định\_yêu\_cầu} \ge 100\%$$
    *   Hạn chế mô hình lấy nợ ngắn hạn (như Repo qua đêm) đi tài trợ cho tài sản dài hạn (như cho vay thế chấp 30 năm). Yêu cầu vốn dài hạn phải tương xứng với tài sản dài hạn.

## 5. Rủi ro Thanh khoản từ Phái sinh
*   Giao dịch phái sinh OTC có thể tạo ra các "hố đen" hút tiền mặt đột ngột do **Variation Margin calls**. 
*   Vụ phá sản nổi tiếng của **AIG (2008)** không phải do họ mất khả năng thanh toán dài hạn, mà do họ bị giáng các đòn Margin Call trị giá hàng tỷ USD trong một thời gian quá ngắn mà không có sẵn tiền mặt để nộp, dẫn đến khủng hoảng thanh khoản cục bộ.

---
**Ghi chú:** Thanh khoản giống như "oxy" của hệ thống tài chính. Bạn có thể nhịn ăn (thua lỗ vốn) trong vài tuần, nhưng không thể nhịn thở (thiếu thanh khoản) quá vài phút.
