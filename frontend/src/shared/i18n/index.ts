import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import esCommon from './locales/es/common.json'
import esChat from './locales/es/chat.json'
import esAdmin from './locales/es/admin.json'
import enCommon from './locales/en/common.json'
import enChat from './locales/en/chat.json'
import enAdmin from './locales/en/admin.json'
import valCommon from './locales/val/common.json'
import valChat from './locales/val/chat.json'
import valAdmin from './locales/val/admin.json'

export const SUPPORTED_LANGUAGES = ['es', 'val', 'en'] as const
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number]

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      es:  { common: esCommon,  chat: esChat,  admin: esAdmin  },
      val: { common: valCommon, chat: valChat, admin: valAdmin },
      en:  { common: enCommon,  chat: enChat,  admin: enAdmin  },
    },
    // Browsers reporting 'ca' or 'ca-ES' get Valencian content (same language)
    fallbackLng: {
      ca:     ['val', 'es'],
      'ca-ES': ['val', 'es'],
      default: ['es'],
    },
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
