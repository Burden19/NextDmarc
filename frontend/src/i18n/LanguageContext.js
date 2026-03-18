import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { messages } from "i18n/messages";

const LANGUAGE_STORAGE_KEY = "nextdmarc_lang";
const supportedLanguages = ["en", "fr"];

const LanguageContext = createContext({
  language: "en",
  setLanguage: () => {},
  t: (_key, fallback = "") => fallback
});

function getByPath(source, key) {
  return key.split(".").reduce((value, part) => {
    if (!value || typeof value !== "object") {
      return undefined;
    }
    return value[part];
  }, source);
}

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState("en");

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const storedLanguage = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    if (storedLanguage && supportedLanguages.includes(storedLanguage)) {
      setLanguageState(storedLanguage);
    }
  }, []);

  const setLanguage = (nextLanguage) => {
    if (!supportedLanguages.includes(nextLanguage)) {
      return;
    }

    setLanguageState(nextLanguage);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLanguage);
    }
  };

  const value = useMemo(() => {
    const t = (key, fallback = "") => {
      const localizedValue = getByPath(messages[language], key);
      if (typeof localizedValue === "string") {
        return localizedValue;
      }

      const englishValue = getByPath(messages.en, key);
      if (typeof englishValue === "string") {
        return englishValue;
      }

      return fallback;
    };

    return { language, setLanguage, t };
  }, [language]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  return useContext(LanguageContext);
}

