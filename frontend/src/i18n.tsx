import { createContext, useContext } from "react";

// UI texts come from the backend (/api/meta), so the language is set once in backend/.env (APP_LANGUAGE).
export type Translate = (key: string, values?: Record<string, string | number>) => string;

export function makeTranslate(messages: Record<string, string>): Translate {
  return (key, values) =>
    (messages[key] ?? key).replace(/\{(\w+)\}/g, (match, name) =>
      values && name in values ? String(values[name]) : match,
    );
}

const I18nContext = createContext<Translate>((key) => key);

export const I18nProvider = I18nContext.Provider;

export function useT(): Translate {
  return useContext(I18nContext);
}
