export type Language = 'en' | 'de' | 'fr' | 'es' | 'it'
export type GameId = 'pinyin' | 'word' | 'matching' | 'flashcards'

export type VocabularyWord = {
  id: string
  chinese: string
  pinyin: string
  translations: Record<Language, string>
  translationSources?: Partial<Record<Language, 'automatic' | 'manual'>>
  pinyinSource?: 'automatic' | 'manual'
  category: string
  image: VocabularyImage | null
}

export type VocabularyImage = {
  url: string
  thumbnailUrl: string
  sourceUrl: string
  sourceName: string
  source: string
  license: string
  creator?: string
  pageUrl?: string
}

export type SavedPractice = {
  id: string
  name: string
  language: Language
  wordIds: string[]
  folderId?: string
  studentName?: string
  status?: 'draft' | 'published'
  shareCode?: string
  remoteId?: string
  settings?: PracticeSettings
  snapshot?: PracticeItemSnapshot[]
  createdAt: string
  updatedAt: string
}

export type PracticeFolder = {
  id: string
  name: string
  isBuiltIn: boolean
  createdAt: string
}

export type PracticeSettings = {
  gameIds: GameId[]
  questionCount: number | 'all'
  showImages: boolean
  showPinyin: boolean
  allowSpeech: boolean
}

export type PracticeItemSnapshot = VocabularyWord & {
  position: number
  answer: string
}

export type PracticeAnswer = {
  itemId: string
  selectedAnswer: string
  displayAnswer?: string
  correct: boolean
  chinese?: string
  pinyin?: string
  correctAnswer?: string
}

export type PracticeResult = {
  id: string
  practiceId: string
  studentName: string
  startTime: string
  endTime: string
  score: number
  maxScore: number
  accuracy: number
  stars: number
  answers: PracticeAnswer[]
  incorrect?: { chinese: string; pinyin: string; selected: string; correct: string }[]
}

export type ExportMode = 'study' | 'workbook' | 'answers' | 'results'

export type ExportFields = {
  chinese: boolean
  pinyin: boolean
  en: boolean
  de: boolean
  fr: boolean
  es: boolean
  it: boolean
  image: boolean
  speechHint: boolean
  exercises: boolean
  answers: boolean
  results: boolean
  stars: boolean
  errorAnalysis: boolean
}

export type ExportResult = {
  score: number
  maxScore: number
  accuracy: number
  starsEarned: number
  incorrect?: { chinese: string; pinyin: string; selected: string; correct: string }[]
}

export type SpeechLocale = 'zh-CN' | 'en-US' | 'de-DE' | 'fr-FR' | 'es-ES' | 'it-IT'