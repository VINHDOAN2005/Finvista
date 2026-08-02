import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProfileMenu } from "../components/layout/ProfileMenu.jsx";


function buildAuth() {
  return {
    authEnabled: true,
    profile: { email: "tester@example.com", name: "Tester", role: "tester" },
    isAdmin: false,
    profileLoading: false,
    refreshProfile: vi.fn(),
    signOut: vi.fn()
  };
}


describe("ProfileMenu", () => {
  it("closes when the user clicks outside", () => {
    render(<ProfileMenu auth={buildAuth()} language="en" page="intro" setPage={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Open profile menu" }));
    expect(screen.getByRole("dialog", { name: "Profile" })).toBeInTheDocument();

    fireEvent.pointerDown(document.body);
    expect(screen.queryByRole("dialog", { name: "Profile" })).not.toBeInTheDocument();
  });

  it("opens settings and closes the popup", () => {
    const setPage = vi.fn();
    render(<ProfileMenu auth={buildAuth()} language="en" page="intro" setPage={setPage} />);
    fireEvent.click(screen.getByRole("button", { name: "Open profile menu" }));
    fireEvent.click(screen.getByText("Settings"));

    expect(setPage).toHaveBeenCalledWith("settings");
    expect(screen.queryByRole("dialog", { name: "Profile" })).not.toBeInTheDocument();
  });
});
