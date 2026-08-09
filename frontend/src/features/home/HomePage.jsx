import React, { useEffect, useState } from "react";
import { Activity, BarChart3, ShieldCheck, TrendingUp } from "lucide-react";

import { getOpportunities } from "../../api.js";
import { formatNumber } from "../../lib/formatters.js";

export function HomePage({ setPage, setSelectedSymbol, language }) {
  const isEnglish = language === "en";
  const [marketBrief, setMarketBrief] = useState(null);
  const [briefLoading, setBriefLoading] = useState(false);
  const [briefError, setBriefError] = useState("");

  useEffect(() => {
    loadBrief();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadBrief({ forceRefresh = false } = {}) {
    setBriefLoading(true);
    setBriefError("");
    try {
      const result = await getOpportunities({
        strategy: "balanced",
        underlying: "",
        limit: 1000,
        forceRefresh,
        vn30Only: false
      });
      setMarketBrief(result);
    } catch (err) {
      setBriefError(err.message);
    } finally {
      setBriefLoading(false);
    }
  }

  const briefRows = marketBrief?.recommendations || [];
  const statusPriority = { BUY: 0, WATCH: 1, NEUTRAL: 2, SKIP: 3 };

  function normalizeSignalStatus(signal = "") {
    const value = String(signal || "").toUpperCase();
    if (value.includes("BUY") || value.includes("STRONG")) return "BUY";
    if (value.includes("WATCH")) return "WATCH";
    if (value.includes("SKIP")) return "SKIP";
    return "NEUTRAL";
  }

  function getTradingValue(row) {
    const volume = Math.max(0, Number(row.volume) || 0);
    const price = Math.max(0, Number(row.market_price) || 0);
    return volume * price;
  }

  const rankedRows = [...briefRows]
    .map((row) => ({
      ...row,
      status: normalizeSignalStatus(row.recommendation_signal),
      score: Number(row.composite_g_score) || 0,
      tradingValue: getTradingValue(row),
      iv: Number(row.implied_volatility_pct) || 0,
      hv: Number(row.historical_volatility_pct) || 0
    }))
    .sort((a, b) => {
      const statusDelta = (statusPriority[a.status] ?? 99) - (statusPriority[b.status] ?? 99);
      if (statusDelta !== 0) return statusDelta;
      const scoreDelta = (b.score || 0) - (a.score || 0);
      if (scoreDelta !== 0) return scoreDelta;
      const tradingDelta = (b.tradingValue || 0) - (a.tradingValue || 0);
      if (tradingDelta !== 0) return tradingDelta;
      const ivDelta = (b.iv || 0) - (a.iv || 0);
      if (ivDelta !== 0) return ivDelta;
      return (b.hv || 0) - (a.hv || 0);
    });

  const briefDisplayRows = rankedRows.slice(0, 6);
  const topSignal = rankedRows.find((row) => row.status === "BUY") || rankedRows[0] || null;
  const signals = topSignal
    ? [topSignal, ...rankedRows.filter((row) => row.warrant_symbol !== topSignal.warrant_symbol).slice(0, 5)]
    : rankedRows.slice(0, 6);
  const buyCount = briefRows.filter((row) => normalizeSignalStatus(row.recommendation_signal) === "BUY").length;
  const skipCount = briefRows.filter((row) => normalizeSignalStatus(row.recommendation_signal) === "SKIP").length;
  const neutralCount = briefRows.filter((row) => {
    const status = normalizeSignalStatus(row.recommendation_signal);
    return status === "WATCH" || status === "NEUTRAL";
  }).length;

  function openWarrantDetail(symbol) {
    if (!symbol) return;
    setSelectedSymbol(symbol.trim().toUpperCase());
    setPage("detail");
  }

  return (
    <section className="intro-grid hero-layout finvista-hero">
      <div className="hero-atmosphere" aria-hidden="true">
        <span className="hero-orbit-core" />
        <span className="hero-scan-plane" />
        <span className="hero-data-stream stream-a" />
        <span className="hero-data-stream stream-b" />
        {/* Ticker ribbon 1 – duplicate for seamless loop */}
        <div className="ticker-ribbon ticker-ribbon-one">
          <span>VN30 +0.8%</span>
          <span>FPT +1.2%</span>
          <span>STB +0.5%</span>
          <span>MWG -0.7%</span>
          <span>HPG +1.4%</span>
          <span>VCB +0.3%</span>
          <span>TCB -0.2%</span>
          <span>VNM +0.9%</span>
          {/* duplicate for seamless loop */}
          <span>VN30 +0.8%</span>
          <span>FPT +1.2%</span>
          <span>STB +0.5%</span>
          <span>MWG -0.7%</span>
          <span>HPG +1.4%</span>
          <span>VCB +0.3%</span>
          <span>TCB -0.2%</span>
          <span>VNM +0.9%</span>
        </div>
        {/* Ticker ribbon 2 – financial terms */}
        <div className="ticker-ribbon ticker-ribbon-two">
          <span>CW Flow</span>
          <span>Delta</span>
          <span>IV/HV</span>
          <span>Credit Health</span>
          <span>G-score</span>
          <span>Z-score</span>
          <span>Theta</span>
          <span>Gearing</span>
          {/* duplicate for seamless loop */}
          <span>CW Flow</span>
          <span>Delta</span>
          <span>IV/HV</span>
          <span>Credit Health</span>
          <span>G-score</span>
          <span>Z-score</span>
          <span>Theta</span>
          <span>Gearing</span>
        </div>
      </div>


      <div className="intro-copy hero-copy-panel">
        <div className="brand-eyebrow">Finvista</div>
        <h1>{isEnglish ? "Quant analytics for smarter warrant decisions" : "Phân tích định lượng cho quyết định chứng quyền"}</h1>
        <p className="intro-text">
          {isEnglish
            ? "Track covered warrants, quantitative signals, and enterprise credit health from one focused workspace."
            : "Theo dõi chứng quyền, tín hiệu định lượng và sức khỏe tài chính doanh nghiệp trong một không gian gọn, dễ đọc."}
        </p>

        <div className="hero-signal-row" aria-label={isEnglish ? "Finvista analytics highlights" : "Điểm nổi bật phân tích Finvista"}>
          <HeroMetric icon={<TrendingUp />} label={isEnglish ? "VN30 CW pulse" : "Nhịp CW VN30"} value={isEnglish ? "Live scan" : "Quét live"} />
          <HeroMetric icon={<BarChart3 />} label={isEnglish ? "Signal stack" : "Bộ tín hiệu"} value="G-score" />
          <HeroMetric icon={<ShieldCheck />} label={isEnglish ? "Credit layer" : "Lớp tín dụng"} value="Z-score" />
        </div>

        <div className="intro-actions">
          <button className="primary-button" onClick={() => setPage("cw")}>
            {isEnglish ? "Open CW list" : "Mở danh sách CW"}
          </button>
          <button className="secondary-button" onClick={() => setPage("market")}>
            {isEnglish ? "Open market overview" : "Mở tổng quan thị trường"}
          </button>
          <button className="secondary-button" onClick={() => setPage("credit")}>
            {isEnglish ? "Check enterprise data" : "Dữ liệu doanh nghiệp"}
          </button>
        </div>

        <div className="hero-preview-board" aria-hidden="true">
          <div className="preview-orbit">
            <span />
            <i />
          </div>
          <div className="preview-chart">
            <span style={{ height: "38%" }} />
            <span style={{ height: "64%" }} />
            <span style={{ height: "52%" }} />
            <span style={{ height: "82%" }} />
            <span style={{ height: "70%" }} />
          </div>
          <div className="preview-heat">
            <i className="up" />
            <i className="down" />
            <i className="up wide" />
            <i className="flat" />
          </div>
        </div>
      </div>

      <div className="market-panel news-panel hero-market-panel" aria-label="Finvista market brief">
        <div className="panel-header">
          <span><Activity size={16} /> {isEnglish ? "CW market brief" : "Bảng tin CW"}</span>
          <button className="link-button" onClick={() => setPage("cw")}>
            {isEnglish ? "View table" : "Xem bảng"}
          </button>
        </div>
        <div className="market-visual">
          {briefLoading ? (
            <div className="market-tile highlight">
              <span>{isEnglish ? "Loading" : "Đang tải"}</span>
              <strong>{isEnglish ? "Fetching CW signals..." : "Đang lấy tín hiệu CW..."}</strong>
            </div>
          ) : null}

          {briefError ? (
            <div className="market-tile warning">
              <span>{isEnglish ? "API status" : "Trạng thái API"}</span>
              <strong>{isEnglish ? "CW brief unavailable" : "Chưa lấy được bảng tin CW"}</strong>
              <small>{briefError}</small>
            </div>
          ) : null}

          {!briefLoading && !briefError && topSignal ? (
            <>
              <div className="signal-section-title" aria-label={isEnglish ? "Top signal section" : "Phần tín hiệu nổi bật"}>
                <span className="signal-section-line" />
                <span className="signal-section-label">{isEnglish ? "TOP SIGNAL" : "TÍN HIỆU NỔI BẬT"}</span>
                <span className="signal-section-line" />
              </div>
              <div className="brief-list">
                {signals.map((signal) => (
                  <SignalCard
                    key={signal.warrant_symbol}
                    signal={signal}
                    isEnglish={isEnglish}
                    onClick={() => openWarrantDetail(signal.warrant_symbol)}
                  />
                ))}
              </div>
              <div className="market-tile-row">
                <div className="market-tile">
                  <span>{isEnglish ? "Buy signals" : "Tín hiệu mua"}</span>
                  <strong>{buyCount}</strong>
                </div>
                <div className="market-tile">
                  <span>{isEnglish ? "Consider signals" : "Tín hiệu xem xét"}</span>
                  <strong>{neutralCount}</strong>
                </div>
                <div className="market-tile">
                  <span>{isEnglish ? "Skip signals" : "Tín hiệu bỏ qua"}</span>
                  <strong>{skipCount}</strong>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>

      <div className="feature-strip">
        <FeatureCard
          title={isEnglish ? "CW opportunities" : "Cơ hội CW"}
          text={
            isEnglish
              ? "Filter covered warrants by score, signal, gearing, delta, and theta."
              : "Bảng lọc chứng quyền theo điểm số, tín hiệu, gearing, delta và theta."
          }
          onClick={() => setPage("cw")}
        />
        <FeatureCard
          title={isEnglish ? "Credit health" : "Sức khỏe tín dụng"}
          text={
            isEnglish
              ? "Enter a ticker to view Altman Z-score, risk zone, and financial ratios."
              : "Nhập mã cổ phiếu để xem Altman Z-score, vùng rủi ro và tỷ lệ tài chính."
          }
          onClick={() => setPage("credit")}
        />
      </div>
    </section>
  );
}

function SignalCard({ signal, featured = false, isEnglish = false, onClick }) {
  if (!signal) return null;

  const statusLabel = signal.status === "BUY"
    ? (isEnglish ? "BUY" : "MUA")
    : signal.status === "WATCH"
      ? (isEnglish ? "WATCH" : "XEM XÉT")
      : signal.status === "SKIP"
        ? (isEnglish ? "SKIP" : "BỎ QUA")
        : (isEnglish ? "NEUTRAL" : "TRUNG TÍNH");

  return (
    <button
      type="button"
      className={`brief-item signal-card ${featured ? "signal-card-featured" : ""} ${signal.status === "SKIP" ? "danger" : signal.status === "BUY" ? "success" : ""}`}
      onClick={onClick}
    >
      <div className="signal-card-top">
        <strong className="signal-card-ticker">{signal.warrant_symbol}</strong>
        <span className={`signal-card-status ${signal.status.toLowerCase()}`}>{statusLabel}</span>
      </div>
      <div className="signal-card-metrics">
        <div className="signal-card-metric">
          <span className="signal-card-metric-label">{isEnglish ? "Score" : "Điểm"}</span>
          <strong>{formatNumber(signal.score, 1)}</strong>
        </div>
        <div className="signal-card-metric">
          <span className="signal-card-metric-label">IV</span>
          <strong>{formatNumber(signal.iv, 1)}%</strong>
        </div>
        <div className="signal-card-metric">
          <span className="signal-card-metric-label">HV</span>
          <strong>{formatNumber(signal.hv, 1)}%</strong>
        </div>
        <div className="signal-card-metric">
          <span className="signal-card-metric-label">{isEnglish ? "Underlying" : "Cơ sở"}</span>
          <strong>{signal.underlying_symbol || "-"}</strong>
        </div>
      </div>
    </button>
  );
}

function HeroMetric({ icon, label, value }) {
  return (
    <div className="hero-metric">
      <span>{icon}</span>
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function FeatureCard({ title, text, onClick }) {
  return (
    <article className="feature-card actionable-card" onClick={onClick}>
      <h3>{title}</h3>
      <p>{text}</p>
    </article>
  );
}
