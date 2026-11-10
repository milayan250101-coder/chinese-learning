import type { Language } from '../types'

type TranslationResponse = {
  responseStatus?: number
  responseDetails?: string
  responseData?: { translatedText?: string }
}

const languages: Language[] = ['en', 'de', 'fr', 'es', 'it']

async function requestTranslation(query: string, source: string, target: string, signal?: AbortSignal) {
  const params = new URLSearchParams({ q: query, langpair: `${source}|${target}` })
  const response = await fetch(`https://api.mymemory.translated.net/get?${params}`, { signal })
  if (!response.ok) throw new Error(`翻译服务返回 HTTP ${response.status}。`)
  const data = await response.json() as TranslationResponse
  const translatedText = data.responseData?.translatedText?.trim()
  if (data.responseStatus !== 200 || !translatedText || translatedText.toLocaleLowerCase() === query.toLocaleLowerCase()) {
    throw new Error(data.responseDetails || '服务没有返回有效翻译。')
  }
  return translatedText
}

export async function translateChineseWord(chinese: string, language: Language, signal?: AbortSignal) {
  const query = chinese.trim()
  if (!query) throw new Error('请输入中文后再翻译。')
  try {
    return await requestTranslation(query, 'zh-CN', language, signal)
  } catch (directError) {
    if (language === 'en') throw directError
    try {
      const english = await requestTranslation(query, 'zh-CN', 'en', signal)
      return await requestTranslation(english, 'en', language, signal)
    } catch {
      throw new Error('直译和英文中转都没有返回有效结果。')
    }
  }
}

export async function translateChineseWordToAll(chinese: string, signal?: AbortSignal) {
  const translations: Partial<Record<Language, string>> = {}
  const failures: Language[] = []
  for (const language of languages) {
    try {
      translations[language] = await translateChineseWord(chinese, language, signal)
    } catch {
      failures.push(language)
    }
  }
  return { translations, failures }
}