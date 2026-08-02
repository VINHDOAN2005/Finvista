import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DEFAULT_PREFERENCES } from "../app/config.js";
import { SettingsPage } from "../features/settings/SettingsPage.jsx";


const authState = vi.hoisted(() => ({
  current: { isAdmin: false }
}));

vi.mock("../auth/AuthProvider.jsx", () => ({
  useAuth: () => authState.current
}));

vi.mock("../api.js", () => ({
  getAdminSecretStatus: vi.fn(async () => ({
    secrets: {
      jwt_secret_key: { configured: true, preview: "...cret" }
    }
  }))
}));

function renderSettings() {
  return render(
    <SettingsPage
      health={null}
      healthLoading={false}
      healthError=""
      refreshHealth={vi.fn()}
      language="en"
      setLanguage={vi.fn()}
      preferences={DEFAULT_PREFERENCES}
      setPreferences={vi.fn()}
    />
  );
}


describe("Settings role visibility", () => {
  it("hides administration tools from testers", () => {
    authState.current = { isAdmin: false };
    renderSettings();
    expect(screen.queryByText("Administration")).not.toBeInTheDocument();
    expect(screen.queryByText("Check status")).not.toBeInTheDocument();
  });

  it("shows administration tools to admins", () => {
    authState.current = { isAdmin: true };
    renderSettings();
    expect(screen.getByText("Administration")).toBeInTheDocument();
    expect(screen.getByText("Check status")).toBeInTheDocument();
  });

  it("closes secret status when the admin clicks outside", async () => {
    authState.current = { isAdmin: true };
    renderSettings();
    fireEvent.click(screen.getByText("Check status"));
    expect(await screen.findByText("jwt_secret_key")).toBeInTheDocument();

    fireEvent.pointerDown(document.body);
    expect(screen.queryByText("jwt_secret_key")).not.toBeInTheDocument();
  });
});
