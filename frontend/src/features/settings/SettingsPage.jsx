import React, { useEffect, useRef, useState } from "react";
import { ShieldCheck } from "lucide-react";

import { getAdminSecretStatus } from "../../api.js";
import { DEFAULT_PREFERENCES } from "../../app/config.js";
import { useAuth } from "../../auth/AuthProvider.jsx";
import { ErrorBox, LoadingBox, MetricCard, StatusPill } from "../../components/ui/status.jsx";
import { formatMoney } from "../../lib/formatters.js";

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

function HealthDashboard({ health, loading, error, refresh, language = "vi" }) {
  const isEnglish = language === "en";
  const registry = health?.model_registry || {};
  const db = health?.database_layer || {};
  const cache = health?.live_market_cache || {};

  return (
    <section className="page-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{isEnglish ? "Technical status" : "Trạng thái kỹ thuật"}</p>
          <h2>{isEnglish ? "Backend Overview" : "Tổng quan Backend"}</h2>
        </div>
        <button className="secondary-button" onClick={refresh}>
          {isEnglish ? "Refresh" : "Làm mới"}
        </button>
      </div>

      {error ? <ErrorBox message={error} language={language} /> : null}
      {loading ? <LoadingBox message={isEnglish ? "Loading /api/health..." : "Đang tải /api/health..."} /> : null}

      <KpiGroup
        title={isEnglish ? "Service status" : "Trạng thái dịch vụ"}
        description={isEnglish ? "Connectivity and API health." : "Kết nối và sức khỏe API."}
      >
        <div className="metric-grid">
          <MetricCard
            label="Backend"
            value={health?.status || (isEnglish ? "unknown" : "chưa rõ")}
            tone={health?.status === "healthy" ? "success" : "warning"}
            detail="GET /api/health"
          />
          <MetricCard
            label={isEnglish ? "Last scan" : "Lần quét gần nhất"}
            value={cache.last_scan_timestamp || (isEnglish ? "No scan yet" : "Chưa có")}
          />
        </div>
      </KpiGroup>

      <KpiGroup
        title={isEnglish ? "Credit-risk model" : "Model rủi ro tín dụng"}
        description={isEnglish ? "Model artifacts and enterprise dataset readiness." : "Trạng thái artifact model và dataset doanh nghiệp."}
      >
        <div className="metric-grid">
          <MetricCard
            label={isEnglish ? "XGBoost model" : "Model XGBoost"}
            value={registry.xgboost_model_loaded ? (isEnglish ? "Loaded" : "Đã tải") : (isEnglish ? "Missing" : "Thiếu")}
            tone={registry.xgboost_model_loaded ? "success" : "warning"}
          />
          <MetricCard
            label="Scaler"
            value={registry.scaler_loaded ? (isEnglish ? "Loaded" : "Đã tải") : (isEnglish ? "Missing" : "Thiếu")}
            tone={registry.scaler_loaded ? "success" : "warning"}
          />
          <MetricCard
            label={isEnglish ? "Enterprise records" : "Bản ghi doanh nghiệp"}
            value={formatMoney(db.total_corporate_records)}
            detail={db.distress_dataset_found ? (isEnglish ? "Dataset found" : "Có dataset") : (isEnglish ? "Dataset missing" : "Thiếu dataset")}
          />
        </div>
      </KpiGroup>

      <KpiGroup
        title={isEnglish ? "Market cache" : "Cache thị trường"}
        description={isEnglish ? "Runtime data used by CW opportunities and market overview." : "Dữ liệu runtime dùng cho cơ hội CW và tổng quan thị trường."}
      >
        <div className="metric-grid">
          <MetricCard
            label={isEnglish ? "Warrant cache" : "Cache chứng quyền"}
            value={cache.cached_warrants_present ? (isEnglish ? "Ready" : "Sẵn sàng") : (isEnglish ? "Empty" : "Trống")}
            tone={cache.cached_warrants_present ? "success" : "warning"}
          />
        </div>
      </KpiGroup>
    </section>
  );
}

function SystemFlow({ language = "vi" }) {
  const isEnglish = language === "en";
  return (
    <div className="system-panel compact" aria-label="Luồng hệ thống Finvista">
      <div className="panel-header">
        <span>{isEnglish ? "Backend flow" : "Luồng Backend"}</span>
        <span className="dot-row">
          <i />
          <i />
          <i />
        </span>
      </div>
      <div className="flow-stack">
        <div>Browser</div>
        <span>↓</span>
        <div>Frontend React + Vite</div>
        <span>↓</span>
        <div>Backend FastAPI</div>
        <span>↓</span>
        <div>SQLite / CW Engine / Credit Risk</div>
      </div>
    </div>
  );
}

export function SettingsPage({
  health,
  healthLoading,
  healthError,
  refreshHealth,
  language,
  setLanguage,
  preferences,
  setPreferences
}) {
  const auth = useAuth();
  const [showBackend, setShowBackend] = useState(false);
  const [notifyStatus, setNotifyStatus] = useState(false);
  const [secretStatus, setSecretStatus] = useState(null);
  const [secretLoading, setSecretLoading] = useState(false);
  const [secretError, setSecretError] = useState("");
  const secretPanelRef = useRef(null);
  const isEnglish = language === "en";

  useEffect(() => {
    if (!secretStatus) return undefined;

    function hideSecretStatusOnOutsideClick(event) {
      if (secretPanelRef.current && !secretPanelRef.current.contains(event.target)) {
        setSecretStatus(null);
      }
    }

    document.addEventListener("pointerdown", hideSecretStatusOnOutsideClick);
    return () => document.removeEventListener("pointerdown", hideSecretStatusOnOutsideClick);
  }, [secretStatus]);

  async function loadSecretStatus() {
    if (!auth.isAdmin) return;
    if (secretStatus) {
      setSecretStatus(null);
      return;
    }
    setSecretLoading(true);
    setSecretError("");
    try {
      const result = await getAdminSecretStatus();
      setSecretStatus(result);
    } catch (err) {
      setSecretError(err.message);
    } finally {
      setSecretLoading(false);
    }
  }

  return (
    <section className="page-section settings-page">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{isEnglish ? "Setup" : "Thiết lập"}</p>
          <h2>{isEnglish ? "Settings" : "Cài đặt"}</h2>
        </div>
        <div className="settings-actions">
          <button
            className="secondary-button"
            onClick={() => setPreferences(DEFAULT_PREFERENCES)}
          >
            {isEnglish ? "Reset defaults" : "Khôi phục mặc định"}
          </button>
          {auth.isAdmin ? (
            <StatusPill
              health={health}
              loading={healthLoading}
              error={healthError}
              language={language}
            />
          ) : null}
        </div>
      </div>

      <div className="settings-grid">
        <div className="settings-group-title">
          <span>{isEnglish ? "Interface" : "Giao diện"}</span>
          <p>{isEnglish ? "Language, theme, and table layout." : "Ngôn ngữ, theme và cách hiển thị bảng."}</p>
        </div>

        <article className="setting-card">
          <span>{isEnglish ? "Language" : "Ngôn ngữ"}</span>
          <strong>{isEnglish ? "English" : "Tiếng Việt"}</strong>
          <p>
            {isEnglish
              ? "Switch all supported labels and messages across the app."
              : "Chuyển toàn bộ nhãn và thông báo được hỗ trợ trong ứng dụng."}
          </p>
          <div className="segmented-control" aria-label="Chọn ngôn ngữ">
            <button
              className={language === "vi" ? "active" : ""}
              onClick={() => setLanguage("vi")}
              data-tooltip={isEnglish ? "Switch to Vietnamese" : "Chuyển sang tiếng Việt"}
            >
              VI
            </button>
            <button
              className={language === "en" ? "active" : ""}
              onClick={() => setLanguage("en")}
              data-tooltip={isEnglish ? "Switch to English" : "Chuyển sang tiếng Anh"}
            >
              EN
            </button>
          </div>
        </article>

        <article className="setting-card">
          <span>{isEnglish ? "Appearance" : "Giao diện"}</span>
          <strong>{preferences.colorMode === "dark" ? (isEnglish ? "Dark workspace" : "Không gian tối") : (isEnglish ? "Light workspace" : "Không gian sáng")}</strong>
          <p>
            {isEnglish
              ? "Control the visual style. Light stays calm, dark reduces glare while keeping charts readable."
              : "Điều chỉnh cảm giác hiển thị. Sáng giữ sự dịu mắt, tối giảm chói nhưng vẫn ưu tiên đọc chart."}
          </p>
          <div className="segmented-control setting-mode-control" aria-label={isEnglish ? "Color mode" : "Chế độ màu"}>
            <button
              className={preferences.colorMode !== "dark" ? "active" : ""}
              onClick={() =>
                setPreferences((current) => ({
                  ...current,
                  colorMode: "light"
                }))
              }
              data-tooltip={isEnglish ? "Use light mode" : "Dùng nền sáng"}
            >
              {isEnglish ? "Light" : "Sáng"}
            </button>
            <button
              className={preferences.colorMode === "dark" ? "active" : ""}
              onClick={() =>
                setPreferences((current) => ({
                  ...current,
                  colorMode: "dark"
                }))
              }
              data-tooltip={isEnglish ? "Use dark mode" : "Dùng nền tối"}
            >
              {isEnglish ? "Dark" : "Tối"}
            </button>
          </div>
          <div className="setting-row">
            <label>
              {isEnglish ? "Theme" : "Theme"}
              <select
                value={preferences.theme}
                onChange={(event) =>
                  setPreferences((current) => ({
                    ...current,
                    theme: event.target.value
                  }))
                }
              >
                <option value="soft">{isEnglish ? "Soft" : "Dịu mắt"}</option>
                <option value="clear">{isEnglish ? "Clear" : "Rõ nét"}</option>
              </select>
            </label>
          </div>
        </article>

        <article className="setting-card">
          <span>{isEnglish ? "Data display" : "Hiển thị dữ liệu"}</span>
          <strong>{isEnglish ? "Table comfort" : "Độ thoáng bảng"}</strong>
          <p>
            {isEnglish
              ? "Choose how dense tables should feel and whether helper hints are visible."
              : "Chọn bảng hiển thị thoáng hay gọn, và bật/tắt gợi ý thao tác."}
          </p>
          <div className="setting-row">
            <label>
              {isEnglish ? "Density" : "Mật độ"}
              <select
                value={preferences.density}
                onChange={(event) =>
                  setPreferences((current) => ({
                    ...current,
                    density: event.target.value
                  }))
                }
              >
                <option value="comfortable">{isEnglish ? "Comfortable" : "Thoáng"}</option>
                <option value="compact">{isEnglish ? "Compact" : "Gọn"}</option>
              </select>
            </label>
          </div>
          <label className="toggle-line">
            <input
              type="checkbox"
              checked={preferences.tableHints}
              onChange={(event) =>
                setPreferences((current) => ({
                  ...current,
                  tableHints: event.target.checked
                }))
              }
            />
            <span>{isEnglish ? "Show table hints" : "Hiện gợi ý trong bảng"}</span>
          </label>
        </article>

        <div className="settings-group-title">
          <span>{isEnglish ? "Chart interaction" : "Tương tác đồ thị"}</span>
          <p>{isEnglish ? "Tune zoom, pan, and animation behavior." : "Tùy chỉnh zoom, kéo ngang và chuyển động."}</p>
        </div>

        <article className="setting-card">
          <span>{isEnglish ? "Motion" : "Chuyển động"}</span>
          <strong>{preferences.smoothMotion ? (isEnglish ? "Enabled" : "Đang bật") : (isEnglish ? "Disabled" : "Đang tắt")}</strong>
          <p>
            {isEnglish
              ? "Smooth transitions make page changes feel softer. Turn this off if you prefer a static interface."
              : "Chuyển động mượt giúp đổi trang dịu hơn. Có thể tắt nếu bạn muốn giao diện tĩnh."}
          </p>
          <label className="toggle-line">
            <input
              type="checkbox"
              checked={preferences.smoothMotion}
              onChange={(event) =>
                setPreferences((current) => ({
                  ...current,
                  smoothMotion: event.target.checked
                }))
              }
            />
            <span>{isEnglish ? "Use smooth animation" : "Dùng animation mượt"}</span>
          </label>
        </article>

        <article className="setting-card">
          <span>{isEnglish ? "Zoom speed" : "Tốc độ zoom"}</span>
          <strong>{preferences.zoomSpeed}</strong>
          <p>
            {isEnglish
              ? "Controls how strongly the chart zooms when using the mouse wheel."
              : "Điều chỉnh mức zoom mỗi lần lăn chuột trong chart."}
          </p>
          <div className="setting-row">
            <select
              value={preferences.zoomSpeed}
              onChange={(event) =>
                setPreferences((current) => ({
                  ...current,
                  zoomSpeed: event.target.value
                }))
              }
            >
              <option value="slow">{isEnglish ? "Slow" : "Chậm"}</option>
              <option value="normal">{isEnglish ? "Normal" : "Vừa"}</option>
              <option value="fast">{isEnglish ? "Fast" : "Nhanh"}</option>
            </select>
          </div>
        </article>

        <article className="setting-card">
          <span>{isEnglish ? "Pan speed" : "Tốc độ kéo ngang"}</span>
          <strong>{preferences.panSpeed}</strong>
          <p>
            {isEnglish
              ? "Controls how far the chart moves when dragging left or right."
              : "Điều chỉnh chart trượt xa bao nhiêu khi kéo trái/phải."}
          </p>
          <div className="setting-row">
            <select
              value={preferences.panSpeed}
              onChange={(event) =>
                setPreferences((current) => ({
                  ...current,
                  panSpeed: event.target.value
                }))
              }
            >
              <option value="slow">{isEnglish ? "Slow" : "Chậm"}</option>
              <option value="normal">{isEnglish ? "Normal" : "Vừa"}</option>
              <option value="fast">{isEnglish ? "Fast" : "Nhanh"}</option>
            </select>
          </div>
        </article>

        {auth.isAdmin ? (
          <>
            <div className="settings-group-title">
              <span>{isEnglish ? "Administration" : "Quản trị"}</span>
              <p>
                {isEnglish
                  ? "Private tools for system monitoring and beta operations."
                  : "Công cụ riêng để theo dõi hệ thống và vận hành private beta."}
              </p>
            </div>

            <article className="setting-card">
              <span>{isEnglish ? "Beta notifications" : "Thông báo beta"}</span>
              <strong>{notifyStatus ? (isEnglish ? "Beta enabled" : "Beta đang bật") : (isEnglish ? "Beta off" : "Beta đang tắt")}</strong>
              <p>
                {isEnglish
                  ? "Experimental controls for future operational notifications."
                  : "Điều khiển thử nghiệm cho các thông báo vận hành sau này."}
              </p>
              <label className="toggle-line">
                <input
                  type="checkbox"
                  checked={notifyStatus}
                  onChange={(event) => setNotifyStatus(event.target.checked)}
                />
                <span>{isEnglish ? "Enable beta status alerts" : "Bật cảnh báo beta"}</span>
              </label>
            </article>

            <article className="setting-card">
              <span>{isEnglish ? "System monitoring" : "Theo dõi hệ thống"}</span>
              <strong>{isEnglish ? "Technical overview" : "Tổng quan kỹ thuật"}</strong>
              <p>
                {isEnglish
                  ? "View service health, loaded models, and the technical flow."
                  : "Xem trạng thái dịch vụ, model đã tải và luồng kỹ thuật."}
              </p>
              <button
                className="primary-button"
                onClick={() => setShowBackend((value) => !value)}
              >
                {showBackend
                  ? isEnglish ? "Hide overview" : "Ẩn tổng quan"
                  : isEnglish ? "View overview" : "Xem tổng quan"}
              </button>
            </article>
          </>
        ) : null}
      </div>

      {auth.isAdmin ? (
        <div className="settings-grid admin-settings-grid">
          <article className="setting-card admin-card" ref={secretPanelRef}>
            <span>{isEnglish ? "Admin security" : "Bảo mật quản trị"}</span>
            <strong>{isEnglish ? "Configuration status" : "Trạng thái cấu hình"}</strong>
            <p>
              {isEnglish
                ? "Check whether protected server settings are configured. Raw values are never shown."
                : "Kiểm tra các thiết lập máy chủ được bảo vệ đã cấu hình hay chưa. Giá trị gốc không bao giờ được hiển thị."}
            </p>
            <button className="secondary-button" onClick={loadSecretStatus} disabled={secretLoading}>
              <ShieldCheck size={16} />
              {secretLoading
                ? isEnglish ? "Checking..." : "Đang kiểm tra..."
                : secretStatus
                  ? isEnglish ? "Hide status" : "Ẩn trạng thái"
                  : isEnglish ? "Check status" : "Kiểm tra trạng thái"}
            </button>
            {secretError ? <div className="notice error">{secretError}</div> : null}
            {secretStatus?.secrets ? (
              <div className="secret-status-list">
                {Object.entries(secretStatus.secrets).map(([key, value]) => (
                  <div key={key} className="secret-status-row">
                    <span>{key}</span>
                    <strong>
                      {value.configured
                        ? value.preview || `${value.count} ${isEnglish ? "items" : "mục"}`
                        : isEnglish ? "not configured" : "chưa cấu hình"}
                    </strong>
                  </div>
                ))}
              </div>
            ) : null}
          </article>
        </div>
      ) : null}

      {auth.isAdmin && showBackend ? (
        <div className="backend-tools">
          <SystemFlow language={language} />
          <HealthDashboard
            health={health}
            loading={healthLoading}
            error={healthError}
            refresh={refreshHealth}
            language={language}
          />
        </div>
      ) : null}
    </section>
  );
}
