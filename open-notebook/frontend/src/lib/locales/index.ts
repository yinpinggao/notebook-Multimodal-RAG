import { zhCN } from './zh-CN';
import { enUS } from './en-US';
import { zhTW } from './zh-TW';
import { ptBR } from './pt-BR';
import { jaJP } from './ja-JP';
import { itIT } from './it-IT';
import { frFR } from './fr-FR';
import { ruRU } from './ru-RU';
import { bnIN } from './bn-IN';

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const mergeLocale = <T extends Record<string, unknown>>(
  base: T,
  overrides: Record<string, unknown>,
): T => {
  const merged: Record<string, unknown> = { ...base };

  for (const [key, value] of Object.entries(overrides)) {
    if (value === undefined) continue;

    const current = merged[key];
    merged[key] = isRecord(current) && isRecord(value)
      ? mergeLocale(current, value)
      : value;
  }

  return merged as T;
};

export const resources = {
  'zh-CN': { translation: zhCN },
  'en-US': { translation: enUS },
  'zh-TW': { translation: mergeLocale(enUS, zhTW) },
  'pt-BR': { translation: mergeLocale(enUS, ptBR) },
  'ja-JP': { translation: mergeLocale(enUS, jaJP) },
  'it-IT': { translation: mergeLocale(enUS, itIT) },
  'fr-FR': { translation: mergeLocale(enUS, frFR) },
  'ru-RU': { translation: mergeLocale(enUS, ruRU) },
  'bn-IN': { translation: mergeLocale(enUS, bnIN) },
} as const;

export type TranslationKeys = typeof enUS;

export type LanguageCode = 'zh-CN' | 'en-US' | 'zh-TW' | 'pt-BR' | 'ja-JP' | 'it-IT' | 'fr-FR' | 'ru-RU' | 'bn-IN';

export type Language = {
  code: LanguageCode;
  label: string;
};

export const languages: Language[] = [
  { code: 'en-US', label: 'English' },
  { code: 'zh-CN', label: '简体中文' },
  { code: 'zh-TW', label: '繁體中文' },
  { code: 'pt-BR', label: 'Português' },
  { code: 'ja-JP', label: '日本語' },
  { code: 'it-IT', label: 'Italiano' },
  { code: 'fr-FR', label: 'Français' },
  { code: 'ru-RU', label: 'Русский' },
  { code: 'bn-IN', label: 'বাংলা' },
];

export { zhCN, enUS, zhTW, ptBR, jaJP, itIT, frFR, ruRU, bnIN };
