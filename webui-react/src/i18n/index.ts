import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import de from "../../../webui/i18n/de.json";
import en from "../../../webui/i18n/en.json";
import es from "../../../webui/i18n/es.json";
import id from "../../../webui/i18n/id.json";
import pt from "../../../webui/i18n/pt.json";
import ru from "../../../webui/i18n/ru.json";
import tr from "../../../webui/i18n/tr.json";
import vi from "../../../webui/i18n/vi.json";

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
