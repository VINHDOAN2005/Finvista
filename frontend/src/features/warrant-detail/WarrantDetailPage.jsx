import React, { useEffect, useState } from "react";
import { RefreshCw, Search, Zap } from "lucide-react";

import { getWarrantHistory, getWarrantSimulation, refreshMarketScan } from "../../api.js";
import { DEFAULT_PREFERENCES } from "../../app/config.js";
import { CandlestickChart, InteractiveLineChart } from "../../components/charts/WarrantCharts.jsx";
import { Button } from "../../components/ui/button.jsx";
import { Input } from "../../components/ui/input.jsx";
import { ErrorBox, LoadingBox, MetricCard } from "../../components/ui/status.jsx";
import { formatMoney, formatNumber } from "../../lib/formatters.js";
import { useDragScroll } from "../../lib/useDragScroll.js";

function getHeatmapBgColor(p_l_pct) {
  const val = Math.max(-100, Math.min(100, p_l_pct));
  if (val >= 0) {
    const opacity = 0.08 + (val / 100) * 0.72; 
    return `rgba(46, 196, 182, ${opacity})`;
  } else {
    const opacity = 0.08 + (Math.abs(val) / 100) * 0.72;
    return `rgba(230, 57, 70, ${opacity})`;
  }
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

export function WarrantDetailPage({
  selectedSymbol,
  setSelectedSymbol,
  language = "vi",
  preferences = DEFAULT_PREFERENCES
}) {
  const isEnglish = language === "en";
  const [symbol, setSymbol] = useState(selectedSymbol || "CACB2510");
  const [simulation, setSimulation] = useState(null);
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshingMarket, setRefreshingMarket] = useState(false);
  const [error, setError] = useState("");
  const scenarioTableDrag = useDragScroll();
  const historyTableDrag = useDragScroll();

  useEffect(() => {
    if (selectedSymbol) setSymbol(selectedSymbol);
  }, [selectedSymbol]);

  async function loadDetail(target = symbol) {
    if (!target.trim()) return;
    setLoading(true);
    setError("");
    setSelectedSymbol(target.trim().toUpperCase());
    try {
      const [sim, hist] = await Promise.all([
        getWarrantSimulation(target),
        getWarrantHistory(target, 500)
      ]);
      setSimulation(sim);
      setHistory(hist);
    } catch (err) {
      setError(err.message);
      setSimulation(null);
      setHistory(null);
    } finally {
      setLoading(false);
    }
  }

  async function refreshLiveDetail() {
    if (!symbol.trim()) return;
    setRefreshingMarket(true);
    setError("");
    try {
      await refreshMarketScan("balanced");
      await loadDetail(symbol);
    } catch (err) {
      setError(err.message);
    } finally {
      setRefreshingMarket(false);
    }
  }

  useEffect(() => {
    if (selectedSymbol) {
      loadDetail(selectedSymbol);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSymbol]);

  const firstScenario = simulation?.scenarios?.[0]?.matrix || [];
  const historyRows = history?.history || [];
  const latestHistoryRows = historyRows.slice(-8).reverse();
  const candleRows = historyRows
    .map((row) => ({
      date: row.date,
      open: row.warrant_ohlc?.open,
      high: row.warrant_ohlc?.high,
      low: row.warrant_ohlc?.low,
      close: row.warrant_ohlc?.close,
      volume: row.warrant_ohlc?.volume || 0
    }))
    .filter((row) => [row.open, row.high, row.low, row.close].every((value) => Number.isFinite(Number(value))));
  function rawPricePoints(accessor) {
    return historyRows.map((row) => ({
      date: row.date,
      value: accessor(row)
    }));
  }
  const marketTrendChartSeries = [
    {
      key: "cw",
      label: isEnglish ? "CW price" : "Giá CW",
      color: "#b34a7d",
      valueSuffix: " VND",
      scaleMode: "relative-visible",
      points: rawPricePoints((row) => row.warrant_price)
    },
    {
      key: "underlying",
      label: isEnglish ? "Underlying price" : "Giá mã cơ sở",
      color: "#5a9bd2",
      valueSuffix: " VND",
      scaleMode: "relative-visible",
      points: rawPricePoints((row) => row.underlying_price)
    }
  ];
  const valuationChartSeries = [
    {
      key: "market",
      label: isEnglish ? "Market CW" : "Giá CW thực tế",
      color: "#b34a7d",
      points: historyRows.map((row) => ({
        date: row.date,
        value: row.warrant_price
      }))
    },
    {
      key: "theoretical",
      label: isEnglish ? "BSM-HV fair value" : "Giá lý thuyết BSM-HV",
      color: "#3f88c5",
      points: historyRows.map((row) => ({
        date: row.date,
        value: row.theoretical_price ?? row.warrant_price
      }))
    }
  ];
  const volatilityChartSeries = [
    {
      key: "iv",
      label: "IV",
      color: "#8b5fbf",
      points: historyRows.map((row) => ({
        date: row.date,
        value: row.implied_volatility_pct
      }))
    },
    {
      key: "hv",
      label: "HV",
      color: "#b87500",
      points: historyRows.map((row) => ({
        date: row.date,
        value: row.historical_volatility_pct
      }))
    }
  ];

  return (
    <section className="page-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{isEnglish ? "Scenario simulation" : "Mô phỏng kịch bản"}</p>
          <h2>{isEnglish ? "CW Detail" : "Chi tiết CW"}</h2>
        </div>
      </div>

      <div className="search-row">
        <Input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          onKeyDown={(e) => e.key === "Enter" && loadDetail()}
          placeholder={isEnglish ? "Enter CW code: CACB2510..." : "Nhập mã CW: CACB2510..."}
        />
        <Button className="detail-refresh-button" variant="secondary" onClick={refreshLiveDetail} disabled={refreshingMarket}>
          {refreshingMarket ? <Zap size={16} /> : <RefreshCw size={16} />}
          {refreshingMarket ? (isEnglish ? "Scanning..." : "Đang quét...") : (isEnglish ? "Refresh live" : "Làm mới thị trường")}
        </Button>
        <Button className="detail-load-button" onClick={() => loadDetail()}>
          <Search size={16} />
          {isEnglish ? "Load detail" : "Tải chi tiết"}
        </Button>
      </div>

      {error ? <ErrorBox message={error} language={language} /> : null}
      {loading ? <LoadingBox message={isEnglish ? "Loading simulation and history..." : "Đang tải mô phỏng và lịch sử..."} /> : null}

      {simulation ? (
        <>
          <KpiGroup
            title={isEnglish ? "Instrument and liquidity" : "Mã và thanh khoản"}
            description={isEnglish ? "Identify the warrant, its underlying stock, and whether there is enough trading activity." : "Xác định mã CW, cổ phiếu cơ sở và mức độ giao dịch."}
          >
            <div className="detail-summary">
              <MetricCard label={isEnglish ? "CW code" : "Mã CW"} value={simulation.symbol} detail={simulation.underlying_symbol} />
              <MetricCard label={isEnglish ? "Current price" : "Giá hiện tại"} value={`${formatMoney(simulation.current_price)}đ`} />
              <MetricCard label={isEnglish ? "Underlying price" : "Giá CPCS"} value={`${formatMoney(simulation.underlying_current_price)}đ`} />
              <MetricCard label="Volume" value={formatMoney(simulation.volume)} />
            </div>
          </KpiGroup>

          <KpiGroup
            title={isEnglish ? "Valuation setup" : "Thiết lập định giá"}
            description={isEnglish ? "Strike, premium, and leverage show whether the entry is expensive or aggressive." : "Giá thực hiện, premium và đòn bẩy cho biết điểm vào đắt hay mạo hiểm."}
          >
            <div className="detail-summary">
              <MetricCard label={isEnglish ? "Strike price" : "Giá thực hiện"} value={`${formatMoney(simulation.strike_price)}đ`} />
              <MetricCard label="Premium" value={`${formatNumber(simulation.premium_pct, 2)}%`} />
              <MetricCard label="Gearing" value={`${formatNumber(simulation.effective_gearing, 2)}x`} />
              <MetricCard label={isEnglish ? "Days left" : "Còn lại"} value={`${simulation.days_to_maturity} ${isEnglish ? "days" : "ngày"}`} />
            </div>
          </KpiGroup>

          <KpiGroup
            title={isEnglish ? "Greeks and volatility" : "Greeks và biến động"}
            description={isEnglish ? "Delta, theta, IV, and HV help judge sensitivity and time decay." : "Delta, theta, IV và HV giúp đọc độ nhạy và hao mòn thời gian."}
          >
            <div className="detail-summary">
              <MetricCard label="Delta" value={formatNumber(simulation.delta, 4)} />
              <MetricCard label="Theta/day" value={`${formatNumber(simulation.theta_daily_burn, 0)}đ`} />
              <MetricCard label="IV" value={`${formatNumber(simulation.implied_volatility_pct, 2)}%`} />
              <MetricCard label="HV" value={`${formatNumber(history?.averages?.average_hv_pct, 2)}%`} />
            </div>
          </KpiGroup>
        </>
      ) : null}

      {historyRows.length ? (
        <div className="chart-grid">
          <CandlestickChart
            title={isEnglish ? "CW candlestick" : "Biểu đồ nến CW"}
            subtitle={simulation?.symbol || symbol}
            candles={candleRows}
            language={language}
            valueSuffix=" VND"
            className="wide"
          />
          <InteractiveLineChart
            title={isEnglish ? "CW / underlying trend" : "Xu hướng CW và CPCS"}
            subtitle={`${simulation?.symbol || symbol} / ${simulation?.underlying_symbol || ""}`}
            series={marketTrendChartSeries}
            language={language}
            chartPreferences={preferences}
            valueSuffix="%"
          />
          <InteractiveLineChart
            title={isEnglish ? "Market vs fair CW price" : "Giá thực tế vs lý thuyết CW"}
            subtitle={isEnglish ? "BSM fair value using HV" : "BSM fair value dùng HV"}
            series={valuationChartSeries}
            language={language}
            chartPreferences={preferences}
            valueSuffix=" VND"
          />
          <InteractiveLineChart
            title={isEnglish ? "IV / HV volatility" : "Biến động IV / HV"}
            subtitle={isEnglish ? "Implied vs historical volatility" : "Implied volatility và historical volatility"}
            series={volatilityChartSeries}
            language={language}
            chartPreferences={preferences}
            valueSuffix="%"
            className="wide"
          />
        </div>
      ) : null}

      {firstScenario.length ? (
        <div className="split-grid">
          <div>
            <h3>{isEnglish ? "2D P/L Scenario Heatmap" : "Bản đồ nhiệt kịch bản P/L 2D"}</h3>
            <div ref={scenarioTableDrag.ref} className="table-wrap compact draggable-table" {...scenarioTableDrag.dragProps}>
              <table>
                <thead>
                  <tr>
                    <th>{isEnglish ? "Holding / Change" : "Nắm giữ / Biến động"}</th>
                    {simulation.scenarios[0]?.matrix.map((col) => (
                      <th key={col.change_pct} className="align-center">
                        {col.change_pct > 0 ? "+" : ""}{col.change_pct}%
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {simulation.scenarios.map((scenario) => (
                    <tr key={scenario.holding_days}>
                      <td className="strong-cell">
                        {scenario.holding_days} {isEnglish ? "days" : "ngày"}
                        <span style={{ display: "block", fontSize: "0.7rem", opacity: 0.6 }}>
                          (T+{scenario.holding_days})
                        </span>
                      </td>
                      {scenario.matrix.map((cell) => {
                        const bg = getHeatmapBgColor(cell.p_l_pct);
                        return (
                          <td
                            key={cell.change_pct}
                            className="align-center"
                            style={{
                              background: bg,
                              color: "var(--text-main, #ffffff)",
                              fontWeight: "600",
                              transition: "all 0.2s"
                            }}
                            title={`${isEnglish ? "Theoretical price" : "Giá lý thuyết"}: ${formatMoney(cell.theoretical_price)}đ`}
                          >
                            {cell.p_l_pct >= 0 ? "+" : ""}{formatNumber(cell.p_l_pct, 1)}%
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <h3>{isEnglish ? "IV/HV history" : "Lịch sử IV/HV"}</h3>
            <div ref={historyTableDrag.ref} className="table-wrap compact draggable-table" {...historyTableDrag.dragProps}>
              <table>
                <thead>
                  <tr>
                    <th>{isEnglish ? "Date" : "Ngày"}</th>
                    <th>{isEnglish ? "CW price" : "Giá CW"}</th>
                    <th>{isEnglish ? "Underlying" : "Giá CPCS"}</th>
                    <th>Volume</th>
                    <th>{isEnglish ? "Fair value" : "Giá lý thuyết"}</th>
                    <th>GAP</th>
                    <th>IV</th>
                    <th>HV</th>
                  </tr>
                </thead>
                <tbody>
                  {latestHistoryRows.map((row) => (
                    <tr key={row.date}>
                      <td>{row.date}</td>
                      <td>{formatMoney(row.warrant_price)}đ</td>
                      <td>{formatMoney(row.underlying_price)}đ</td>
                      <td>{formatMoney(row.warrant_ohlc?.volume)}</td>
                      <td>{formatMoney(row.theoretical_price)}đ</td>
                      <td className={row.pricing_gap_pct >= 0 ? "profit" : "loss"}>
                        {formatNumber(row.pricing_gap_pct, 1)}%
                      </td>
                      <td>{formatNumber(row.implied_volatility_pct, 1)}%</td>
                      <td>{formatNumber(row.historical_volatility_pct, 1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
