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
})
