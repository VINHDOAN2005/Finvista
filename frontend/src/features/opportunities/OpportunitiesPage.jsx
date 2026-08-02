import React, { useEffect, useRef, useState } from "react";
import { Bookmark, RefreshCw, Save, Search, Trash2 } from "lucide-react";

import { getMarketMetadata, getOpportunities } from "../../api.js";
import { useAuth } from "../../auth/AuthProvider.jsx";
import { STORAGE_KEYS, VN30_UNDERLYINGS } from "../../app/config.js";
import { Button } from "../../components/ui/button.jsx";
import { Input } from "../../components/ui/input.jsx";
import { ErrorBox, LoadingBox } from "../../components/ui/status.jsx";
import { formatMoney, formatNumber, formatSignal, signalClass } from "../../lib/formatters.js";

const ENGLISH_INDUSTRIES = {
  "Ngân hàng": "Banking",
  "Chứng khoán": "Securities",
  "Bảo hiểm": "Insurance",
  "Bất động sản": "Real estate",
  "Tiện ích": "Utilities",
  "Năng lượng": "Energy",
  "Thép": "Steel",
  "Cao su": "Rubber",
  "Hóa chất": "Chemicals",
  "Thực phẩm": "Food & Beverage",
  "Bán lẻ": "Retail",
  "Công nghệ": "Technology",
  "Vận tải": "Transportation",
  "Logistics": "Logistics",
  "Vật liệu xây dựng": "Construction materials",
  "Công nghệ và thông tin": "Technology & information",
  "Thực phẩm - Đồ uống": "Food & beverage",
  "Vận tải - kho bãi": "Transportation & logistics",
  "SX Nhựa - Hóa chất": "Plastics & chemicals",
  "Khác": "Others",
  "Unknown": "Unknown"
};

function displayIndustry(industry, language) {
  if (!industry) return "";
  if (language !== "en") return industry;
  return ENGLISH_INDUSTRIES[industry] || industry;
}

export function NumericStepperInput({
  value,
  onValueChange,
  min,
  max,
  step = 1,
  placeholder,
  onKeyDown,
  className = ""
}) {
  function emitValue(nextValue) {
    onValueChange?.(nextValue);
  }

  function handleChange(event) {
    emitValue(event.target.value);
  }

  function handleStep(delta) {
    if (value === "") {
      emitValue(String(delta > 0 ? step : -step));
      return;
    }

    const numericValue = Number(value);
    const nextValue = Number.isFinite(numericValue) ? numericValue + delta : delta;

    if (min !== undefined && nextValue < Number(min)) {
      emitValue(String(min));
      return;
    }

    if (max !== undefined && nextValue > Number(max)) {
      emitValue(String(max));
      return;
    }

    emitValue(String(nextValue));
  }

  return (
    <div className={`numeric-stepper ${className}`.trim()}>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={handleChange}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
      />
      <div className="numeric-stepper-buttons" aria-label="numeric stepper">
        <button type="button" className="numeric-stepper-button" aria-label="Increase" onClick={() => handleStep(Number(step))}>
          <i className="bi bi-chevron-up" aria-hidden="true" />
        </button>
        <button type="button" className="numeric-stepper-button" aria-label="Decrease" onClick={() => handleStep(-Number(step))}>
          <i className="bi bi-chevron-down" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}

export function OpportunitiesPage({ setPage, setSelectedSymbol, language = "vi" }) {
  const auth = useAuth();
  const isEnglish = language === "en";
  const [strategy, setStrategy] = useState("balanced");
  const [underlying, setUnderlying] = useState("");
  const [limit, setLimit] = useState(10);
  const [currentPage, setCurrentPage] = useState(1);
  const [maturityMax, setMaturityMax] = useState("");
  const [priceMax, setPriceMax] = useState("");
  const [gearMin, setGearMin] = useState("");
  const [deltaMin, setDeltaMin] = useState("");
  const [thetaMax, setThetaMax] = useState("");
  const [ivHvMax, setIvHvMax] = useState("");
  const [signalFilter, setSignalFilter] = useState("all");
  const [industryFilter, setIndustryFilter] = useState("");
  const [marketMeta, setMarketMeta] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pendingSymbol, setPendingSymbol] = useState("");
  const [presetName, setPresetName] = useState("");
  const [filterPresets, setFilterPresets] = useState([]);
  const [activePresetId, setActivePresetId] = useState("");
  const tableScrollRef = useRef(null);
  const tableDragRef = useRef(null);
  const suppressTableRowClickUntilRef = useRef(0);

  const [debouncedUnderlying, setDebouncedUnderlying] = useState(underlying);
  const [sortColumn, setSortColumn] = useState("composite_g_score");
  const [sortDirection, setSortDirection] = useState("desc");

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedUnderlying(underlying);
    }, 300);
    return () => clearTimeout(timer);
  }, [underlying]);

  function handleSort(column) {
    if (sortColumn === column) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(column);
      setSortDirection("desc");
    }
  }

  function getSortedRows(rows) {
    return [...rows].sort((a, b) => {
      let aVal = a[sortColumn];
      let bVal = b[sortColumn];
      
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      
      if (typeof aVal === "string") {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }
      
      if (sortDirection === "asc") {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });
  }

  async function loadOpportunities({ forceRefresh = false, underlyingOverride } = {}) {
    setLoading(true);
    setError("");
    try {
      const searchUnderlying = underlyingOverride !== undefined ? underlyingOverride : debouncedUnderlying;
      const [result, metadata] = await Promise.all([
        getOpportunities({
          strategy,
          underlying: searchUnderlying,
          limit: 1000, // Fetch up to 1000 elements for frontend pagination
          forceRefresh,
          industry: industryFilter
        }),
        getMarketMetadata({ forceRefresh })
      ]);
      setData(result);
      setMarketMeta(metadata);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadOpportunities({ underlyingOverride: debouncedUnderlying });
  }, [strategy, debouncedUnderlying, industryFilter]);

  useEffect(() => {
    setCurrentPage(1);
  }, [strategy, debouncedUnderlying, limit, industryFilter, maturityMax, priceMax, gearMin, deltaMin, thetaMax, ivHvMax, signalFilter]);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.filterPresets) || "[]");
      if (Array.isArray(saved)) setFilterPresets(saved);
    } catch {
      setFilterPresets([]);
    }
  }, []);

  function currentFilterConfig() {
    return {
      strategy,
      underlying,
      limit,
      maturityMax,
      priceMax,
      gearMin,
      deltaMin,
      thetaMax,
      ivHvMax,
      industryFilter,
      signalFilter
    };
  }

  function persistPresets(nextPresets) {
    setFilterPresets(nextPresets);
    localStorage.setItem(STORAGE_KEYS.filterPresets, JSON.stringify(nextPresets));
  }

  function saveFilterPreset() {
    const name = presetName.trim();
    if (!name) return;
    const nextPreset = {
      id: `${Date.now()}`,
      name,
      config: currentFilterConfig()
    };
    const nextPresets = [
      nextPreset,
      ...filterPresets.filter((preset) => preset.name.toLowerCase() !== name.toLowerCase())
    ].slice(0, 12);
    persistPresets(nextPresets);
    setPresetName("");
  }

  function setFilterConfig(config = {}) {
    setStrategy(config.strategy || "balanced");
    setUnderlying(config.underlying || "");
    setLimit(config.limit || 10);
    setMaturityMax(config.maturityMax || "");
    setPriceMax(config.priceMax || "");
    setGearMin(config.gearMin || "");
    setDeltaMin(config.deltaMin || "");
    setThetaMax(config.thetaMax || "");
    setIvHvMax(config.ivHvMax || "");
    setIndustryFilter(config.industryFilter || "");
    setSignalFilter(config.signalFilter || "all");
  }

  function clearFilterPreset() {
    setFilterConfig();
    setActivePresetId("");
  }

  function applyFilterPreset(preset) {
    if (activePresetId === preset.id) {
      clearFilterPreset();
      return;
    }
    const config = preset.config || {};
    setFilterConfig(config);
    setActivePresetId(preset.id);
  }

  function deleteFilterPreset(id) {
    persistPresets(filterPresets.filter((preset) => preset.id !== id));
    if (activePresetId === id) setActivePresetId("");
  }

  function handleOpportunitySectionClick(event) {
    if (!pendingSymbol) return;
    if (event.target.closest("tbody tr")) return;
    setPendingSymbol("");
  }

  const rows = data?.recommendations || [];
  const sortedRows = getSortedRows(rows);
  const availableIndustries = [
    ...new Set([
      ...(marketMeta?.industries || []),
      ...rows.map((row) => row.underlying_industry).filter(Boolean)
    ])
  ].sort((a, b) => a.localeCompare(b));
  const filteredRows = sortedRows.filter((row) => {
    const activeOk = Number(row.days_to_maturity) > 0;
    const maturityOk =
      !maturityMax || Number(row.days_to_maturity) <= Number(maturityMax);
    const priceOk = !priceMax || Number(row.market_price) <= Number(priceMax);
    const gearOk = !gearMin || Number(row.effective_gearing) >= Number(gearMin);
    const deltaOk = !deltaMin || Number(row.delta) >= Number(deltaMin);
    const thetaOk = !thetaMax || Math.abs(Number(row.theta_daily_burn)) <= Number(thetaMax);
    const ivHvSpread = Math.abs(Number(row.implied_volatility_pct) - Number(row.historical_volatility_pct));
    const ivHvOk = !ivHvMax || ivHvSpread <= Number(ivHvMax);
    const signal = row.recommendation_signal?.toUpperCase() || "";
    const signalOk =
      signalFilter === "all" ||
      (signalFilter === "strong_buy" && signal.includes("STRONG")) ||
      (signalFilter === "buy" && signal.includes("BUY") && !signal.includes("STRONG")) ||
      (signalFilter === "skip" && signal.includes("SKIP"));
    const industryOk =
      !industryFilter ||
      (row.underlying_industry || "Unknown").toLowerCase() === industryFilter.toLowerCase();

    return activeOk && maturityOk && priceOk && gearOk && deltaOk && thetaOk && ivHvOk && signalOk && industryOk;
  });

  const totalPages = Math.ceil(filteredRows.length / limit);
  const safeCurrentPage = Math.min(currentPage, Math.max(1, totalPages));
  const startIndex = (safeCurrentPage - 1) * limit;
  const endIndex = Math.min(startIndex + limit, filteredRows.length);
  const paginatedRows = filteredRows.slice(startIndex, endIndex);

  function handleFilterEnter(event) {
    if (event.key === "Enter") {
      loadOpportunities();
    }
  }

  function openDetail(symbol) {
    const normalized = symbol.trim().toUpperCase();
    setSelectedSymbol(normalized);
    setPage("detail");
  }

  function handleRowClick(symbol) {
    if (Date.now() < suppressTableRowClickUntilRef.current) {
      return;
    }
    const normalized = symbol.trim().toUpperCase();
    if (pendingSymbol === normalized) {
      openDetail(normalized);
      return;
    }
    setPendingSymbol(normalized);
  }

  function handleTablePointerDown(event) {
    if (event.button !== 0) return;
    if (event.target.closest("button, input, select, a")) return;
    const tableWrap = tableScrollRef.current;
    if (!tableWrap || tableWrap.scrollWidth <= tableWrap.clientWidth) return;
    tableDragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      scrollLeft: tableWrap.scrollLeft,
      moved: false,
      active: false
    };
  }

  function handleTablePointerMove(event) {
    const drag = tableDragRef.current;
    const tableWrap = tableScrollRef.current;
    if (!drag || !tableWrap || drag.pointerId !== event.pointerId) return;
    const deltaX = event.clientX - drag.startX;
    if (Math.abs(deltaX) > 12) {
      drag.moved = true;
      if (!drag.active) {
        drag.active = true;
        tableWrap.setPointerCapture?.(event.pointerId);
        tableWrap.classList.add("is-dragging");
      }
      event.preventDefault();
      tableWrap.scrollLeft = drag.scrollLeft - deltaX;
    }
  }

  function endTableDrag(event) {
    const drag = tableDragRef.current;
    const tableWrap = tableScrollRef.current;
    if (!drag || !tableWrap) return;
    tableWrap.releasePointerCapture?.(drag.pointerId || event.pointerId);
    tableWrap.classList.remove("is-dragging");
    if (drag.moved) {
      suppressTableRowClickUntilRef.current = Date.now() + 180;
    }
    tableDragRef.current = null;
  }

  return (
    <section className="page-section" onClick={handleOpportunitySectionClick}>
      <div className="section-heading">
        <div>
          <p className="eyebrow">{isEnglish ? "Covered warrants" : "Chứng quyền"}</p>
          <h2>{isEnglish ? "CW Opportunities" : "Cơ hội CW"}</h2>
        </div>
        <div className="section-actions">
          <Button onClick={() => loadOpportunities()}>
            <Search size={16} />
            {isEnglish ? "Load data" : "Tải dữ liệu"}
          </Button>
          <Button variant="secondary" onClick={() => loadOpportunities({ forceRefresh: true })}>
            <RefreshCw size={16} />
            {isEnglish ? "Refresh live" : "Quét thị trường"}
          </Button>
        </div>
      </div>

      <div className="filter-shell">
        <div className="filter-section filter-section-core">
          <div className="filter-section-header">
            <span>{isEnglish ? "Core filters" : "Bộ lọc cốt lõi"}</span>
          </div>
          <div className="filters">
            <label>
              <span className="filter-label">{isEnglish ? "Strategy" : "Chiến lược"}</span>
              <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
                <option value="balanced">{isEnglish ? "Balanced" : "Cân bằng"}</option>
                <option value="safe">{isEnglish ? "Safe" : "An toàn"}</option>
                <option value="aggressive">{isEnglish ? "Aggressive" : "Mạo hiểm"}</option>
              </select>
            </label>
            <label>
              <span className="filter-label">{isEnglish ? "Underlying" : "Mã cơ sở"}</span>
              <input
                value={underlying}
                onChange={(e) => setUnderlying(e.target.value.toUpperCase())}
                onKeyDown={handleFilterEnter}
                placeholder="HPG, FPT..."
              />
            </label>
            <label>
              <span className="filter-label">{isEnglish ? "Rows per page" : "Số dòng / trang"}</span>
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={55}>55</option>
                <option value={100}>100</option>
              </select>
            </label>
            <label>
              <span className="filter-label">{isEnglish ? "Signal" : "Tín hiệu"}</span>
              <select
                value={signalFilter}
                onChange={(e) => setSignalFilter(e.target.value)}
              >
                <option value="all">{isEnglish ? "All signals" : "Tất cả tín hiệu"}</option>
                <option value="strong_buy">STRONG BUY</option>
                <option value="buy">BUY</option>
                <option value="skip">SKIP</option>
              </select>
            </label>
            <label>
              <span className="filter-label">{isEnglish ? "Sector" : "Ngành / lĩnh vực"}</span>
              <select
                value={industryFilter}
                onChange={(e) => setIndustryFilter(e.target.value)}
              >
                <option value="">{isEnglish ? "All sectors" : "Tất cả ngành"}</option>
                {availableIndustries.map((industryName) => (
                  <option key={industryName} value={industryName}>
                    {displayIndustry(industryName, language)}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div className="filter-section filter-section-advanced">
          <div className="filter-section-header">
            <span>{isEnglish ? "Risk / Greeks thresholds" : "Ngưỡng rủi ro / Greeks"}</span>
            <span className="filter-section-subtitle">{isEnglish ? "Advanced filters" : "Bộ lọc nâng cao"}</span>
          </div>
          <div className="quick-filters" aria-label={isEnglish ? "Quick filters" : "Bộ lọc nhanh"}>
            <label>
              <span className="filter-label">{isEnglish ? "Maturity max" : "Đáo hạn tối đa"}</span>
              <NumericStepperInput
                min="1"
                value={maturityMax}
                onValueChange={(value) => setMaturityMax(value)}
                onKeyDown={handleFilterEnter}
                placeholder={isEnglish ? "Days" : "Ngày"}
              />
            </label>
            <label>
              <span className="filter-label">{isEnglish ? "Buy price max" : "Giá mua tối đa"}</span>
              <NumericStepperInput
                min="0"
                value={priceMax}
                onValueChange={(value) => setPriceMax(value)}
                onKeyDown={handleFilterEnter}
                placeholder="VD: 2500"
              />
            </label>
            <label>
              <span className="filter-label">Gear min</span>
              <NumericStepperInput
                min="0"
                step="0.1"
                value={gearMin}
                onValueChange={(value) => setGearMin(value)}
                onKeyDown={handleFilterEnter}
                placeholder="VD: 3"
              />
            </label>
            <label>
              <span className="filter-label">Delta min</span>
              <NumericStepperInput
                min="0"
                max="1"
                step="0.01"
                value={deltaMin}
                onValueChange={(value) => setDeltaMin(value)}
                onKeyDown={handleFilterEnter}
                placeholder="VD: 0.25"
              />
            </label>
            <label>
              <span className="filter-label">Theta max</span>
              <NumericStepperInput
                min="0"
                step="1"
                value={thetaMax}
                onValueChange={(value) => setThetaMax(value)}
                onKeyDown={handleFilterEnter}
                placeholder="VD: 15"
              />
            </label>
            <label>
              <span className="filter-label">IV-HV max</span>
              <NumericStepperInput
                min="0"
                step="1"
                value={ivHvMax}
                onValueChange={(value) => setIvHvMax(value)}
                onKeyDown={handleFilterEnter}
                placeholder="VD: 20"
              />
            </label>
          </div>
        </div>

        <div className="filter-presets" aria-label={isEnglish ? "Saved filter presets" : "Bộ lọc đã lưu"}>
          <div className="filter-section-header preset-header">
            <span>{isEnglish ? "Preset" : "Bộ lọc đã lưu"}</span>
          </div>
          <div className="preset-save">
            <label>
              <span className="filter-label">{isEnglish ? "Preset name" : "Tên bộ lọc"}</span>
              <input
                value={presetName}
                onChange={(e) => setPresetName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && saveFilterPreset()}
                placeholder={isEnglish ? "High liquidity setup" : "Thanh khoản cao"}
              />
            </label>
            <div className="preset-actions">
              <button type="button" className="preset-reset" onClick={clearFilterPreset}>
                {isEnglish ? "Reset filters" : "Đặt lại bộ lọc"}
              </button>
              <Button variant="secondary" onClick={saveFilterPreset} disabled={!presetName.trim()}>
                <Save size={16} />
                {isEnglish ? "Save setup" : "Lưu bộ lọc"}
              </Button>
            </div>
          </div>
        {filterPresets.length ? (
          <div className="preset-list">
            {filterPresets.map((preset) => (
              <span className={`preset-chip ${activePresetId === preset.id ? "active" : ""}`} key={preset.id}>
                <button type="button" onClick={() => applyFilterPreset(preset)}>
                  <Bookmark size={14} />
                  {preset.name}
                </button>
                <button
                  type="button"
                  className="preset-delete"
                  onClick={() => deleteFilterPreset(preset.id)}
                  aria-label={`Delete ${preset.name}`}
                >
                  <Trash2 size={14} />
                </button>
              </span>
            ))}
          </div>
        ) : null}
      </div>
      </div>

      {error ? <ErrorBox message={error} language={language} /> : null}
      {loading ? <LoadingBox message={isEnglish ? "Loading CW opportunities..." : "Đang tải cơ hội CW..."} /> : null}
      {pendingSymbol ? (
        <div className="notice info">
          {isEnglish ? "Selected" : "Đã chọn"} <strong>{pendingSymbol}</strong>.
          {isEnglish
            ? " Click the same code again to open its detail page."
            : " Bấm cùng mã này lần nữa để mở trang chi tiết."}
        </div>
      ) : null}

      <div
        ref={tableScrollRef}
        className="table-wrap draggable-table"
        onPointerDown={handleTablePointerDown}
        onPointerMove={handleTablePointerMove}
        onPointerUp={endTableDrag}
        onPointerCancel={endTableDrag}
        onPointerLeave={endTableDrag}
      >
        <table>
          <thead>
            <tr>
              <th onClick={() => handleSort("warrant_symbol")} className="sortable">
                {isEnglish ? "CW code" : "Mã CW"}
                {sortColumn === "warrant_symbol" && <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>}
              </th>
              <th onClick={() => handleSort("underlying_symbol")} className="sortable">
                CPCS
                {sortColumn === "underlying_symbol" && <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>}
              </th>
              <th onClick={() => handleSort("underlying_industry")} className="sortable">
                {isEnglish ? "Sector" : "Ngành"}
                {sortColumn === "underlying_industry" && <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>}
              </th>
              <th onClick={() => handleSort("issuer")} className="sortable">
                TCPH
                {sortColumn === "issuer" && <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>}
              </th>
              <th onClick={() => handleSort("market_price")} className="sortable align-right">
                {isEnglish ? "Price" : "Giá"}
                {sortColumn === "market_price" && <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>}
              </th>
              <th onClick={() => handleSort("price_change_pct")} className="sortable align-right">
                {isEnglish ? "% Change" : "% Thay đổi"}
                {sortColumn === "price_change_pct" && <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>}
              </th>
              <th onClick={() => handleSort("underlying_price")} className="sortable align-right">
                {isEnglish ? "Underlying px" : "Giá CPCS"}
                {sortColumn === "underlying_price" && <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>}
              </th>
              <th onClick={() => handleSort("premium_pct")} className="sortable align-right">
                Premium
                {sortColumn === "premium_pct" && <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>}
              </th>
              <th onClick={() => handleSort("volume")} className="sortable align-right">
                Volume
                {sortColumn === "volume" && <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>}
              </th>
              <th onClick={() => handleSort("composite_g_score")} className="sortable align-right">
                {isEnglish ? "Score" : "Điểm"}
                {sortColumn === "composite_g_score" && <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>}
              </th>
              <th onClick={() => handleSort("effective_gearing")} className="sortable align-right">
                Gearing
                {sortColumn === "effective_gearing" && <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>}
              </th>
              <th onClick={() => handleSort("delta")} className="sortable align-right">
                Delta
                {sortColumn === "delta" && <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>}
              </th>
              <th onClick={() => handleSort("theta_daily_burn")} className="sortable align-right">
                Theta
                {sortColumn === "theta_daily_burn" && <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>}
              </th>
              <th onClick={() => handleSort("implied_volatility_pct")} className="sortable align-right">
                IV/HV
                {sortColumn === "implied_volatility_pct" && <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>}
              </th>
              <th onClick={() => handleSort("days_to_maturity")} className="sortable align-center">
                {isEnglish ? "Days left" : "Còn lại"}
                {sortColumn === "days_to_maturity" && <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>}
              </th>
              <th onClick={() => handleSort("recommendation_signal")} className="sortable align-center">
                {isEnglish ? "Signal" : "Tín hiệu"}
                {sortColumn === "recommendation_signal" && <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>}
              </th>
            </tr>
          </thead>
          <tbody>
            {paginatedRows.length === 0 && !loading ? (
              <tr>
                 <td colSpan="16" className="empty-cell">
                  {isEnglish
                    ? "No matching rows. Adjust filters or reload data."
                    : "Không có dòng phù hợp. Hãy đổi bộ lọc hoặc tải lại dữ liệu."}
                </td>
              </tr>
            ) : null}
            {paginatedRows.map((row) => (
              <tr
                key={row.warrant_symbol}
                className={pendingSymbol === row.warrant_symbol ? "selected-row" : ""}
                onClick={() => handleRowClick(row.warrant_symbol)}
                onDoubleClick={() => openDetail(row.warrant_symbol)}
              >
                <td className="strong-cell">{row.warrant_symbol}</td>
                <td>{row.underlying_symbol}</td>
                <td>{displayIndustry(row.underlying_industry, language) || "-"}</td>
                <td>{row.issuer || "-"}</td>
                <td className="align-right">{formatMoney(row.market_price)}đ</td>
                <td className="align-right">
                  {row.price_change_pct !== null && row.price_change_pct !== undefined ? (
                    <span className={Number(row.price_change_pct) > 0 ? "text-green" : Number(row.price_change_pct) < 0 ? "text-red" : ""}>
                      {Number(row.price_change_pct) > 0 ? "+" : ""}{formatNumber(row.price_change_pct, 1)}%
                    </span>
                  ) : "-"}
                </td>
                <td className="align-right">{formatMoney(row.underlying_price)}đ</td>
                <td className="align-right">
                  <span className={Number(row.premium_pct) < 0 ? "text-green" : Number(row.premium_pct) > 15 ? "text-red" : ""}>
                    {formatNumber(row.premium_pct, 1)}%
                  </span>
                </td>
                <td className="align-right">{formatMoney(row.volume)}</td>
                <td className="align-right">
                  <span className={Number(row.composite_g_score) >= 70 ? "text-green" : Number(row.composite_g_score) <= 50 ? "text-red" : ""}>
                    {formatNumber(row.composite_g_score, 1)}
                  </span>
                </td>
                <td className="align-right">{formatNumber(row.effective_gearing, 2)}x</td>
                <td className="align-right">
                  <span className={Number(row.delta) >= 0.3 && Number(row.delta) <= 0.7 ? "text-green" : Number(row.delta) < 0.15 ? "text-red" : ""}>
                    {formatNumber(row.delta, 4)}
                  </span>
                </td>
                <td className="align-right">
                  <span className={Math.abs(Number(row.theta_daily_burn)) > 20 ? "text-red" : ""}>
                    {formatNumber(row.theta_daily_burn, 0)}đ
                  </span>
                </td>
                <td className="align-right">
                  <span className={Math.abs(Number(row.implied_volatility_pct) - Number(row.historical_volatility_pct)) > 10 ? "text-yellow" : ""}>
                    {formatNumber(row.implied_volatility_pct, 1)}% /{"  "}
                    {formatNumber(row.historical_volatility_pct, 1)}%
                  </span>
                </td>
                <td className="align-center">
                  {row.days_to_maturity ?? "-"} {isEnglish ? "days" : "ngày"}
                </td>
                <td className="align-center">
                  <span className={signalClass(row.recommendation_signal)}>
                    {formatSignal(row.recommendation_signal, isEnglish)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 ? (
        <div className="pagination-wrapper">
          <Button
            variant="secondary"
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={safeCurrentPage === 1}
          >
            {isEnglish ? "Previous" : "Trang trước"}
          </Button>
          <span className="pagination-text">
            {isEnglish ? `Page ${safeCurrentPage} of ${totalPages}` : `Trang ${safeCurrentPage} / ${totalPages}`}
            <span className="pagination-sub">
              ({isEnglish ? `Showing ${startIndex + 1}-${endIndex} of ${filteredRows.length}` : `Hiển thị ${startIndex + 1}-${endIndex} của ${filteredRows.length} mã`})
            </span>
          </span>
          <Button
            variant="secondary"
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={safeCurrentPage === totalPages}
          >
            {isEnglish ? "Next" : "Trang sau"}
          </Button>
        </div>
      ) : null}

      <p className="helper-text">
        {isEnglish
          ? "Click a row to select it, then click it again to open CW Detail."
          : "Bấm một dòng để chọn, sau đó bấm lại để mở Chi tiết CW."}
        {auth.isAdmin && filteredRows.length === 0 ? (
          <>
            {" "}
            {isEnglish ? "Admin note: refresh market data if the table remains empty." : "Ghi chú quản trị: hãy làm mới dữ liệu thị trường nếu bảng vẫn trống."}
          </>
        ) : null}
      </p>
    </section>
  );
}
