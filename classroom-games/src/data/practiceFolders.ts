import type { PracticeFolder, PracticeSettings } from '../types'

export const defaultPracticeFolders: PracticeFolder[] = Array.from({ length: 6 }, (_, index) => ({
  id: `hsk-${index + 1}`,
  name: `HSK ${index + 1}`,
  isBuiltIn: true,
  createdAt: '2026-10-08T00:00:00.000Z',
}))

export const defaultPracticeSettings: PracticeSettings = {
  gameIds: ['pinyin', 'word', 'matching', 'flashcards'],
  questionCount: 'all',
  showImages: true,
  showPinyin: true,
  allowSpeech: true,
}