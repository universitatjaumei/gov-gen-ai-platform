import { describe, it, expect, beforeAll } from 'vitest'
import { createInstance } from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import i18n, { SUPPORTED_LANGUAGES } from '../index'
import esCommon from '../locales/es/common.json'
import caCommon from '../locales/ca/common.json'
import enCommon from '../locales/en/common.json'

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

/**
 * Lo que ve un navegador que se declara en `idiomaDelNavegador` (issue #16).
 *
 * Monta una instancia aparte con el **detector puesto**, porque el filtrado por `supportedLngs`
 * ocurre al detectar el idioma y no al cambiarlo a mano: `changeLanguage('en-GB')` se salta
 * exactamente la parte que hay que probar.
 */
async function idiomaDetectado(idiomaDelNavegador: string): Promise<string> {
  Object.defineProperty(window.navigator, 'language', {
    value: idiomaDelNavegador,
    configurable: true,
  })
  Object.defineProperty(window.navigator, 'languages', {
    value: [idiomaDelNavegador],
    configurable: true,
  })
  window.localStorage.clear()

  const instancia = createInstance()
  await instancia.use(LanguageDetector).init({
    resources: {
      es: { common: esCommon },
      ca: { common: caCommon },
      en: { common: enCommon },
    },
    fallbackLng: { 'ca-ES': ['ca', 'es'], default: ['es'] },
    supportedLngs: SUPPORTED_LANGUAGES as unknown as string[],
    ns: ['common'],
    defaultNS: 'common',
    interpolation: { escapeValue: false },
    detection: { order: ['localStorage', 'navigator'], caches: [] },
  })
  return instancia.t('loading')
}

describe('i18n configuration', () => {
  it('should_load_spanish_translations', async () => {
    await i18n.changeLanguage('es')
    expect(i18n.t('loading')).toBe('Cargando...')
    expect(i18n.t('save')).toBe('Guardar')
  })

  it('should_load_catalan_translations', async () => {
    await i18n.changeLanguage('ca')
    expect(i18n.t('loading')).toBe('Carregant...')
    expect(i18n.t('cancel')).toBe('Cancel·lar')
  })

  it('should_load_english_translations', async () => {
    await i18n.changeLanguage('en')
    expect(i18n.t('loading')).toBe('Loading...')
    expect(i18n.t('save')).toBe('Save')
  })

  it('should_fallback_to_spanish_for_unknown_language', async () => {
    await i18n.changeLanguage('fr')
    expect(i18n.t('loading')).toBe('Cargando...')
  })

  /**
   * Issue #16 — una variante regional resuelve al idioma base que sí existe.
   *
   * La issue decía que un navegador `en-GB` caía al castellano porque no casaba con `en`, y que
   * faltaba `load: 'languageOnly'`. **Se midió el 2026-09-26 y ya no ocurre**: con i18next 26.4.2
   * el camino del navegador resuelve `en-GB` a `en`, y añadir esa línea no cambia absolutamente
   * nada — comprobado ejecutando las dos configuraciones en paralelo, con y sin ella.
   *
   * Así que lo que queda no es la línea, es **este test**. Un arreglo que no hace nada sería
   * código especulativo; un test que fija la garantía avisa el día que una actualización de
   * i18next la rompa, y entonces la línea se añadirá con motivo y no por si acaso.
   *
   * **Se prueba por donde pasa un navegador de verdad**, no con `changeLanguage`: el filtrado
   * por `supportedLngs` ocurre al detectar, así que llamar directamente al cambio de idioma
   * esquiva justamente la parte que la issue señalaba. Esa fue la primera versión de este test
   * y pasaba sin demostrar nada.
   *
   * **Lo que no se ha podido demostrar, dicho para que nadie lo suponga**: no hay forma de
   * reproducir el defecto original con esta versión. Se intentó forzando `load: 'currentOnly'`
   * —lo contrario de lo que pedía la issue— y `en-GB` seguía resolviendo a `en`, o sea que en
   * i18next 26 esa resolución ya no depende de `load` en absoluto. Lo que sí se comprobó es que
   * este test **sabe ponerse rojo**: quitando el inglés de los recursos falla con
   * «expected 'Cargando...' to be 'Loading...'», que es exactamente el síntoma de la issue.
   */
  it('should_resolve_regional_variants_to_their_base_language', async () => {
    expect(await idiomaDetectado('en-GB')).toBe('Loading...')
    expect(await idiomaDetectado('ca-ES')).toBe('Carregant...')
    expect(await idiomaDetectado('es-MX')).toBe('Cargando...')
  })

  /** Y una variante de un idioma que NO está traducido sigue cayendo al castellano. */
  it('should_still_fallback_when_the_base_language_is_not_translated', async () => {
    expect(await idiomaDetectado('fr-CA')).toBe('Cargando...')
  })

  it('should_expose_supported_languages_constant', () => {
    expect(SUPPORTED_LANGUAGES).toContain('es')
    expect(SUPPORTED_LANGUAGES).toContain('ca')
    expect(SUPPORTED_LANGUAGES).toContain('en')
    expect(SUPPORTED_LANGUAGES).toHaveLength(3)
  })

  it('should_have_confirm_delete_and_no_results_in_all_locales', async () => {
    for (const lang of ['es', 'ca', 'en']) {
      await i18n.changeLanguage(lang)
      expect(i18n.t('confirm_delete')).not.toBe('confirm_delete')
      expect(i18n.t('no_results')).not.toBe('no_results')
    }
  })

  it('should_load_admin_namespace', async () => {
    await i18n.changeLanguage('es')
    expect(i18n.t('nav.chatbots', { ns: 'admin' })).toBe('Chatbots')
    expect(i18n.t('login.title', { ns: 'admin' })).toBe('Iniciar sesión')
  })

  it('should_load_chat_namespace', async () => {
    await i18n.changeLanguage('es')
    expect(i18n.t('send', { ns: 'chat' })).toBe('Enviar')
    expect(i18n.t('placeholder', { ns: 'chat' })).toBe('Escribe tu pregunta...')
  })
})
