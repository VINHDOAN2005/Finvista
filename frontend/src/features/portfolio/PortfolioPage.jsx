import React, { useEffect, useState } from "react";
import { 
  Briefcase, 
  DollarSign, 
  RefreshCw, 
  TrendingUp, 
  TrendingDown, 
  History, 
  RotateCcw,
  Zap,
  ArrowRightLeft,
  AlertCircle
} from "lucide-react";

import { getPortfolio, placeOrder, resetPortfolio, scanPortfolio } from "../../api.js";
import { InteractiveLineChart } from "../../components/charts/WarrantCharts.jsx";
import { Button } from "../../components/ui/button.jsx";
import { Input } from "../../components/ui/input.jsx";
import { ErrorBox, LoadingBox, MetricCard } from "../../components/ui/status.jsx";
import { formatMoney, formatNumber } from "../../lib/formatters.js";

export function PortfolioPage({ language = "vi", prepopulatedSymbol = "", clearPrepopulatedSymbol }) {
  const isEnglish = language === "en";
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Order Form State
  const [symbol, setSymbol] = useState(prepopulatedSymbol || "");
  const [side, setSide] = useState("BUY");
  const [qty, setQty] = useState("");
  const [price, setPrice] = useState("");
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (prepopulatedSymbol) {
      setSymbol(prepopulatedSymbol);
      if (clearPrepopulatedSymbol) {
        clearPrepopulatedSymbol();
      }
    }
  }, [prepopulatedSymbol]);

  async function loadPortfolioData() {
    setLoading(true);
    setError("");
    try {
      const result = await getPortfolio();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPortfolioData();
  }, []);

  async function handleReset() {
    if (!window.confirm(
      isEnglish 
        ? "Are you sure you want to reset your paper trading account? This clears all positions and transaction logs."
        : "Bạn có chắc chắn muốn khởi tạo lại tài khoản giao dịch giả lập? Việc này sẽ xóa sạch danh mục và nhật ký giao dịch."
    )) return;

    setActionLoading(true);
    setError("");
    setSuccessMsg("");
    try {
      await resetPortfolio();
      setSuccessMsg(isEnglish ? "Account reset successfully." : "Khởi tạo lại tài khoản thành công.");
      await loadPortfolioData();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleScan(force = false) {
    setActionLoading(true);
    setError("");
    setSuccessMsg("");
    try {
      const res = await scanPortfolio(force);
      const actions = res.actions_executed || [];
      if (actions.length === 0) {
        setSuccessMsg(
          isEnglish 
            ? "Risk-scan executed: No rebalancing or risk actions needed at this moment."
            : "Đã quét rủi ro: Không có hành động tái cơ cấu hoặc cắt lỗ nào cần thực hiện lúc này."
        );
      } else {
        setSuccessMsg(
          isEnglish 
            ? `Risk-scan executed: Automated actions run successfully: ${actions.join(", ")}`
            : `Đã quét rủi ro: Thực thi thành công hành động tự động: ${actions.join(", ")}`
        );
      }
      await loadPortfolioData();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  async function handlePlaceOrder(e) {
    e.preventDefault();
    setError("");
    setSuccessMsg("");

    const targetSymbol = symbol.trim().toUpperCase();
    if (!targetSymbol) {
      setError(isEnglish ? "Please enter a warrant symbol." : "Vui lòng nhập mã chứng quyền.");
      return;
    }

    const orderQty = parseInt(qty);
    if (!orderQty || orderQty <= 0) {
      setError(isEnglish ? "Please enter a valid quantity." : "Vui lòng nhập khối lượng hợp lệ.");
      return;
    }

    if (orderQty % 100 !== 0) {
      setError(isEnglish ? "Order quantity must be a multiple of 100 (HOSE rule)." : "Khối lượng đặt phải chia hết cho 100 (Luật HOSE).");
      return;
    }

    setActionLoading(true);
    try {
      const res = await placeOrder({
        symbol: targetSymbol,
        side,
        qty: orderQty,
        price: price ? parseFloat(price) : undefined,
        reason: reason.trim() || undefined
      });
      setSuccessMsg(res.message || (isEnglish ? "Order placed successfully." : "Đặt lệnh thành công."));
      setSymbol("");
      setQty("");
      setPrice("");
      setReason("");
      await loadPortfolioData();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleQuickSell(item) {
    if (!window.confirm(
      isEnglish 
        ? `Place sell order for all ${item.qty} shares of ${item.symbol}?`
        : `Đặt lệnh bán toàn bộ ${item.qty} chứng quyền ${item.symbol}?`
    )) return;

    setActionLoading(true);
    setError("");
    setSuccessMsg("");
    try {
      const res = await placeOrder({
        symbol: item.symbol,
        side: "SELL",
        qty: item.qty,
        reason: "Manual Quick Sell from Dashboard"
      });
      setSuccessMsg(res.message || (isEnglish ? "Sell order executed." : "Lệnh bán đã thực hiện xong."));
      await loadPortfolioData();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  if (loading && !data) {
    return <LoadingBox text={isEnglish ? "Loading portfolio data..." : "Đang tải dữ liệu danh mục..."} />;
  }

  const cash = data?.cash ?? 0;
  const initialCash = data?.initial_cash ?? 0;
  const positionsValue = data?.positions_value ?? 0;
  const nav = data?.total_nav ?? 0;
  const p_l_vnd = data?.cumulative_p_l_vnd ?? 0;
  const p_l_pct = data?.cumulative_p_l_pct ?? 0;
  const activePositions = data?.active_positions || [];
  const history = data?.history || [];

  const isProfit = p_l_vnd >= 0;
  const plClass = isProfit ? "text-success" : "text-danger";

  return (
    <div className="portfolio-container">
      {/* Title Header */}
      <div className="section-header-row">
        <div>
          <h2>{isEnglish ? "Paper Trading Dashboard" : "Giao dịch giả lập thực chiến"}</h2>
          <p className="subtitle-desc">
            {isEnglish 
              ? "Simulate warrant investments, monitor live portfolios, and test algorithms under HOSE regulations." 
              : "Mô phỏng đầu tư chứng quyền, giám sát danh mục trực tiếp và kiểm thử thuật toán theo luật HOSE."}
          </p>
        </div>
        <div className="action-buttons-group">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => loadPortfolioData()}
            disabled={actionLoading || loading}
          >
            <RefreshCw size={14} className={actionLoading || loading ? "animate-spin" : ""} />
            {isEnglish ? "Sync" : "Đồng bộ"}
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => handleScan(false)}
            disabled={actionLoading}
            className="action-accent-green"
          >
            <Zap size={14} />
            {isEnglish ? "Scan & Rebalance" : "Quét & Tái cơ cấu"}
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleReset}
            disabled={actionLoading}
            className="action-accent-red"
          >
            <RotateCcw size={14} />
            {isEnglish ? "Reset Portfolio" : "Khởi tạo lại"}
          </Button>
        </div>
      </div>

      {/* Messages */}
      {error && <ErrorBox message={error} />}
      {successMsg && (
        <div className="alert alert-success" style={{ margin: "1rem 0" }}>
          <span>{successMsg}</span>
        </div>
      )}

      {/* Account stats cards */}
      <div className="metric-tiles-row">
        <MetricCard
          title={isEnglish ? "Net Asset Value (NAV)" : "Tài sản ròng (NAV)"}
          value={`${formatMoney(nav)}đ`}
          icon={<Briefcase size={20} />}
          description={
            <span className={plClass}>
              {isProfit ? "+" : ""}{formatMoney(p_l_vnd)}đ ({formatNumber(p_l_pct, 2)}%)
            </span>
          }
        />
        <MetricCard
          title={isEnglish ? "Cash Balance" : "Số dư tiền mặt"}
          value={`${formatMoney(cash)}đ`}
          icon={<DollarSign size={20} />}
          description={
            <span>
              {isEnglish ? "Allocated:" : "Đã phân bổ:"} {formatNumber((positionsValue / (nav || 1)) * 100, 1)}%
            </span>
          }
        />
        <MetricCard
          title={isEnglish ? "Positions Value" : "Giá trị chứng quyền"}
          value={`${formatMoney(positionsValue)}đ`}
          icon={<TrendingUp size={20} />}
          description={
            <span>
              {activePositions.length} {isEnglish ? "active positions" : "vị thế đang mở"}
            </span>
          }
        />
      </div>

      {data?.nav_history?.length > 1 ? (
        <div className="portfolio-chart-container" style={{ marginBottom: "2rem" }}>
          <InteractiveLineChart
            title={isEnglish ? "Historical NAV Trend" : "Xu hướng tài sản ròng"}
            subtitle={isEnglish ? "Total NAV and Cash over time" : "Tài sản ròng & Tiền mặt lịch sử"}
            series={[
              {
                key: "nav",
                label: isEnglish ? "Total NAV" : "Tài sản ròng (NAV)",
                color: "#3f88c5",
                points: data.nav_history.map((item) => ({
                  date: item.date,
                  value: item.nav
                }))
              },
              {
                key: "cash",
                label: isEnglish ? "Cash" : "Tiền mặt",
                color: "#2ec4b6",
                points: data.nav_history.map((item) => ({
                  date: item.date,
                  value: item.cash
                }))
              }
            ]}
            language={language}
            valueSuffix=" VND"
          />
        </div>
      ) : null}

      <div className="portfolio-grid-layout">
        {/* Left Side: Positions table */}
        <div className="positions-panel-container">
          <div className="panel-box">
            <h3 className="panel-title">{isEnglish ? "Active Positions" : "Danh mục nắm giữ"}</h3>
            
            {activePositions.length === 0 ? (
              <div className="empty-panel-state">
                <AlertCircle size={32} />
                <p>{isEnglish ? "No active positions. Make your first transaction using the order form." : "Danh mục đang trống. Hãy thực hiện lệnh giao dịch đầu tiên."}</p>
              </div>
            ) : (
              <div className="scrollable-table-wrapper">
                <table className="opportunities-table">
                  <thead>
                    <tr>
                      <th>{isEnglish ? "CW Symbol" : "Mã CW"}</th>
                      <th>{isEnglish ? "Underlying" : "Cơ sở"}</th>
                      <th className="align-right">{isEnglish ? "Qty" : "Số lượng"}</th>
                      <th className="align-right">{isEnglish ? "Avg Cost" : "Giá mua TB"}</th>
                      <th className="align-right">{isEnglish ? "Current Px" : "Giá hiện tại"}</th>
                      <th className="align-right">{isEnglish ? "Market Value" : "Trị giá"}</th>
                      <th className="align-right">{isEnglish ? "P/L" : "Lãi/Lỗ"}</th>
                      <th>{isEnglish ? "Status" : "Trạng thái"}</th>
                      <th className="align-center">{isEnglish ? "Action" : "Hành động"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activePositions.map((item) => {
                      const posProfit = item.p_l_vnd >= 0;
                      const posPlClass = posProfit ? "text-success" : "text-danger";
                      return (
                        <tr key={item.symbol}>
                          <td><strong>{item.symbol}</strong></td>
                          <td><span className="badge badge-muted">{item.underlying}</span></td>
                          <td className="align-right">{formatMoney(item.qty)}</td>
                          <td className="align-right">{formatMoney(item.buy_price)}đ</td>
                          <td className="align-right">{formatMoney(item.current_price)}đ</td>
                          <td className="align-right">{formatMoney(item.current_value)}đ</td>
                          <td className={`align-right ${posPlClass}`}>
                            <strong>{posProfit ? "+" : ""}{formatNumber(item.p_l_pct, 1)}%</strong>
                            <div style={{ fontSize: "0.75rem", opacity: 0.8 }}>
                              {posProfit ? "+" : ""}{formatMoney(item.p_l_vnd)}đ
                            </div>
                          </td>
                          <td>
                            {item.is_locked ? (
                              <span className="badge badge-danger" title={`Settlement locked`}>
                                T+2.5 ({item.lock_hours_remaining}h)
                              </span>
                            ) : (
                              <span className="badge badge-success">Tradable</span>
                            )}
                          </td>
                          <td className="align-center">
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={item.is_locked || actionLoading}
                              onClick={() => handleQuickSell(item)}
                              className="action-accent-red"
                              style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
                            >
                              {isEnglish ? "Sell" : "Bán"}
                            </Button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Order placement form */}
        <div className="order-panel-container">
          <div className="panel-box">
            <h3 className="panel-title">{isEnglish ? "Place Order" : "Đặt lệnh giao dịch"}</h3>
            <form onSubmit={handlePlaceOrder} className="order-placement-form">
              <div className="form-group-toggle">
                <button
                  type="button"
                  className={`toggle-btn buy ${side === "BUY" ? "active" : ""}`}
                  onClick={() => setSide("BUY")}
                >
                  {isEnglish ? "BUY (MUA)" : "MUA"}
                </button>
                <button
                  type="button"
                  className={`toggle-btn sell ${side === "SELL" ? "active" : ""}`}
                  onClick={() => setSide("SELL")}
                >
                  {isEnglish ? "SELL (BÁN)" : "BÁN"}
                </button>
              </div>

              <div className="form-field">
                <label>{isEnglish ? "Covered Warrant Symbol" : "Mã chứng quyền"}</label>
                <Input
                  type="text"
                  placeholder="e.g. CACB2511"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  required
                />
              </div>

              <div className="form-field">
                <label>{isEnglish ? "Quantity" : "Khối lượng"}</label>
                <Input
                  type="number"
                  placeholder="e.g. 1000 (Multiple of 100)"
                  value={qty}
                  onChange={(e) => setQty(e.target.value)}
                  required
                />
                <span className="field-hint">
                  {isEnglish ? "HOSE lot size: multiple of 100 CW" : "Quy định sàn HOSE: lô tối thiểu 100 CW"}
                </span>
              </div>

              <div className="form-field">
                <label>{isEnglish ? "Price Override (Optional)" : "Giá chỉ định (Tùy chọn)"}</label>
                <Input
                  type="number"
                  step="1"
                  placeholder={isEnglish ? "Market price if empty" : "Để trống dùng giá thị trường"}
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                />
              </div>

              <div className="form-field">
                <label>{isEnglish ? "Reason / Strategy Note" : "Ghi chú chiến lược"}</label>
                <Input
                  type="text"
                  placeholder="e.g. Volatility arbitrage"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </div>

              <Button
                type="submit"
                disabled={actionLoading}
                className={side === "BUY" ? "submit-buy-btn" : "submit-sell-btn"}
              >
                <ArrowRightLeft size={16} />
                {isEnglish 
                  ? `Execute ${side} Order` 
                  : `Thực hiện đặt lệnh ${side === "BUY" ? "MUA" : "BÁN"}`}
              </Button>
            </form>
          </div>
        </div>
      </div>

      {/* Transaction Logs */}
      <div className="panel-box text-logs-panel" style={{ marginTop: "1.5rem" }}>
        <h3 className="panel-title flex-title-row">
          <span><History size={16} /> {isEnglish ? "Transaction History" : "Nhật ký giao dịch"}</span>
          <span className="badge badge-muted">{history.length} {isEnglish ? "records" : "lịch sử"}</span>
        </h3>

        {history.length === 0 ? (
          <div className="empty-panel-state">
            <p>{isEnglish ? "No transactions recorded yet." : "Chưa ghi nhận giao dịch nào."}</p>
          </div>
        ) : (
          <div className="scrollable-table-wrapper">
            <table className="opportunities-table">
              <thead>
                <tr>
                  <th>{isEnglish ? "Date & Time" : "Thời gian"}</th>
                  <th>{isEnglish ? "CW Symbol" : "Mã CW"}</th>
                  <th>{isEnglish ? "Type" : "Loại lệnh"}</th>
                  <th className="align-right">{isEnglish ? "Quantity" : "Khối lượng"}</th>
                  <th className="align-right">{isEnglish ? "Price" : "Giá khớp"}</th>
                  <th className="align-right">{isEnglish ? "Total Value" : "Giá trị"}</th>
                  <th className="align-right">{isEnglish ? "Fee Paid" : "Phí"}</th>
                  <th>{isEnglish ? "Strategy Notes" : "Lý do / Ghi chú"}</th>
                </tr>
              </thead>
              <tbody>
                {history.map((tx, idx) => {
                  const isBuy = tx.type === "BUY" || tx.type === "buy";
                  return (
                    <tr key={`${tx.date}-${tx.symbol}-${idx}`}>
                      <td>{tx.date}</td>
                      <td><strong>{tx.symbol}</strong></td>
                      <td>
                        <span className={`badge ${isBuy ? "badge-success" : "badge-danger"}`}>
                          {tx.type}
                        </span>
                      </td>
                      <td className="align-right">{formatMoney(tx.qty)}</td>
                      <td className="align-right">{formatMoney(tx.price)}đ</td>
                      <td className="align-right">{formatMoney(tx.value)}đ</td>
                      <td className="align-right">{formatMoney(tx.fee)}đ</td>
                      <td><span style={{ fontSize: "0.85rem", opacity: 0.9 }}>{tx.reason}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
