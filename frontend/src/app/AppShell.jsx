import React, { useEffect, useState } from "react";

import { getHealth } from "../api.js";
import { useAuth } from "../auth/AuthProvider.jsx";
import { ProfileMenu } from "../components/layout/ProfileMenu.jsx";
import { CreditHealthPage } from "../features/credit-health/CreditHealthPage.jsx";
import { HomePage } from "../features/home/HomePage.jsx";
import { MarketPage } from "../features/market/MarketPage.jsx";
import { OpportunitiesPage } from "../features/opportunities/OpportunitiesPage.jsx";
import { SettingsPage } from "../features/settings/SettingsPage.jsx";
import { WarrantDetailPage } from "../features/warrant-detail/WarrantDetailPage.jsx";
import { PortfolioPage } from "../features/portfolio/PortfolioPage.jsx";
import { AIChatWidget } from "../components/chat/AIChatWidget.jsx";
import { LoginPage } from "../pages/LoginPage.jsx";
import { NAV_ITEMS } from "./config.js";
import { usePreferences } from "./usePreferences.js";

export function AppShell() {
  const auth = useAuth();
  const [page, setPage] = useState("intro");
  const { language, setLanguage, preferences, setPreferences } = usePreferences();
  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthError, setHealthError] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState("");

  async function refreshHealth() {
    setHealthLoading(true);
    setHealthError("");
    try {
      const result = await getHealth();
      setHealth(result);
    } catch (err) {
      setHealthError(err.message);
    } finally {
      setHealthLoading(false);
    }
  }

  useEffect(() => {
    refreshHealth();
  }, []);

  const currentNavItems = NAV_ITEMS[language] || NAV_ITEMS.en;

  if (auth.authEnabled && auth.loading) {
    return (
      <main className={`login-shell color-${preferences.colorMode}`}>
        <section className="login-panel">
          <div className="brand-mark">F</div>
          <p className="notice loading" style={{ marginTop: "1.25rem" }}>
            {language === "en" ? "Checking your sign-in session…" : "Đang kiểm tra phiên đăng nhập…"}
          </p>
        </section>
      </main>
    );
  }

  if (auth.authEnabled && !auth.profile) {
    return <LoginPage auth={auth} language={language} colorMode={preferences.colorMode} />;
  }

  return (
    <div
      className={[
        "app-shell",
        `theme-${preferences.theme}`,
        `color-${preferences.colorMode}`,
        `density-${preferences.density}`,
        preferences.smoothMotion ? "motion-smooth" : "motion-static",
        preferences.tableHints ? "hints-on" : "hints-off"
      ].join(" ")}
    >
      <header className="topbar">
        <button className="brand" onClick={() => setPage("intro")}>
          <span className="brand-mark">F</span>
          <span>
            <strong>Finvista</strong>
            <small>{language === "en" ? "Quant analytics" : "Phân tích định lượng"}</small>
          </span>
        </button>

        <div className="topbar-actions">
          {page !== "intro" ? (
            <nav aria-label="Main navigation">
              {currentNavItems.map((item) => (
                <button
                  key={item.id}
                  className={page === item.id ? "active" : ""}
                  onClick={() => setPage(item.id)}
                >
                  {item.label}
                </button>
              ))}
            </nav>
          ) : null}
          <ProfileMenu
            auth={auth}
            language={language}
            page={page}
            setPage={setPage}
          />
        </div>
      </header>

      <main>
        {/* key={page} triggers CSS re-animation on every page switch for smooth transitions */}
        <div key={page} className="page-enter">
          {page === "intro" ? (
            <HomePage
              setPage={setPage}
              setSelectedSymbol={setSelectedSymbol}
              health={health}
              healthLoading={healthLoading}
              healthError={healthError}
              language={language}
            />
          ) : null}

          {page === "cw" ? (
            <OpportunitiesPage
              setPage={setPage}
              setSelectedSymbol={setSelectedSymbol}
              language={language}
            />
          ) : null}

          {page === "market" ? (
            <MarketPage
              setPage={setPage}
              setSelectedSymbol={setSelectedSymbol}
              language={language}
            />
          ) : null}

          {page === "credit" ? <CreditHealthPage language={language} /> : null}

          {page === "detail" ? (
            <WarrantDetailPage
              selectedSymbol={selectedSymbol}
              setSelectedSymbol={setSelectedSymbol}
              language={language}
              preferences={preferences}
            />
          ) : null}

          {page === "settings" ? (
            <SettingsPage
              health={health}
              healthLoading={healthLoading}
              healthError={healthError}
              refreshHealth={refreshHealth}
              language={language}
              setLanguage={setLanguage}
              preferences={preferences}
              setPreferences={setPreferences}
            />
          ) : null}

          {page === "portfolio" ? (
            <PortfolioPage 
              language={language} 
              prepopulatedSymbol={selectedSymbol}
              clearPrepopulatedSymbol={() => setSelectedSymbol("")}
            />
          ) : null}
        </div>

        <footer>
          {language === "en"
            ? "For analytics only, not investment advice."
            : "Chỉ dùng cho mục đích phân tích, không phải khuyến nghị đầu tư."}
        </footer>
      </main>

      <AIChatWidget language={language} />
    </div>
  );
}
