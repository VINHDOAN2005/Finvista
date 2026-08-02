import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CreditHealthPage } from "../features/credit-health/CreditHealthPage.jsx";


vi.mock("../api.js", () => ({
  getCreditHealth: vi.fn(async () => ({
    ticker: "HPG",
    reported_year: 2025,
    credit_metrics: {
      altman_z_score: 3.53,
      risk_zone: "SAFE (GREEN)",
      is_ml_distressed: false,
      bankruptcy_probability: 0.151,
      status_description: "Excellent corporate credit score. Stable financial standing."
    },
    financial_ratios: {
      leverage_debt_ratio: 0.4912,
      liquidity_current_ratio: 1.1006,
      roa: 0.0602,
      roe: 0.1182,
      ebit_to_assets: 0.0694,
      icr: 4.2231,
      ocf_to_total_debt: 0.1371
    },
    distress_scores: {
      altman_zone: "SAFE (GREEN)",
      springate_s_score: 1.2345,
      springate_distressed: false,
      zmijewski_x_score: -1.4567,
      zmijewski_distressed: false
    }
  }))
}));


describe("Credit health page", () => {
  it("localizes the risk zone and renders extended distress indicators in Vietnamese", async () => {
    render(<CreditHealthPage language="vi" />);

    expect(await screen.findByText("HPG")).toBeInTheDocument();
    expect(screen.getAllByText("AN TOÀN (XANH)").length).toBeGreaterThan(0);
    expect(screen.queryByText("SAFE (GREEN)")).not.toBeInTheDocument();
    expect(screen.getByText("ICR")).toBeInTheDocument();
    expect(screen.getByText("Springate S-score")).toBeInTheDocument();
    expect(screen.getByText("Zmijewski X-score")).toBeInTheDocument();
    expect(screen.getByText("ML cảnh báo")).toBeInTheDocument();
  });
});
