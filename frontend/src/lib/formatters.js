export function formatMoney(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }
  return new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 }).format(
    Number(value)
  );
}

export function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }
  return Number(value).toFixed(digits);
}

export function formatChartValue(value, valueSuffix = "") {
  const suffix = valueSuffix || "";
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return `-${suffix}`;
  }
  if (suffix.trim().toUpperCase() === "VND" || suffix.includes("đ")) {
    return `${formatMoney(value)}${suffix}`;
  }
  if (suffix === "%") return `${formatNumber(value, 1)}%`;
  return `${formatNumber(value, 2)}${suffix}`;
}

export function signalClass(signal = "") {
  const normalized = signal.toUpperCase();
  if (normalized.includes("STRONG")) return "badge badge-success-strong";
  if (normalized.includes("BUY")) return "badge badge-success";
  if (normalized.includes("SKIP") || normalized.includes("DANGER")) {
    return "badge badge-danger";
  }
  return "badge badge-muted";
}

export function formatSignal(signal = "", isEnglish = false) {
  if (!signal) return "-";
  const normalized = signal.toUpperCase();
  if (!isEnglish) return signal;
  if (normalized.includes("STRONG")) return "STRONG BUY";
  if (normalized.includes("BUY")) return "BUY";
  if (normalized.includes("THANH KHOẢN") || normalized.includes("LIQUID")) {
    return "SKIP (LOW LIQUIDITY)";
  }
  if (normalized.includes("SKIP")) return "SKIP";
  return signal;
}
