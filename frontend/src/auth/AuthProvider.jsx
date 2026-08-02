import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { API_BASE_URL, setAuthTokenProvider } from "../api.js";
import { getStoredLanguage } from "../i18n/index.js";

const AuthContext = createContext(null);
const TOKEN_STORAGE_KEY = "finvista-access-token";

// Đọc từ .env – nếu không set hoặc set "false" thì app chạy không cần login
const AUTH_ENABLED = import.meta.env.VITE_AUTH_ENABLED === "true";

function isEnglishLanguage() {
  return getStoredLanguage() === "en";
}

function getLoginErrorMessage(error) {
  const isEnglish = isEnglishLanguage();
  return (
    error?.message ||
    (isEnglish
      ? "Could not sign in. Check your username and password."
      : "Không đăng nhập được. Hãy kiểm tra username và mật khẩu.")
  );
}

function normalizeProfile(payload) {
  const user = payload?.user || payload || {};
  const email = user.email || user.username || payload?.email || payload?.username || "";
  return {
    uid: user.id || user.uid || `basic:${email}`,
    email,
    name: user.name || email.split("@")[0] || "Finvista user",
    picture: user.picture || "",
    role: user.role || payload?.role || "tester",
    permissions: user.permissions || payload?.permissions || []
  };
}

async function parseJsonResponse(response) {
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(payload?.detail || payload?.message || `HTTP ${response.status}`);
  }
  return payload;
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY) || "");
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [profileLoading, setProfileLoading] = useState(false);
  const [signInLoading, setSignInLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    // No-auth mode: set a guest profile và skip login flow hoàn toàn
    if (!AUTH_ENABLED) {
      setAuthTokenProvider(null);
      setProfile({ uid: "guest", email: "", name: "Guest", picture: "", role: "guest", permissions: [] });
      setLoading(false);
      return;
    }

    if (!token) {
      setAuthTokenProvider(null);
      setProfile(null);
      setLoading(false);
      return;
    }

    setAuthTokenProvider(() => token);
    loadProfile(token).finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function loadProfile(activeToken = token) {
    if (!activeToken) return null;
    setProfileLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: {
          Authorization: `Bearer ${activeToken}`
        }
      });
      const payload = await parseJsonResponse(response);
      const nextProfile = normalizeProfile(payload);
      setProfile(nextProfile);
      return nextProfile;
    } catch (err) {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      setToken("");
      setProfile(null);
      setAuthTokenProvider(null);
      setError(getLoginErrorMessage(err));
      return null;
    } finally {
      setProfileLoading(false);
    }
  }

  async function signIn({ username, password }) {
    setError("");
    setSignInLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append("username", username);
      formData.append("password", password);

      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded"
        },
        body: formData.toString()
      });
      const payload = await parseJsonResponse(response);
      const nextToken = payload?.access_token || "";
      if (!nextToken) {
        throw new Error(
          isEnglishLanguage()
            ? "Login response did not include a token."
            : "Phản hồi đăng nhập không có token."
        );
      }
      localStorage.setItem(TOKEN_STORAGE_KEY, nextToken);
      setAuthTokenProvider(() => nextToken);
      setToken(nextToken);
      setProfile(normalizeProfile(payload));
    } catch (err) {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      setToken("");
      setProfile(null);
      setAuthTokenProvider(null);
      setError(getLoginErrorMessage(err));
    } finally {
      setSignInLoading(false);
      setLoading(false);
    }
  }

  async function signOut() {
    // No-auth mode: không thực sự signout
    if (!AUTH_ENABLED) return;
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken("");
    setProfile(null);
    setError("");
    setAuthTokenProvider(null);
  }

  const value = useMemo(
    () => ({
      authEnabled: AUTH_ENABLED,
      token,
      profile,
      role: profile?.role || "",
      isAdmin: profile?.role === "admin",
      loading,
      profileLoading,
      signInLoading,
      error,
      signIn,
      signOut,
      refreshProfile: () => loadProfile()
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [token, profile, loading, profileLoading, signInLoading, error]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
