import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MarketPage } from "../features/market/MarketPage.jsx";


const apiMocks = vi.hoisted(() => ({
  getMarketMetadata: vi.fn(async () => ({
    vn30_symbols: ["MBB", "HPG"]
  })),
  getOpportunities: vi.fn(async () => ({
    recommendations: [
      {
        warrant_symbol: "CMBB2601",
        underlying_symbol: "MBB",
        is_vn30_underlying: true,
        days_to_maturity: 100,
        recommendation_signal: "BUY",
        volume: 100000,
        market_price: 1200,
        composite_g_score: 80,
        price_change_pct: 1.2
      }
    ]
  })),
  getUnderlyingMarket: vi.fn(async () => ({
  status: "success",
  underlying_count: 2,
  sector_count: 2,
  breadth: { advancing: 1, declining: 1, unchanged: 0 },
  data_sources: { quotes: "vnstock / KBS price_board", news: "vnstock / KBS Company.news" },
  news_coverage: { symbols_with_news: 1, active_symbols: 2 },
  sectors: [
    {
      industry: "Banks",
      underlying_count: 1,
      cw_count: 3,
      average_change_pct: 1.2,
      stock_traded_value: 1000000000,
      cw_traded_value: 80000000,
      advancing: 1,
      declining: 0,
      unchanged: 0
    },
    {
      industry: "Steel",
      underlying_count: 1,
      cw_count: 2,
      average_change_pct: -0.8,
      stock_traded_value: 700000000,
      cw_traded_value: 40000000,
      advancing: 0,
      declining: 1,
      unchanged: 0
    }
  ],
  underlyings: [
    {
      symbol: "MBB",
      company_name: "Ngân hàng TMCP Quân đội",
      company_name_en: "Military Commercial Joint Stock Bank",
      industry: "Banks",
      price: 28000,
      change_pct: 1.2,
      stock_volume: 2000000,
      cw_count: 3,
      buy_count: 2,
      skip_count: 1,
      neutral_count: 0,
      cw_traded_value: 80000000,
      best_warrant_symbol: "CMBB2601"
    },
    {
      symbol: "HPG",
      company_name: "CTCP Tập đoàn Hòa Phát",
      company_name_en: "Hoa Phat Group",
      industry: "Steel",
      price: 26000,
      change_pct: -0.8,
      stock_volume: 1500000,
      cw_count: 2,
      buy_count: 0,
      skip_count: 1,
      neutral_count: 1,
      cw_traded_value: 40000000,
      best_warrant_symbol: "CHPG2601"
    },
    {
      symbol: "VIB",
      company_name: "Ngân hàng TMCP Quốc tế Việt Nam",
      company_name_en: "Vietnam International Commercial Joint Stock Bank",
      industry: "Banks",
      price: 20000,
      change_pct: 0.4,
      stock_volume: 1000000,
      cw_count: 1,
      buy_count: 1,
      skip_count: 0,
      neutral_count: 0,
      cw_traded_value: 10000000,
      best_warrant_symbol: "CVIB2601"
    },
    {
      symbol: "VHM",
      company_name: "CTCP Vinhomes Việt Nam",
      company_name_en: "Vinhomes Joint Stock Company",
      industry: "Real estate",
      price: 50000,
      change_pct: 0.2,
      stock_volume: 800000,
      cw_count: 1,
      buy_count: 1,
      skip_count: 0,
      neutral_count: 0,
      cw_traded_value: 9000000,
      best_warrant_symbol: "CVHM2601"
    }
  ],
  news: [
    {
      symbol: "MBB",
      title: "MBB company update",
      source: "KBS",
      published_at: "2026-06-04",
      url: "https://vietstock.vn/mbb-update.htm"
    },
    {
      symbol: "HPG",
      title: "HPG company update",
      source: "KBS",
      published_at: "2026-06-03",
      url: "https://vietstock.vn/hpg-update.htm"
    }
  ],
  live_errors: []
  }))
}));

vi.mock("../api.js", () => apiMocks);


describe("Underlying market page", () => {
  it("renders only CW-linked stocks and opens the selected best warrant", async () => {
    const setPage = vi.fn();
    const setSelectedSymbol = vi.fn();
    render(<MarketPage language="en" setPage={setPage} setSelectedSymbol={setSelectedSymbol} />);

    expect(await screen.findByRole("heading", { name: "Market Overview" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Covered warrant pulse" })).toBeInTheDocument();
    expect(screen.getAllByText("MBB")[0]).toBeInTheDocument();
    expect(screen.getAllByText("HPG")[0]).toBeInTheDocument();

    fireEvent.click(screen.getByRole("cell", { name: "MBB" }));
    expect(screen.getByText("HPG company update")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "MBB company update" })).toHaveAttribute(
      "href",
      "https://vietstock.vn/mbb-update.htm"
    );
    fireEvent.click(screen.getByRole("button", { name: "Open CW detail" }));
    expect(setSelectedSymbol).toHaveBeenCalledWith("CMBB2601");
    expect(setPage).toHaveBeenCalledWith("detail");
  });

  it("uses Vietnamese labels and requests live refresh on demand", async () => {
    render(<MarketPage language="vi" setPage={vi.fn()} setSelectedSymbol={vi.fn()} />);
    expect(await screen.findByRole("heading", { name: "Tổng quan thị trường" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Làm mới live" }));
    await waitFor(() => {
      expect(apiMocks.getUnderlyingMarket).toHaveBeenCalledWith({
        forceRefresh: true,
        newsLimit: 30,
        language: "vi"
      });
    });
  });

  it("toggles a selected news symbol off on the second click", async () => {
    render(<MarketPage language="en" setPage={vi.fn()} setSelectedSymbol={vi.fn()} />);
    const newsSymbol = await screen.findByRole("button", { name: "MBB" });

    fireEvent.click(newsSymbol);
    expect(screen.getByRole("button", { name: "Open CW detail" })).toBeInTheDocument();

    fireEvent.click(newsSymbol);
    expect(screen.queryByRole("button", { name: "Open CW detail" })).not.toBeInTheDocument();
  });

  it("shows custom CW pulse hover values for signal and traded-value charts", async () => {
    const { container } = render(<MarketPage language="en" setPage={vi.fn()} setSelectedSymbol={vi.fn()} />);
    expect(await screen.findByRole("heading", { name: "Covered warrant pulse" })).toBeInTheDocument();

    fireEvent.pointerEnter(container.querySelector(".cw-signal-segment"), {
      clientX: 120,
      clientY: 120
    });
    expect(screen.getByText("1 CW · 100.0%")).toBeInTheDocument();

    fireEvent.pointerEnter(container.querySelector(".flow-track"), {
      clientX: 220,
      clientY: 180
    });
    expect(screen.getByText(/120\.000\.000 VND/)).toBeInTheDocument();
  });

  it("suggests and filters ticker prefixes before matching company names", async () => {
    render(<MarketPage language="en" setPage={vi.fn()} setSelectedSymbol={vi.fn()} />);
    const search = await screen.findByPlaceholderText("Search symbol or company");

    fireEvent.change(search, { target: { value: "VI" } });

    expect(screen.getByRole("cell", { name: "VIB" })).toBeInTheDocument();
    expect(screen.queryByRole("cell", { name: "VHM" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Ticker suggestions")).toBeInTheDocument();
    expect(screen.queryByText("Ngân hàng TMCP Quốc tế Việt Nam")).not.toBeInTheDocument();
  });
});
