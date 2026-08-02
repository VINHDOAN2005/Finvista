import React, { useState } from "react";
import { LogIn } from "lucide-react";
import { getLoginMessages } from "../i18n/index.js";

export function LoginPage({ auth, language = "en", colorMode = "light" }) {
  const messages = getLoginMessages(language);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  async function submitLogin(event) {
    event.preventDefault();
    await auth.signIn({ username, password });
  }

  return (
    <main className={`login-shell color-${colorMode}`}>
      <div className="login-atmosphere" aria-hidden="true">
        <span className="login-grid-plane" />
        <span className="login-flow-line login-flow-one" />
        <span className="login-flow-line login-flow-two" />
        <span className="login-orbit-ring login-orbit-one" />
        <span className="login-orbit-ring login-orbit-two" />
        <span className="login-market-chip login-chip-one">VN30</span>
        <span className="login-market-chip login-chip-two">CW</span>
        <span className="login-market-chip login-chip-three">Z</span>
      </div>

      <section className="login-panel">
        <div className="brand-mark">F</div>
        <div>
          <p className="eyebrow">Private beta</p>
          <h1>Finvista</h1>
          <p className="intro-text">{messages.intro}</p>
        </div>

        {auth.error ? <div className="notice error">{auth.error}</div> : null}

        <form className="login-form" onSubmit={submitLogin}>
          <label>
            <span>{messages.username}</span>
            <input
              autoComplete="username"
              name="username"
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </label>
          <label>
            <span>{messages.password}</span>
            <input
              autoComplete="current-password"
              name="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          <button
            className="primary-button login-button"
            type="submit"
            disabled={auth.loading || auth.profileLoading || auth.signInLoading}
          >
            <LogIn size={18} />
            {auth.signInLoading ? messages.signingIn : messages.action}
          </button>
        </form>

        <p className="helper-text">{messages.help}</p>
      </section>
    </main>
  );
}
