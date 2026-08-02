export const DEFAULT_LANGUAGE = "en";
export const LANGUAGE_STORAGE_KEY = "finvista-language";

export function getStoredLanguage() {
  return localStorage.getItem(LANGUAGE_STORAGE_KEY) || DEFAULT_LANGUAGE;
}

const loginMessages = {
  en: {
    intro: "Sign in with your private beta account to access your workspace.",
    username: "Username or email",
    password: "Password",
    action: "Sign in",
    signingIn: "Signing in...",
    help: "Use the username and password provided by the Finvista administrator."
  },
  vi: {
    intro: "Dang nhap bang tai khoan private beta de truy cap workspace.",
    username: "Username hoac email",
    password: "Mat khau",
    action: "Dang nhap",
    signingIn: "Dang dang nhap...",
    help: "Dung username va mat khau duoc quan tri vien Finvista cung cap."
  }
};

export function getLoginMessages(language) {
  return loginMessages[language] || loginMessages.en;
}
