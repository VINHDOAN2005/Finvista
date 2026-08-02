import { useEffect, useState } from "react";

import { DEFAULT_PREFERENCES, STORAGE_KEYS } from "./config.js";


export function usePreferences() {
  const [language, setLanguage] = useState(
    () => localStorage.getItem(STORAGE_KEYS.language) || "en"
  );
  const [preferences, setPreferences] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.preferences);
    if (!saved) return DEFAULT_PREFERENCES;
    try {
      return { ...DEFAULT_PREFERENCES, ...JSON.parse(saved) };
    } catch {
      return DEFAULT_PREFERENCES;
    }
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.language, language);
  }, [language]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.preferences, JSON.stringify(preferences));
  }, [preferences]);

  return { language, setLanguage, preferences, setPreferences };
}
