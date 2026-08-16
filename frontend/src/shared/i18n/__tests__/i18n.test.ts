import { describe, it, expect, beforeAll } from 'vitest'
import i18n, { SUPPORTED_LANGUAGES } from '../index'

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

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
