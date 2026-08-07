import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import de from "./locales/de.json";
import en from "./locales/en.json";
import es from "./locales/es.json";
import id from "./locales/id.json";
import pt from "./locales/pt.json";
import ru from "./locales/ru.json";
import tr from "./locales/tr.json";
import vi from "./locales/vi.json";

type Locale = { Language: string; Translation: Record<string, string> };
export const localeFiles: Record<string, Locale> = { de, en, es, id, pt, ru, tr, vi };
const resources = Object.fromEntries(Object.entries(localeFiles).map(([code, locale]) => [code, { translation: locale.Translation }]));

void i18n.use(initReactI18next).init({
  resources,
  lng: "en",
  fallbackLng: "en",
  keySeparator: false,
  nsSeparator: false,
  returnEmptyString: false,
  interpolation: { escapeValue: false, prefix: "{", suffix: "}" },
});

export default i18n;
