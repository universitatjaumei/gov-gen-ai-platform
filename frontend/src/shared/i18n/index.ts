import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import esCommon from './locales/es/common.json'
import esChat from './locales/es/chat.json'
import esAdmin from './locales/es/admin.json'
import caCommon from './locales/ca/common.json'
import caChat from './locales/ca/chat.json'
import caAdmin from './locales/ca/admin.json'
import enCommon from './locales/en/common.json'
import enChat from './locales/en/chat.json'
import enAdmin from './locales/en/admin.json'

export const SUPPORTED_LANGUAGES = ['es', 'ca', 'en'] as const
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number]

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      es: { common: esCommon, chat: esChat, admin: esAdmin },
      ca: { common: caCommon, chat: caChat, admin: caAdmin },
      en: { common: enCommon, chat: enChat, admin: enAdmin },
    },
    fallbackLng: 'es',
    supportedLngs: SUPPORTED_LANGUAGES,
    ns: ['common', 'chat', 'admin'],
    defaultNS: 'common',
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  })

export default i18n
