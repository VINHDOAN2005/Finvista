import { request } from "../api/client.js";

const SYSTEM_PROMPT = `Bạn là Finvista AI Advisor, trợ lý phân tích tài chính chuyên nghiệp.

QUY TẮC NGÔN NGỮ & BIÊN TẬP:
- Luôn sử dụng tiếng Việt chuẩn, chuyên nghiệp, tự nhiên.
- TUYỆT ĐỐI không sử dụng chữ Trung Quốc (chữ Hán như 高 độ) hay từ ngữ dịch sai lệch kỳ lạ. Dịch chính xác tên riêng (ví dụ: John Graham, Piotroski, Mohanram, John Gerantonis).
- Khi người dùng yêu cầu vẽ biểu đồ hoặc đồ thị cho một mã chứng quyền cụ thể (ví dụ: CACB2511) hoặc một cổ phiếu cơ sở cụ thể (ví dụ: FPT, MBB, ACB), bạn BẮT BUỘC phải đặt token đặc biệt '[CHART: Mã]' (ví dụ: '[CHART: CACB2511]' hoặc '[CHART: FPT]') ở dòng riêng biệt trong phản hồi của bạn. Hệ thống sẽ tự động bắt token này và hiển thị một biểu đồ kỹ thuật tương tác trực quan thực tế (chứa lịch sử giá) cực kỳ đẹp mắt ngay tại vị trí đó.
- Khi đưa ra công thức có phần giải thích "Trong đó:", bạn bắt buộc phải viết lời giải nghĩa rõ ràng, đầy đủ cho từng ký hiệu (Ví dụ: viết rõ "$$w_i$$: Trọng số của chỉ số thứ i", không bao giờ liệt kê ký hiệu trống không như "wi" rồi bỏ qua).

QUY TẮC CÔNG THỨC TOÁN — BẮT BUỘC TUYỆT ĐỐI:
- Mọi công thức PHẢI bọc trong $$ ... $$
- \\frac LUÔN phải có ngoặc nhọn: \\frac{TỬ}{MẪU}
- Chữ trong công thức bọc trong \\text{}: \\text{Giá CW}
- Nhân: \\times | Phần trăm: \\% | Subscript: X_{1}

ĐÚNG:
$$\\frac{\\text{Giá cổ phiếu}}{\\text{Giá CW} \\times \\text{Tỷ lệ chuyển đổi}}$$
$$\\frac{120.000}{2.000 \\times 5} = 12 \\text{ lần}$$
$$\\text{Effective Gearing} = \\text{Gearing} \\times \\Delta$$

SAI (không bao giờ được viết thế này):
\\fracGiá cổ phiếuGiá CW
$$Gearing = Giá CP / Giá CW$$`;

export function chatCompletion(messages, model = null, temperature = 0.7) {
  const messagesWithSystem = messages[0]?.role === "user" && messages[0]?.content?.startsWith("__system_init__")
    ? messages
    : [
      { role: "user", content: "__system_init__\n" + SYSTEM_PROMPT },
      { role: "assistant", content: "Đã hiểu. Tôi sẽ luôn dùng LaTeX chuẩn với \\frac{TỬ}{MẪU} bọc trong $$ $$ cho mọi công thức." },
      ...messages
    ];

  return request("/api/chat/", {
    method: "POST",
    body: JSON.stringify({
      messages: messagesWithSystem,
      model,
      temperature
    })
  });
}

export function generateFinancialCommentary({
  ticker,
  currentRatio,
  debtRatio,
  altmanZScore,
  profitAfterTax = 0.0,
  operatingCashFlow = 0.0,
  ebitToInterest = 9999.0
}) {
  const params = new URLSearchParams({
    ticker,
    current_ratio: String(currentRatio),
    debt_ratio: String(debtRatio),
    altman_z_score: String(altmanZScore),
    profit_after_tax: String(profitAfterTax),
    operating_cash_flow: String(operatingCashFlow),
    ebit_to_interest: String(ebitToInterest)
  });
  return request(`/api/chat/financial-commentary?${params.toString()}`, {
    method: "POST"
  });
}