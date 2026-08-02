import React from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "../auth/AuthProvider.jsx";

function wrapper({ children }) {
  return <AuthProvider>{children}</AuthProvider>;
}

function mockFetchResponse(payload, ok = true, status = 200) {
  return {
    ok,
    status,
    json: vi.fn().mockResolvedValue(payload)
  };
}

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  it("signs in with username and password and stores the access token", async () => {
    fetch
      .mockResolvedValueOnce(
        mockFetchResponse({
          access_token: "jwt-token",
          username: "tester@example.com",
          email: "tester@example.com",
          role: "tester",
          permissions: ["view_dashboard"]
        })
      )
      .mockResolvedValueOnce(
        mockFetchResponse({
          email: "tester@example.com",
          role: "tester",
          permissions: ["view_dashboard"]
        })
      );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.signIn({
        username: "tester@example.com",
        password: "secret"
      });
    });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/login"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          username: "tester@example.com",
          password: "secret"
        })
      })
    );
    expect(localStorage.getItem("finvista-access-token")).toBe("jwt-token");
    expect(result.current.profile.email).toBe("tester@example.com");
  });

  it("loads the saved session from /api/auth/me", async () => {
    localStorage.setItem("finvista-access-token", "jwt-token");
    fetch.mockResolvedValueOnce(
      mockFetchResponse({
        email: "tester@example.com",
        role: "tester",
        permissions: ["view_dashboard"]
      })
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/auth/me"),
        expect.objectContaining({
          headers: {
            Authorization: "Bearer jwt-token"
          }
        })
      );
    });
    await waitFor(() => {
      expect(result.current.profile.email).toBe("tester@example.com");
    });
  });
});
