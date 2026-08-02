import React, { useEffect, useRef, useState } from "react";
import { LogOut, RefreshCw, ShieldCheck } from "lucide-react";


function GearIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false">
      <path
        d="M12 8.25a3.75 3.75 0 1 0 0 7.5 3.75 3.75 0 0 0 0-7.5Zm0 1.8a1.95 1.95 0 1 1 0 3.9 1.95 1.95 0 0 1 0-3.9Z"
        fill="currentColor"
      />
      <path
        d="M19.43 13.2a7.7 7.7 0 0 0 .05-1.2 7.7 7.7 0 0 0-.05-1.2l1.55-1.2a.8.8 0 0 0 .2-.98l-1.47-2.55a.8.8 0 0 0-.93-.37l-1.83.74a7.9 7.9 0 0 0-2.07-1.2l-.27-1.95A.8.8 0 0 0 13.82 2h-2.94a.8.8 0 0 0-.79.69l-.27 1.95a7.9 7.9 0 0 0-2.07 1.2l-1.83-.74a.8.8 0 0 0-.93.37L3.52 8.02a.8.8 0 0 0 .2.98l1.55 1.2a7.7 7.7 0 0 0-.05 1.2 7.7 7.7 0 0 0 .05 1.2l-1.55 1.2a.8.8 0 0 0-.2.98l1.47 2.55a.8.8 0 0 0 .93.37l1.83-.74a7.9 7.9 0 0 0 2.07 1.2l.27 1.95a.8.8 0 0 0 .79.69h2.94a.8.8 0 0 0 .79-.69l.27-1.95a7.9 7.9 0 0 0 2.07-1.2l1.83.74a.8.8 0 0 0 .93-.37l1.47-2.55a.8.8 0 0 0-.2-.98l-1.55-1.2Zm-2.05-.5.04-.7-.04-.7 1.43-1.1-.71-1.23-1.68.68-.58-.43a6 6 0 0 0-1.58-.92l-.67-.27-.25-1.8h-1.42l-.25 1.8-.67.27a6 6 0 0 0-1.58.92l-.58.43-1.68-.68-.71 1.23 1.43 1.1-.04.7.04.7-1.43 1.1.71 1.23 1.68-.68.58.43a6 6 0 0 0 1.58.92l.67.27.25 1.8h1.42l.25-1.8.67-.27a6 6 0 0 0 1.58-.92l.58-.43 1.68.68.71-1.23-1.43-1.1Z"
        fill="currentColor"
      />
    </svg>
  );
}


export function ProfileMenu({ auth, language, page, setPage }) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);
  const isEnglish = language === "en";
  const avatarUrl = auth.profile?.picture || "";
  const accountEmail = auth.profile?.email || (isEnglish ? "Local mode" : "Chế độ local");
  const accountRole = auth.profile?.role || "local";
  const displayName =
    auth.profile?.name ||
    auth.profile?.email?.split("@")[0] ||
    "Finvista user";
  const avatarInitial = displayName.trim().charAt(0).toUpperCase() || "F";

  useEffect(() => {
    function closeOnOutsideClick(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) setIsOpen(false);
    }
    function closeOnEscape(event) {
      if (event.key === "Escape") setIsOpen(false);
    }
    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);

  async function signOut() {
    setIsOpen(false);
    await auth.signOut();
  }

  return (
    <div className="profile-menu-wrap" ref={menuRef}>
      <button
        className={`profile-trigger ${isOpen || page === "settings" ? "active" : ""}`}
        onClick={() => setIsOpen((value) => !value)}
        aria-label={isEnglish ? "Open profile menu" : "Mở menu hồ sơ"}
        aria-expanded={isOpen}
      >
        {avatarUrl ? <img src={avatarUrl} alt="" referrerPolicy="no-referrer" /> : <span>{avatarInitial}</span>}
        <i className={auth.isAdmin ? "admin" : "tester"} />
      </button>

      {isOpen ? (
        <>
          <button
            className="profile-menu-backdrop"
            onClick={() => setIsOpen(false)}
            aria-label={isEnglish ? "Close profile menu" : "Đóng menu hồ sơ"}
          />
          <div className="profile-popover" role="dialog" aria-label={isEnglish ? "Profile" : "Hồ sơ"}>
            <div className="profile-popover-head">
              <div className="profile-avatar-large">
                {avatarUrl ? <img src={avatarUrl} alt="" referrerPolicy="no-referrer" /> : <span>{avatarInitial}</span>}
              </div>
              <div className="profile-identity">
                <strong>{displayName}</strong>
                <span>{accountEmail}</span>
                <small className={auth.isAdmin ? "admin" : "tester"}>
                  <ShieldCheck size={13} />
                  {accountRole}
                </small>
              </div>
            </div>

            <div className="profile-menu-actions">
              <button
                className={page === "settings" ? "active" : ""}
                onClick={() => {
                  setPage("settings");
                  setIsOpen(false);
                }}
              >
                <GearIcon />
                <span>
                  <strong>{isEnglish ? "Settings" : "Cài đặt"}</strong>
                  <small>
                    {auth.isAdmin
                      ? isEnglish ? "Interface and admin tools" : "Giao diện và công cụ quản trị"
                      : isEnglish ? "Language and appearance" : "Ngôn ngữ và giao diện"}
                  </small>
                </span>
              </button>
              {auth.authEnabled ? (
                <button onClick={auth.refreshProfile} disabled={auth.profileLoading}>
                  <RefreshCw size={17} />
                  <span>
                    <strong>{isEnglish ? "Refresh profile" : "Làm mới hồ sơ"}</strong>
                    <small>
                      {auth.profileLoading
                        ? isEnglish ? "Checking access..." : "Đang kiểm tra quyền..."
                        : isEnglish ? "Recheck email and role" : "Kiểm tra lại email và quyền"}
                    </small>
                  </span>
                </button>
              ) : null}
            </div>

            {auth.authEnabled ? (
              <button className="profile-signout" onClick={signOut}>
                <LogOut size={16} />
                {isEnglish ? "Sign out" : "Đăng xuất"}
              </button>
            ) : null}
          </div>
        </>
      ) : null}
    </div>
  );
}
