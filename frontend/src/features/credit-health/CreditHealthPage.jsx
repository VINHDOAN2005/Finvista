import React, { useEffect, useState } from "react";
import { AlertTriangle, BarChart3, RefreshCw, Search, ShieldCheck } from "lucide-react";

import { getCreditHealth } from "../../api.js";
import { Button } from "../../components/ui/button.jsx";
import { Input } from "../../components/ui/input.jsx";
import { ErrorBox, LoadingBox, MetricCard } from "../../components/ui/status.jsx";
import { formatNumber } from "../../lib/formatters.js";

// Set to true to show the AI (SHAP) model explanations section during presentations
const SHOW_SHAP_EXPLANATION = false;

function Ratio({ label, value }) {
  return (
    <div className="ratio-item">
      <span>{label}</span>
      <strong>{formatNumber(value, 4)}</strong>
    </div>
  );
}

function RatioText({ label, value, tone = "" }) {
  return (
    <div className={`ratio-item ${tone}`}>
      <span>{label}</span>
      <strong>{value || "-"}</strong>
    </div>
  );
}

function KpiGroup({ title, description, children }) {
  return (
    <section className="kpi-group">
      <div className="kpi-group-heading">
        <span>{title}</span>
        {description ? <p>{description}</p> : null}
      </div>
      {children}
    </section>
  );
}

function formatRiskZone(zone, isEnglish) {
  const normalized = String(zone || "").toUpperCase();
  if (!zone) return "-";
  if (isEnglish) return zone;
  if (normalized.includes("DANGER")) return "NGUY HIỂM (ĐỎ)";
  if (normalized.includes("WARNING")) return "CẢNH BÁO (XÁM)";
  if (normalized.includes("SAFE")) return "AN TOÀN (XANH)";
  return zone;
}

function formatStatusDescription(description, zone, isEnglish) {
  if (isEnglish) return description || "";
  const normalized = String(zone || "").toUpperCase();
  if (normalized.includes("DANGER")) {
    return "Doanh nghiệp có dấu hiệu suy yếu tài chính nghiêm trọng. Cần tránh chiến lược rủi ro cao.";
  }
  if (normalized.includes("WARNING")) {
    return "Tình hình tài chính chưa ổn định. Nên dùng chiến lược phòng thủ và kiểm tra thêm dữ liệu.";
  }
  if (normalized.includes("SAFE")) {
    return "Điểm tín dụng doanh nghiệp tốt. Nền tảng tài chính đang ổn định.";
  }
  return description || "";
}

function formatDistressFlag(value, isEnglish) {
  return value ? (isEnglish ? "Distressed" : "Có rủi ro") : (isEnglish ? "Normal" : "Bình thường");
}

function getRiskTone(zone) {
  const normalized = String(zone || "").toUpperCase();
  if (normalized.includes("DANGER")) return "danger";
  if (normalized.includes("WARNING")) return "warning";
  if (normalized.includes("SAFE")) return "success";
  return "default";
}

function getRiskBadgeText(zone, isEnglish) {
  const normalized = String(zone || "").toUpperCase();
  if (!zone) return isEnglish ? "Unknown" : "Không rõ";
  if (normalized.includes("DANGER")) return isEnglish ? "Distressed" : "Nguy hiểm";
  if (normalized.includes("WARNING")) return isEnglish ? "Warning" : "Cảnh báo";
  if (normalized.includes("SAFE")) return isEnglish ? "Normal" : "An toàn";
  return zone;
}

function pickMetricTone(label, value, fallbackTone) {
  const normalized = String(label || "").toLowerCase();
  const numericValue = Number(value);

  if (normalized.includes("debt") && Number.isFinite(numericValue)) {
    if (numericValue > 0.6) return "danger";
    if (numericValue < 0.4) return "success";
    return "warning";
  }

  if (normalized.includes("liquidity") && Number.isFinite(numericValue)) {
    if (numericValue > 1.5) return "success";
    if (numericValue < 0.8) return "danger";
    return "warning";
  }

  if ((normalized.includes("roa") || normalized.includes("roe")) && Number.isFinite(numericValue)) {
    if (numericValue > 0) return "success";
    return "warning";
  }

  if (normalized.includes("icr") && Number.isFinite(numericValue)) {
    if (numericValue > 3) return "success";
    if (numericValue < 1) return "danger";
    return "warning";
  }

  if (normalized.includes("ocf") && Number.isFinite(numericValue)) {
    if (numericValue > 0.1) return "success";
    return "warning";
  }

  return fallbackTone;
}

export function CreditHealthPage({ language = "vi" }) {
  const isEnglish = language === "en";
  const [ticker, setTicker] = useState("HPG");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function searchTicker() {
    if (!ticker.trim()) return;
    setLoading(true);
    setError("");
    try {
      setData(await getCreditHealth(ticker));
    } catch (err) {
      setError(err.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    searchTicker();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const metrics = data?.credit_metrics || {};
  const ratios = data?.financial_ratios || {};
  const scores = data?.distress_scores || {};
  const zoneTone = getRiskTone(metrics.risk_zone);
  const riskBadgeText = getRiskBadgeText(metrics.risk_zone, isEnglish);
  const riskProbabilityPercent = (metrics.bankruptcy_probability || 0) * 100;
  const alertSummary = formatStatusDescription(metrics.status_description, metrics.risk_zone, isEnglish);

  return (
    <section className="page-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{isEnglish ? "Enterprise risk" : "Rủi ro doanh nghiệp"}</p>
          <h2>{isEnglish ? "Credit Health" : "Sức khỏe tín dụng"}</h2>
        </div>
      </div>

      <div className="search-row">
        <Input
          value={ticker}
          onChange={(event) => setTicker(event.target.value.toUpperCase())}
          onKeyDown={(event) => event.key === "Enter" && searchTicker()}
          placeholder={isEnglish ? "Enter ticker: HPG, FPT, VIC..." : "Nhập mã cổ phiếu: HPG, FPT, VIC..."}
        />
        <Button onClick={searchTicker}><Search size={16} />{isEnglish ? "Search" : "Tra cứu"}</Button>
        <Button variant="secondary" onClick={searchTicker}><RefreshCw size={16} />{isEnglish ? "Refresh" : "Làm mới"}</Button>
      </div>

      {error ? <ErrorBox message={error} language={language} /> : null}
      {loading ? <LoadingBox message={isEnglish ? "Loading credit health..." : "Đang tải sức khỏe tín dụng..."} /> : null}

      {data ? (
        <>
          <div className="credit-hero-card">
            <div className="credit-hero-main">
              <div className="credit-hero-badges">
                <span className={`status-pill ${zoneTone}`}>{riskBadgeText}</span>
                <span className="credit-hero-meta">{data.ticker} · {isEnglish ? "Risk overview" : "Tổng quan rủi ro"}</span>
              </div>
              <h3>{data.ticker} · {isEnglish ? "Credit risk overview" : "Tổng quan tín dụng"}</h3>
              <p>{alertSummary}</p>
            </div>
            <div className="credit-hero-side">
              <div className="credit-probability-card" data-testid="risk-probability-gauge">
                <div className="probability-label">{isEnglish ? "Risk probability" : "Xác suất rủi ro"}</div>
                <div className="probability-gauge">
                  <div className={`probability-fill ${zoneTone}`} style={{ width: `${Math.min(100, Math.max(0, riskProbabilityPercent))}%` }} />
                </div>
                <div className="probability-values">
                  <strong>{riskProbabilityPercent.toFixed(1)}%</strong>
                  <span>{riskBadgeText}</span>
                </div>
              </div>
            </div>
          </div>

          {data.is_bank ? (
            <>
              <KpiGroup
                title={isEnglish ? "Risk snapshot" : "Tóm tắt rủi ro"}
                description={isEnglish ? "Read this first to decide whether the bank is safe enough for CW strategies." : "Đọc nhóm này trước để biết ngân hàng có đủ an toàn cho chiến lược CW không."}
              >
                <div className="metric-grid credit-metric-grid">
                  <MetricCard label={isEnglish ? "Ticker" : "Mã cổ phiếu"} value={data.ticker} detail={`${isEnglish ? "Year" : "Năm"} ${data.reported_year}`} />
                  <MetricCard label={isEnglish ? "Capital Adequacy (CAR)" : "An toàn vốn (CAR)"} value={`${formatNumber((ratios.car || 0) * 100, 2)}%`} tone={zoneTone} />
                  <MetricCard label={isEnglish ? "Risk zone" : "Vùng rủi ro"} value={formatRiskZone(metrics.risk_zone, isEnglish)} tone={zoneTone} />
                  <MetricCard label={isEnglish ? "Risk probability" : "Xác suất rủi ro"} value={`${formatNumber((metrics.bankruptcy_probability || 0) * 100, 1)}%`} tone={zoneTone} />
                </div>
              </KpiGroup>

              <KpiGroup
                title={isEnglish ? "CAMELS Quality Metrics" : "Chất lượng CAMELS"}
                description={isEnglish ? "Capital adequacy, asset quality, earnings, liquidity, and sensitivity." : "Độ an toàn vốn, chất lượng tài sản, năng lực quản lý, hiệu quả sinh lời và thanh khoản."}
              >
                <div className="ratio-grid quality-grid">
                  <Ratio label={isEnglish ? "Capital Adequacy (CAR)" : "An toàn vốn (CAR)"} value={ratios.car} />
                  <Ratio label={isEnglish ? "Bad Debt Ratio (NPL)" : "Tỷ lệ nợ xấu (NPL)"} value={ratios.npl} />
                  <Ratio label={isEnglish ? "Bad Debt Coverage (LLR)" : "Bao phủ nợ xấu (LLR)"} value={ratios.llr} />
                  <Ratio label={isEnglish ? "Cost-to-Income (CIR)" : "Hiệu quả chi phí (CIR)"} value={ratios.cir} />
                  <Ratio label={isEnglish ? "Net Interest Margin (NIM)" : "Biên lãi ròng (NIM)"} value={ratios.nim} />
                  <Ratio label={isEnglish ? "Loan-to-Deposit (LDR)" : "Tỷ lệ dư nợ/huy động (LDR)"} value={ratios.ldr} />
                  <Ratio label="ROE" value={ratios.roe} />
                </div>
              </KpiGroup>

              <KpiGroup
                title={isEnglish ? "Bank Risk Assessment" : "Đánh giá rủi ro ngân hàng"}
                description={isEnglish ? "Specialized financial institution risk parameters." : "Các chỉ báo rủi ro định chế tài chính chuyên biệt."}
              >
                <div className="distress-comparison-list">
                  <div className="distress-row distress-row-head">
                    <span>{isEnglish ? "Indicator" : "Chỉ báo"}</span>
                    <span>{isEnglish ? "Signal" : "Tín hiệu"}</span>
                  </div>
                  <div className="distress-row">
                    <span>{isEnglish ? "CAMELS rating" : "Xếp hạng CAMELS"}</span>
                    <span className={`signal-pill ${zoneTone}`}>{formatRiskZone(metrics.risk_zone, isEnglish)}</span>
                  </div>
                  <div className="distress-row">
                    <span>{isEnglish ? "Market sensitivity" : "Độ nhạy thị trường"}</span>
                    <span className="signal-pill success">{isEnglish ? "Low / Stable" : "Thấp / An toàn"}</span>
                  </div>
                  <div className="distress-row">
                    <span>{isEnglish ? "ML distress alert" : "ML cảnh báo"}</span>
                    <span className={`signal-pill ${metrics.is_ml_distressed ? "danger" : "success"}`}>{formatDistressFlag(metrics.is_ml_distressed, isEnglish)}</span>
                  </div>
                </div>
              </KpiGroup>

              {SHOW_SHAP_EXPLANATION && data.shap_contributions && Object.keys(data.shap_contributions).length ? (
                <KpiGroup
                  title={isEnglish ? "XAI Model Explanations (SHAP)" : "Giải thích mô hình AI (SHAP)"}
                  description={isEnglish ? "Key drivers pushing the bank rating towards Safe (green/negative) or Distress (red/positive)." : "Các chỉ báo chính đóng góp đẩy điểm tín dụng ngân hàng về Safe (xanh/âm) hoặc Distress (đỏ/dương)."}
                >
                  <div className="shap-container" style={{ display: "flex", flexDirection: "column", gap: "0.75rem", padding: "1rem", background: "rgba(255, 255, 255, 0.03)", borderRadius: "6px" }}>
                    {Object.entries(data.shap_contributions).map(([feature, val]) => {
                      const maxVal = Math.max(...Object.values(data.shap_contributions).map(Math.abs)) || 1.0;
                      const percentage = Math.min(50, (Math.abs(val) / maxVal) * 50);
                      const isDanger = val > 0;
                      return (
                        <div key={feature} style={{ display: "grid", gridTemplateColumns: "150px 1fr 60px", alignItems: "center", gap: "1rem" }}>
                          <span style={{ fontSize: "0.85rem", fontWeight: "600", color: "var(--text-muted)" }}>
                            {feature.toUpperCase()}
                          </span>
                          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", height: "16px", background: "rgba(255,255,255,0.02)", borderRadius: "4px", overflow: "hidden" }}>
                            <div style={{ display: "flex", justifyContent: "flex-end" }}>
                              {!isDanger ? (
                                <div style={{ width: `${percentage * 2}%`, background: "rgba(46, 196, 182, 0.85)", height: "100%", borderTopLeftRadius: "4px", borderBottomLeftRadius: "4px" }} />
                              ) : null}
                            </div>
                            <div style={{ display: "flex", justifyContent: "flex-start" }}>
                              {isDanger ? (
                                <div style={{ width: `${percentage * 2}%`, background: "rgba(230, 57, 70, 0.85)", height: "100%", borderTopRightRadius: "4px", borderBottomRightRadius: "4px" }} />
                              ) : null}
                            </div>
                          </div>
                          <span style={{ fontSize: "0.8rem", fontWeight: "600", textAlign: "right", color: isDanger ? "#e63946" : "#2ec4b6" }}>
                            {val > 0 ? "+" : ""}{val.toFixed(4)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </KpiGroup>
              ) : null}
              <div className={`advisory-banner ${zoneTone}`}>
                <AlertTriangle size={16} />
                <div>
                  <strong>{isEnglish ? "Advisory" : "Khuyến nghị"}</strong>
                  <p>{metrics.status_description}</p>
                </div>
              </div>
            </>
          ) : (
            <>
              <KpiGroup
                title={isEnglish ? "Risk snapshot" : "Tóm tắt rủi ro"}
                description={isEnglish ? "Read this first to decide whether the ticker is safe enough for CW strategies." : "Đọc nhóm này trước để biết mã có đủ an toàn cho chiến lược CW không."}
              >
                <div className="metric-grid credit-metric-grid">
                  <MetricCard label={isEnglish ? "Ticker" : "Mã cổ phiếu"} value={data.ticker} detail={`${isEnglish ? "Year" : "Năm"} ${data.reported_year}`} />
                  <MetricCard label="Altman Z-score" value={formatNumber(metrics.altman_z_score, 2)} tone={zoneTone} />
                  <MetricCard label={isEnglish ? "Risk zone" : "Vùng rủi ro"} value={formatRiskZone(metrics.risk_zone, isEnglish)} tone={zoneTone} />
                  <MetricCard label={isEnglish ? "Risk probability" : "Xác suất rủi ro"} value={`${formatNumber((metrics.bankruptcy_probability || 0) * 100, 1)}%`} tone={zoneTone} />
                </div>
              </KpiGroup>

              <KpiGroup
                title={isEnglish ? "Financial quality" : "Chất lượng tài chính"}
                description={isEnglish ? "Liquidity, leverage, profitability, and debt-service capacity." : "Thanh khoản, đòn bẩy, khả năng sinh lời và khả năng trả lãi/nợ."}
              >
                <div className="ratio-grid quality-grid">
                  <Ratio label={isEnglish ? "Debt ratio" : "Tỷ lệ nợ"} value={ratios.leverage_debt_ratio} />
                  <Ratio label={isEnglish ? "Liquidity" : "Thanh khoản"} value={ratios.liquidity_current_ratio} />
                  <Ratio label="ROA" value={ratios.roa} />
                  <Ratio label="ROE" value={ratios.roe} />
                  <Ratio label="EBIT/tài sản" value={ratios.ebit_to_assets} />
                  <Ratio label="ICR" value={ratios.icr} />
                  <Ratio label="OCF/debt" value={ratios.ocf_to_total_debt} />
                </div>
              </KpiGroup>

              <KpiGroup
                title={isEnglish ? "Distress models" : "Mô hình cảnh báo"}
                description={isEnglish ? "Cross-check statistical and rule-based distress signals before trusting a setup." : "Đối chiếu nhiều mô hình cảnh báo trước khi tin một setup."}
              >
                <div className="distress-comparison-list">
                  <div className="distress-row distress-row-head">
                    <span>{isEnglish ? "Model" : "Mô hình"}</span>
                    <span>{isEnglish ? "Score" : "Điểm"}</span>
                    <span>{isEnglish ? "Signal" : "Tín hiệu"}</span>
                  </div>
                  <div className="distress-row">
                    <span>Altman</span>
                    <span>{formatRiskZone(scores.altman_zone, isEnglish)}</span>
                    <span className={`signal-pill ${zoneTone}`}>{formatRiskZone(scores.altman_zone, isEnglish)}</span>
                  </div>
                  <div className="distress-row">
                    <span>Springate</span>
                    <span>{formatNumber(scores.springate_s_score, 3)}</span>
                    <span className={`signal-pill ${scores.springate_distressed ? "danger" : "success"}`}>{formatDistressFlag(scores.springate_distressed, isEnglish)}</span>
                  </div>
                  <div className="distress-row">
                    <span>Zmijewski</span>
                    <span>{formatNumber(scores.zmijewski_x_score, 3)}</span>
                    <span className={`signal-pill ${scores.zmijewski_distressed ? "danger" : "success"}`}>{formatDistressFlag(scores.zmijewski_distressed, isEnglish)}</span>
                  </div>
                  <div className="distress-row">
                    <span>ML</span>
                    <span>{isEnglish ? "Model" : "Mô hình"}</span>
                    <span className={`signal-pill ${metrics.is_ml_distressed ? "danger" : "success"}`}>{formatDistressFlag(metrics.is_ml_distressed, isEnglish)}</span>
                  </div>
                </div>
              </KpiGroup>

              {SHOW_SHAP_EXPLANATION && data.shap_contributions && Object.keys(data.shap_contributions).length ? (
                <KpiGroup
                  title={isEnglish ? "XAI Model Explanations (SHAP)" : "Giải thích mô hình AI (SHAP)"}
                  description={isEnglish ? "Key drivers pushing the XGBoost rating towards Safe (green/negative) or Distress (red/positive)." : "Các chỉ báo chính đóng góp đẩy điểm XGBoost về Safe (xanh/âm) hoặc Distress (đỏ/dương)."}
                >
                  <div className="shap-container" style={{ display: "flex", flexDirection: "column", gap: "0.75rem", padding: "1rem", background: "rgba(255, 255, 255, 0.03)", borderRadius: "6px" }}>
                    {Object.entries(data.shap_contributions).map(([feature, val]) => {
                      const maxVal = Math.max(...Object.values(data.shap_contributions).map(Math.abs)) || 1.0;
                      const percentage = Math.min(50, (Math.abs(val) / maxVal) * 50);
                      const isDanger = val > 0;
                      return (
                        <div key={feature} style={{ display: "grid", gridTemplateColumns: "150px 1fr 60px", alignItems: "center", gap: "1rem" }}>
                          <span style={{ fontSize: "0.85rem", fontWeight: "600", color: "var(--text-muted)" }}>
                            {feature}
                          </span>
                          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", height: "16px", background: "rgba(255,255,255,0.02)", borderRadius: "4px", overflow: "hidden" }}>
                            <div style={{ display: "flex", justifyContent: "flex-end" }}>
                              {!isDanger ? (
                                <div style={{ width: `${percentage * 2}%`, background: "rgba(46, 196, 182, 0.85)", height: "100%", borderTopLeftRadius: "4px", borderBottomLeftRadius: "4px" }} />
                              ) : null}
                            </div>
                            <div style={{ display: "flex", justifyContent: "flex-start" }}>
                              {isDanger ? (
                                <div style={{ width: `${percentage * 2}%`, background: "rgba(230, 57, 70, 0.85)", height: "100%", borderTopRightRadius: "4px", borderBottomRightRadius: "4px" }} />
                              ) : null}
                            </div>
                          </div>
                          <span style={{ fontSize: "0.8rem", fontWeight: "600", textAlign: "right", color: isDanger ? "#e63946" : "#2ec4b6" }}>
                            {val > 0 ? "+" : ""}{val.toFixed(4)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </KpiGroup>
              ) : null}
              <div className={`advisory-banner ${zoneTone}`}>
                <AlertTriangle size={16} />
                <div>
                  <strong>{isEnglish ? "Advisory" : "Khuyến nghị"}</strong>
                  <p>{formatStatusDescription(metrics.status_description, metrics.risk_zone, isEnglish)}</p>
                </div>
              </div>
            </>
          )}
        </>
      ) : null}
    </section>
  );
}
