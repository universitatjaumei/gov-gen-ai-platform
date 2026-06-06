import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import esCommon from './locales/es/common.json'
import esChat from './locales/es/chat.json'
import esAdmin from './locales/es/admin.json'
import esScripts from './locales/es/scripts.json'
import esRedaccion from './locales/es/redaccion.json'
import esContentQuality from './locales/es/contentQuality.json'
import enCommon from './locales/en/common.json'
import enChat from './locales/en/chat.json'
import enAdmin from './locales/en/admin.json'
import enScripts from './locales/en/scripts.json'
import enRedaccion from './locales/en/redaccion.json'
import enContentQuality from './locales/en/contentQuality.json'
import caCommon from './locales/ca/common.json'
import caChat from './locales/ca/chat.json'
import caAdmin from './locales/ca/admin.json'
import caScripts from './locales/ca/scripts.json'
import caRedaccion from './locales/ca/redaccion.json'
import caContentQuality from './locales/ca/contentQuality.json'

export const SUPPORTED_LANGUAGES = ['es', 'ca', 'en'] as const
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number]

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      es: { common: esCommon, chat: esChat, admin: esAdmin, scripts: esScripts, redaccion: esRedaccion, contentQuality: esContentQuality },
      ca: { common: caCommon, chat: caChat, admin: caAdmin, scripts: caScripts, redaccion: caRedaccion, contentQuality: caContentQuality },
      en: { common: enCommon, chat: enChat, admin: enAdmin, scripts: enScripts, redaccion: enRedaccion, contentQuality: enContentQuality },
    },
    fallbackLng: {
      'ca-ES': ['ca', 'es'],
      default: ['es'],
    },
    supportedLngs: SUPPORTED_LANGUAGES,
    ns: ['common', 'chat', 'admin', 'scripts', 'redaccion', 'contentQuality'],
    defaultNS: 'common',
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  })

export default i18n
