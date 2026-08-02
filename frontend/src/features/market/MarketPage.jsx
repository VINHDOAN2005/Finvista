import React, { useEffect, useMemo, useState } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  Building2,
  ExternalLink,
  Newspaper,
  RefreshCw,
  Search,
  Waves
} from "lucide-react";

import { getMarketMetadata, getOpportunities, getUnderlyingMarket } from "../../api.js";
import { CwMarketMovement } from "../../components/market/CwMarketMovement.jsx";
import { Button } from "../../components/ui/button.jsx";
import { CursorTooltip, useCursorTooltip } from "../../components/ui/cursor-tooltip.jsx";
import { ErrorBox, LoadingBox } from "../../components/ui/status.jsx";
import { formatMoney, formatNumber } from "../../lib/formatters.js";
import { useDragScroll } from "../../lib/useDragScroll.js";


const COPY = {
  en: {
    eyebrow: "CW and stock intelligence",
    title: "Market Overview",
    intro: "Prices, sector movement, CW activity, and company news for stocks that currently have active covered warrants.",
    load: "Reload cache",
    live: "Refresh live",
    stocks: "Underlying stocks",
    sectors: "Sectors",
    cwValue: "CW traded value",
    activeCw: "Active CW",
    breadth: "Market breadth",
    advancing: "Advancing",
    declining: "Declining",
    unchanged: "Unchanged",
    sectorMap: "Sector flow map",
    sectorMapHelp: "Hover for flow details. Click a sector to filter the tables.",
    sectorTable: "Sector pulse",
    sector: "Sector",
    movement: "Movement",
    stockValue: "Stock traded value",
    allocation: "Breadth allocation",
    allSectors: "All sectors",
    stockTable: "CW-linked stock board",
    stock: "Stock",
    company: "Company",
    price: "Price",
    change: "Change",
    volume: "Volume",
    cwCount: "CW count",
    signalMix: "Signal mix",
    topCw: "Top CW",
    search: "Search symbol or company",
    searchHint: "Ticker suggestions",
    valueSort: "CW value",
    gainers: "Gainers",
    losers: "Losers",
    companyNews: "Company news",
    newsHelp: "News comes from vnstock when the public provider is available.",
    noNews: "No English company news is available in cache. Use Refresh live to request the English public feed.",
    noRows: "No underlying stocks match the current filter.",
    openCw: "Open CW detail",
    source: "Sources",
    newsCoverage: "News coverage",
    cache: "Cache",
    loading: "Loading the market overview...",
    routeMissing: "The running backend has not loaded the new underlying-market route. Close the old backend terminal and run Start_Finvista_API_Auth.bat again.",
    liveWarning: "The public source was partly unavailable. Cached and Finvista scan data are still shown.",
    autoRefresh: "Auto-refresh (5m)"
  },
  vi: {
    eyebrow: "Thị trường cổ phiếu có CW",
    title: "Tổng quan thị trường",
    intro: "Giá, biến động ngành, hoạt động CW và tin doanh nghiệp của các cổ phiếu hiện đang có chứng quyền.",
    load: "Tải lại cache",
    live: "Làm mới live",
    stocks: "Mã cơ sở",
    sectors: "Nhóm ngành",
    cwValue: "GTGD CW",
    activeCw: "CW đang hoạt động",
    breadth: "Độ rộng thị trường",
    advancing: "Tăng",
    declining: "Giảm",
    unchanged: "Không đổi",
    sectorMap: "Bản đồ dòng tiền ngành",
    sectorMapHelp: "Rê chuột để xem dòng tiền. Bấm một ngành để lọc các bảng.",
    sectorTable: "Nhịp ngành",
    sector: "Ngành",
    movement: "Biến động",
    stockValue: "GTGD cổ phiếu",
    allocation: "Phân bổ độ rộng",
    allSectors: "Tất cả ngành",
    stockTable: "Bảng giá cổ phiếu có CW",
    stock: "Mã CK",
    company: "Doanh nghiệp",
    price: "Giá",
    change: "Thay đổi",
    volume: "Khối lượng",
    cwCount: "Số CW",
    signalMix: "Tín hiệu CW",
    topCw: "CW nổi bật",
    search: "Tìm mã hoặc doanh nghiệp",
    searchHint: "Gợi ý mã chứng khoán",
    valueSort: "GTGD CW",
    gainers: "Tăng giá",
    losers: "Giảm giá",
    companyNews: "Tin doanh nghiệp",
    newsHelp: "Tin được lấy qua vnstock khi nguồn công khai hoạt động.",
    noNews: "Chưa có tin doanh nghiệp trong cache. Bấm Làm mới live để gọi nguồn công khai.",
    noRows: "Không có mã cơ sở phù hợp với bộ lọc hiện tại.",
    openCw: "Mở chi tiết CW",
    source: "Nguồn",
    newsCoverage: "Độ phủ tin",
    cache: "Cache",
    loading: "Đang tải tổng quan thị trường...",
    routeMissing: "Backend đang chạy chưa nạp route tổng quan thị trường mới. Hãy đóng terminal backend cũ rồi chạy lại Start_Finvista_API_Auth.bat.",
    liveWarning: "Nguồn công khai đang lỗi một phần. Trang vẫn hiển thị cache và dữ liệu quét Finvista.",
    autoRefresh: "Tự động làm mới (5p)"
  }
};

const ENGLISH_INDUSTRIES = {
  "Ngân hàng": "Banking",
  "Bất động sản": "Real estate",
  "Bán lẻ": "Retail",
  "Vật liệu xây dựng": "Construction materials",
  "Công nghệ và thông tin": "Technology & information",
  "Công nghệ": "Technology",
  "Thực phẩm - Đồ uống": "Food & beverage",
  "Thực phẩm": "Food",
  "Vận tải - kho bãi": "Transportation & logistics",
  "Vận tải": "Transportation",
  "SX Nhựa - Hóa chất": "Plastics & chemicals",
  "Thép": "Steel",
  "Khác": "Others",
  "Unknown": "Unknown"
};


function compactNumber(value, language) {
  const amount = Number(value) || 0;
  const locale = language === "en" ? "en-US" : "vi-VN";
  if (Math.abs(amount) >= 1e12) {
    return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(amount / 1e12)} ${language === "en" ? "trillion" : "nghìn tỷ"}`;
  }
  if (Math.abs(amount) >= 1e9) {
    return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(amount / 1e9)} ${language === "en" ? "billion" : "tỷ"}`;
  }
  if (Math.abs(amount) >= 1e6) {
    return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(amount / 1e6)} ${language === "en" ? "million" : "triệu"}`;
  }
  return formatMoney(amount);
}

function compactVnd(value, language) {
  return `${compactNumber(value, language)} ${language === "en" ? "VND" : "đồng"}`;
}

function displayIndustry(industry, language) {
  if (language !== "en") return industry;
  return ENGLISH_INDUSTRIES[industry] || industry;
}

function displayCompany(row, language) {
  if (language !== "en") return row.company_name || row.symbol;
  return row.company_name_en || `${row.symbol} listed company`;
}

function normalizeSearch(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
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

function changeClass(value) {
  if (Number(value) > 0) return "profit";
  if (Number(value) < 0) return "loss";
  return "flat-value";
}

export function MarketPage({ setPage, setSelectedSymbol, language = "en" }) {
  const text = COPY[language] || COPY.en;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeSector, setActiveSector] = useState("");
  const [selectedStock, setSelectedStock] = useState("");
  const [query, setQuery] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [sortMode, setSortMode] = useState("value");
  const [cwPulse, setCwPulse] = useState(null);
  const [marketMeta, setMarketMeta] = useState(null);
  const [pulseLoading, setPulseLoading] = useState(false);
  const [pulseError, setPulseError] = useState("");
  const [activeMovement, setActiveMovement] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(false);
  const stockTableDrag = useDragScroll();

  async function loadMarket({ forceRefresh = false } = {}) {
    setLoading(true);
    setError("");
    try {
      setData(await getUnderlyingMarket({ forceRefresh, newsLimit: 30, language }));
    } catch (err) {
      setError(err.message === "Not Found" ? text.routeMissing : err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadCwPulse({ forceRefresh = false } = {}) {
    setPulseLoading(true);
    setPulseError("");
    try {
      const [opportunities, metadata] = await Promise.all([
        getOpportunities({
          strategy: "balanced",
          underlying: "",
          limit: 300,
          forceRefresh
        }),
        getMarketMetadata({ forceRefresh })
      ]);
      setCwPulse(opportunities);
      setMarketMeta(metadata);
    } catch (err) {
      setPulseError(err.message);
    } finally {
      setPulseLoading(false);
    }
  }

  useEffect(() => {
    loadMarket();
    loadCwPulse();
  }, [language]);

  useEffect(() => {
    if (!autoRefresh) return;

    // Trigger an immediate scan on activation
    loadMarket({ forceRefresh: true });
    loadCwPulse({ forceRefresh: true });

    const interval = setInterval(() => {
      loadMarket({ forceRefresh: true });
      loadCwPulse({ forceRefresh: true });
    }, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, [autoRefresh, language]);

  const underlyings = data?.underlyings || [];
  const sectors = data?.sectors || [];
  const filteredRows = useMemo(() => {
    const normalizedQuery = normalizeSearch(query);
    const tickerQuery =
      /^[a-z0-9]+$/.test(normalizedQuery) &&
      underlyings.some((row) => row.symbol.toLowerCase().startsWith(normalizedQuery));
    const rows = underlyings.filter((row) => {
      const sectorOk = !activeSector || row.industry === activeSector;
      const movementOk =
        !activeMovement ||
        (activeMovement === "advancing" && Number(row.change_pct) > 0) ||
        (activeMovement === "declining" && Number(row.change_pct) < 0) ||
        (activeMovement === "unchanged" && Number(row.change_pct) === 0);
      const queryOk =
        !normalizedQuery ||
        (tickerQuery
          ? row.symbol.toLowerCase().startsWith(normalizedQuery)
          : normalizeSearch(displayCompany(row, language)).includes(normalizedQuery));
      return sectorOk && movementOk && queryOk;
    });
    return [...rows].sort((a, b) => {
      if (sortMode === "gainers") return Number(b.change_pct) - Number(a.change_pct);
      if (sortMode === "losers") return Number(a.change_pct) - Number(b.change_pct);
      return Number(b.cw_traded_value) - Number(a.cw_traded_value);
    });
  }, [activeMovement, activeSector, language, query, sortMode, underlyings]);

  const symbolSuggestions = useMemo(() => {
    const normalizedQuery = query.trim().toUpperCase();
    if (!normalizedQuery || !/^[A-Z0-9]+$/.test(normalizedQuery)) return [];
    return underlyings
      .filter((row) => row.symbol.startsWith(normalizedQuery))
      .sort((a, b) => a.symbol.localeCompare(b.symbol))
      .slice(0, 8);
  }, [query, underlyings]);

  const selected = underlyings.find((item) => item.symbol === selectedStock);
  
  const allNews = useMemo(() => {
    if (!data?.underlyings) return [];
    const collected = [];
    data.underlyings.forEach((und) => {
      if (und.news && Array.isArray(und.news)) {
        und.news.forEach((n) => {
          collected.push(n);
        });
      }
    });
    const seen = new Set();
    const unique = [];
    collected.forEach((item) => {
      const titleKey = (item.title || "").trim();
      const urlKey = (item.url || item.link || "").trim();
      if (titleKey && !seen.has(titleKey) && (!urlKey || !seen.has(urlKey))) {
        seen.add(titleKey);
        if (urlKey) seen.add(urlKey);
        unique.push(item);
      }
    });
    return unique.sort((a, b) => new Date(b.published_at || b.date) - new Date(a.published_at || a.date));
  }, [data]);

  const news = [...allNews].filter((item) => {
    if (activeSector) {
      const sectorSymbols = new Set(
        underlyings.filter((row) => row.industry === activeSector).map((row) => row.symbol)
      );
      return sectorSymbols.has(item.symbol);
    }
    return true;
  }).sort((a, b) => Number(b.symbol === selectedStock) - Number(a.symbol === selectedStock));
  const totalCwValue = underlyings.reduce((sum, row) => sum + Number(row.cw_traded_value || 0), 0);
  const activeCw = underlyings.reduce((sum, row) => sum + Number(row.cw_count || 0), 0);

  function chooseSector(industry) {
    setActiveSector((current) => (current === industry ? "" : industry));
    setSelectedStock("");
  }

  function openBestWarrant(row = selected) {
    if (!row?.best_warrant_symbol) return;
    setSelectedSymbol(row.best_warrant_symbol);
    setPage("detail");
  }

  function openWarrantDetail(symbol) {
    if (!symbol) return;
    setSelectedSymbol(symbol.trim().toUpperCase());
    setPage("detail");
  }

  return (
    <section className="page-section underlying-market-page">
      <div className="section-heading market-page-heading">
        <div>
          <p className="eyebrow">{text.eyebrow}</p>
          <h2>{text.title}</h2>
          <p className="market-page-intro">{text.intro}</p>
        </div>
        <div className="section-actions">
          <label className="auto-refresh-container">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={() => setAutoRefresh(!autoRefresh)}
              style={{ display: "none" }}
            />
            <div className={`auto-refresh-toggle ${autoRefresh ? "active" : ""}`}>
              <div className="auto-refresh-dot" />
            </div>
            <span className="auto-refresh-label">{text.autoRefresh}</span>
          </label>
          <Button variant="secondary" onClick={() => loadMarket()}>
            <RefreshCw size={16} />
            {text.load}
          </Button>
          <Button onClick={() => loadMarket({ forceRefresh: true })}>
            <Waves size={16} />
            {text.live}
          </Button>
        </div>
      </div>

      {error ? <ErrorBox message={error} language={language} /> : null}
      {loading ? <LoadingBox message={text.loading} /> : null}
      {data?.live_errors?.length ? <div className="notice info">{text.liveWarning}</div> : null}

      {pulseError ? <ErrorBox message={pulseError} language={language} /> : null}
      <CwMarketMovement
        rows={cwPulse?.recommendations || []}
        marketMeta={marketMeta}
        isEnglish={language === "en"}
        loading={pulseLoading}
        onOpenDetail={openWarrantDetail}
        onRefresh={() => loadCwPulse({ forceRefresh: true })}
      />

      {data ? (
        <>
      <div className="market-content-grid">
        <article className="market-workbench-card stock-board-card">
          <CardHeading title={text.stockTable} help={activeSector ? displayIndustry(activeSector, language) : text.allSectors} />
          <div className="market-board-tools">
            <label className="market-search">
              <Search size={16} />
              <input
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setShowSuggestions(true);
                }}
                onFocus={() => setShowSuggestions(true)}
                onBlur={() => setShowSuggestions(false)}
                placeholder={text.search}
              />
              {showSuggestions && symbolSuggestions.length ? (
                <div className="market-search-suggestions" aria-label={text.searchHint}>
                  {symbolSuggestions.map((row) => (
                    <button
                      type="button"
                      key={row.symbol}
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => {
                        setQuery(row.symbol);
                        setSelectedStock(row.symbol);
                        setShowSuggestions(false);
                      }}
                    >
                      <strong>{row.symbol}</strong>
                      <span>{displayCompany(row, language)}</span>
                    </button>
                  ))}
                </div>
              ) : null}
            </label>
            <div className="market-sort-tabs">
              {[
                ["value", text.valueSort],
                ["gainers", text.gainers],
                ["losers", text.losers]
              ].map(([id, label]) => (
                <button
                  type="button"
                  key={id}
                  className={sortMode === id ? "active" : ""}
                  onClick={() => setSortMode(id)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div ref={stockTableDrag.ref} className="market-table-scroll stock-table-scroll draggable-table" {...stockTableDrag.dragProps}>
            <table className="market-stock-table">
              <thead>
                <tr>
                  <th>{text.stock}</th>
                  <th>{text.company}</th>
                  <th>{text.price}</th>
                  <th>{text.change}</th>
                  <th>{text.volume}</th>
                  <th>{text.cwCount}</th>
                  <th>{text.signalMix}</th>
                  <th>{text.topCw}</th>
                </tr>
              </thead>
              <tbody>
                {!filteredRows.length ? (
                  <tr><td colSpan="8" className="empty-cell">{text.noRows}</td></tr>
                ) : null}
                {filteredRows.map((row) => (
                  <tr
                    key={row.symbol}
                    className={selectedStock === row.symbol ? "selected-row" : ""}
                    onClick={() => stockTableDrag.clickAllowed() && setSelectedStock((current) => current === row.symbol ? "" : row.symbol)}
                    onDoubleClick={() => openBestWarrant(row)}
                  >
                    <td className={`strong-cell market-state-label ${changeClass(row.change_pct)}`}>{row.symbol}</td>
                    <td><TooltipText text={displayCompany(row, language)} /></td>
                    <td>{formatMoney(row.price)}đ</td>
                    <td className={changeClass(row.change_pct)}>
                      {Number(row.change_pct) > 0 ? "+" : ""}{formatNumber(row.change_pct, 2)}%
                    </td>
                    <td>{row.stock_volume ? compactNumber(row.stock_volume, language) : "-"}</td>
                    <td>{row.cw_count}</td>
                    <td><SignalMix row={row} /></td>
                    <td>{row.best_warrant_symbol || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {selected ? (
            <div className="selected-stock-action">
              <span><strong>{selected.symbol}</strong> · {displayCompany(selected, language)}</span>
              <Button size="sm" variant="secondary" onClick={() => openBestWarrant()}>
                {text.openCw}
              </Button>
            </div>
          ) : null}
        </article>

        <article className="market-workbench-card news-board-card">
          <CardHeading title={text.companyNews} help={text.newsHelp} icon={<Newspaper size={17} />} />
          <div className="news-list">
            {!news.length ? <div className="market-empty-state">{text.noNews}</div> : null}
            {news.map((item, index) => (
              <article className={`news-item ${selectedStock === item.symbol ? "related" : ""}`} key={`${item.symbol}-${item.published_at}-${index}`}>
                <div className="news-meta">
                  <button
                    type="button"
                    onClick={() => setSelectedStock((current) => current === item.symbol ? "" : item.symbol)}
                  >
                    {item.symbol}
                  </button>
                  <span>{item.source || "vnstock"}</span>
                  <time>{formatNewsDate(item.published_at, language)}</time>
                </div>
                {item.url ? (
                  <h3><a className="news-title-link" href={item.url} target="_blank" rel="noreferrer">{item.title}</a></h3>
                ) : <h3>{item.title}</h3>}
                {item.summary ? <p>{item.summary}</p> : null}
                {item.url?.startsWith("http") ? (
                  <a href={item.url} target="_blank" rel="noreferrer">
                    {language === "en" ? "Open source" : "Mở nguồn"} <ExternalLink size={13} />
                  </a>
                ) : null}
              </article>
            ))}
          </div>
        </article>
      </div>

      <div className="market-source-line">
        <span>{text.source}: {data?.data_sources?.quotes || "-"} · {data?.data_sources?.news || "-"}</span>
        <span>
          {text.newsCoverage}: {data?.news_coverage?.symbols_with_news || 0}/{data?.news_coverage?.active_symbols || data?.underlying_count || 0}
          {" · "}{text.cache}: {formatNewsDate(data?.cache_updated_at, language)}
        </span>
      </div>
        </>
      ) : null}
    </section>
  );
}


function MarketKpi({ icon, label, value }) {
  return (
    <article className="market-kpi">
      <span>{icon}</span>
      <div><small>{label}</small><strong>{value}</strong></div>
    </article>
  );
}


function CardHeading({ title, help, icon = null }) {
  return (
    <div className="market-card-heading">
      <div>{icon}<strong>{title}</strong></div>
      <small>{help}</small>
    </div>
  );
}


function BreadthChart({ breadth, text, activeMovement, onChoose }) {
  const { tooltip, showTooltip, hideTooltip } = useCursorTooltip();
  const items = [
    { key: "advancing", label: text.advancing, value: Number(breadth.advancing) || 0, color: "#008b7a" },
    { key: "unchanged", label: text.unchanged, value: Number(breadth.unchanged) || 0, color: "#c9952f" },
    { key: "declining", label: text.declining, value: Number(breadth.declining) || 0, color: "#d94a6f" }
  ];
  const total = Math.max(items.reduce((sum, item) => sum + item.value, 0), 1);
  let offset = 0;
  return (
    <div className="market-breadth-chart">
      <div className="market-donut-wrap">
        <svg viewBox="0 0 42 42" role="img" aria-label={text.breadth}>
          <circle cx="21" cy="21" r="15.9" fill="none" stroke="#f1e8d9" strokeWidth="7" />
          {items.map((item) => {
            const pct = (item.value / total) * 100;
            const node = (
              <circle
                key={item.key}
                className="market-donut-segment"
                cx="21" cy="21" r="15.9" fill="none"
                stroke={item.color}
                strokeWidth="7"
                strokeDasharray={`${pct} ${100 - pct}`}
                strokeDashoffset={-offset}
                onClick={() => onChoose(item.key)}
                onPointerEnter={(event) => showTooltip(event, {
                  title: item.label,
                  detail: `${item.value} · ${formatNumber(pct, 1)}%`
                })}
                onPointerMove={(event) => showTooltip(event, {
                  title: item.label,
                  detail: `${item.value} · ${formatNumber(pct, 1)}%`
                })}
                onPointerLeave={hideTooltip}
                data-active={activeMovement === item.key}
              />
            );
            offset += pct;
            return node;
          })}
        </svg>
        <strong>{total}</strong>
      </div>
      <div className="market-breadth-legend">
        {items.map((item) => (
          <button
            type="button"
            key={item.key}
            className={activeMovement === item.key ? "active" : ""}
            onClick={() => onChoose(item.key)}
          >
            <i style={{ background: item.color }} />
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </button>
        ))}
      </div>
      <CursorTooltip tooltip={tooltip} />
    </div>
  );
}


function SectorMap({ sectors, activeSector, onChoose, language }) {
  const { tooltip, showTooltip, hideTooltip } = useCursorTooltip();
  const maxFlow = Math.max(...sectors.map((item) => Number(item.cw_traded_value) || 0), 1);
  if (!sectors.length) return <div className="market-empty-state">-</div>;
  return (
    <div className="sector-flow-map">
      {sectors.map((sector) => (
        <button
          type="button"
          key={sector.industry}
          className={`${changeClass(sector.average_change_pct)} ${activeSector === sector.industry ? "active" : ""}`}
          style={{ flexBasis: `${Math.max(24, (Number(sector.cw_traded_value) / maxFlow) * 58)}%` }}
          aria-label={`${displayIndustry(sector.industry, language)}: ${formatNumber(sector.average_change_pct, 2)}%, ${compactVnd(sector.cw_traded_value, language)} CW`}
          onPointerEnter={(event) => showTooltip(event, {
            title: displayIndustry(sector.industry, language),
            detail: `${formatNumber(sector.average_change_pct, 2)}% · ${compactVnd(sector.cw_traded_value, language)} CW`
          })}
          onPointerMove={(event) => showTooltip(event, {
            title: displayIndustry(sector.industry, language),
            detail: `${formatNumber(sector.average_change_pct, 2)}% · ${compactVnd(sector.cw_traded_value, language)} CW`
          })}
          onPointerLeave={hideTooltip}
          onClick={() => onChoose(sector.industry)}
        >
          <strong>{displayIndustry(sector.industry, language)}</strong>
          <span>{Number(sector.average_change_pct) > 0 ? "+" : ""}{formatNumber(sector.average_change_pct, 2)}%</span>
          <small>{sector.underlying_count} CP · {compactVnd(sector.cw_traded_value, language)} CW</small>
        </button>
      ))}
      <CursorTooltip tooltip={tooltip} />
    </div>
  );
}


function BreadthBar({ up, down, flat }) {
  const { tooltip, showTooltip, hideTooltip } = useCursorTooltip();
  const total = Math.max(Number(up) + Number(down) + Number(flat), 1);
  return (
    <span
      className="breadth-allocation"
      aria-label={`+${up} / =${flat} / -${down}`}
      onPointerEnter={(event) => showTooltip(event, {
        title: "Breadth",
        detail: `+${up} / =${flat} / -${down}`
      })}
      onPointerMove={(event) => showTooltip(event, {
        title: "Breadth",
        detail: `+${up} / =${flat} / -${down}`
      })}
      onPointerLeave={hideTooltip}
    >
      <i className="up" style={{ width: `${(Number(up) / total) * 100}%` }} />
      <i className="flat" style={{ width: `${(Number(flat) / total) * 100}%` }} />
      <i className="down" style={{ width: `${(Number(down) / total) * 100}%` }} />
      <CursorTooltip tooltip={tooltip} />
    </span>
  );
}


function SignalMix({ row }) {
  const { tooltip, showTooltip, hideTooltip } = useCursorTooltip();
  const total = Math.max(Number(row.cw_count), 1);
  return (
    <span
      className="signal-mix"
      aria-label={`BUY ${row.buy_count} · NEUTRAL ${row.neutral_count} · SKIP ${row.skip_count}`}
      onPointerEnter={(event) => showTooltip(event, {
        title: "Signal mix",
        detail: `BUY ${row.buy_count} · NEUTRAL ${row.neutral_count} · SKIP ${row.skip_count}`
      })}
      onPointerMove={(event) => showTooltip(event, {
        title: "Signal mix",
        detail: `BUY ${row.buy_count} · NEUTRAL ${row.neutral_count} · SKIP ${row.skip_count}`
      })}
      onPointerLeave={hideTooltip}
    >
      <i className="buy" style={{ width: `${(Number(row.buy_count) / total) * 100}%` }} />
      <i className="neutral" style={{ width: `${(Number(row.neutral_count) / total) * 100}%` }} />
      <i className="skip" style={{ width: `${(Number(row.skip_count) / total) * 100}%` }} />
      <CursorTooltip tooltip={tooltip} />
    </span>
  );
}


function TooltipText({ text }) {
  const { tooltip, showTooltip, hideTooltip } = useCursorTooltip();
  return (
    <span
      className="tooltip-text"
      onPointerEnter={(event) => showTooltip(event, { title: text })}
      onPointerMove={(event) => showTooltip(event, { title: text })}
      onPointerLeave={hideTooltip}
    >
      {text}
      <CursorTooltip tooltip={tooltip} />
    </span>
  );
}


function formatNewsDate(value, language) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(language === "en" ? "en-GB" : "vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  }).format(date);
}
