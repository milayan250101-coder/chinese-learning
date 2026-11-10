import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, ArrowRight, BookOpenCheck, FolderOpen, House, ListPlus, RotateCcw } from 'lucide-react'
import GameMenu from './components/GameMenu'
import FolderManager from './components/FolderManager'
import TeacherAccess from './components/TeacherAccess'
import StudentPracticePage from './components/StudentPracticePage'
import PracticeResults from './components/PracticeResults'
import Header from './components/Header'
import LanguageSelector from './components/LanguageSelector'
import PdfExportDialog, { type ExportSettings } from './components/PdfExportDialog'
import PrintableDocument from './components/PrintableDocument'
import PracticeBuilder from './components/PracticeBuilder'
import SavedPractices from './components/SavedPractices'
import Score from './components/Score'
import VocabularyManager from './components/VocabularyManager'
import { languageOptions, text } from './data/translations'
import { vocabulary } from './data/vocabulary'
import { defaultPracticeFolders, defaultPracticeSettings } from './data/practiceFolders'
import type { ExportMode, ExportResult, GameId, Language, PracticeFolder, PracticeResult, PracticeSettings, SavedPractice, VocabularyWord } from './types'
import { StarRewardSession } from './services/starRewards'
import { isSupabaseConfigured, supabase } from './services/supabaseClient'
import { deleteTeacherVocabulary, listPracticeResults, loadHostedWorkspace, moveHostedPractices, publishPractice as publishHostedPractice, signInTeacher as sendTeacherLink, signOutTeacher as signOutHostedTeacher, syncTeacherFolders, syncTeacherVocabulary } from './services/hostedPracticeService'
import FlashCards from './games/FlashCards'
import MatchingGame from './games/MatchingGame'
import PinyinQuiz from './games/PinyinQuiz'
import WordQuiz from './games/WordQuiz'

type Page = 'home' | 'vocabulary' | 'folders' | 'create' | 'practices' | 'results' | 'game' | 'student' | 'settings' | 'print'

function readStored<T>(key: string, fallback: T): T {
  try {
    const saved = window.localStorage.getItem(key)
    return saved ? JSON.parse(saved) as T : fallback
  } catch {
    return fallback
  }
}

function saveStored(key: string, value: unknown) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch {
    window.alert('浏览器存储空间不可用，请导出或备份当前词汇。')
  }
}

function shuffled<T>(items: T[]) {
  const result = [...items]
  for (let index = result.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1))
    ;[result[index], result[swapIndex]] = [result[swapIndex], result[index]]
  }
  return result
}

function matchingRounds(words: VocabularyWord[]) {
  if (words.length < 2) return []
  const roundCount = Math.ceil(words.length / 4)
  const baseSize = Math.floor(words.length / roundCount)
  const extra = words.length % roundCount
  const rounds: VocabularyWord[][] = []
  let cursor = 0
  for (let index = 0; index < roundCount; index += 1) {
    const size = baseSize + (index < extra ? 1 : 0)
    rounds.push(words.slice(cursor, cursor + size))
    cursor += size
  }
  return rounds
}

function newId() {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function App() {
  const [shareCode, setShareCode] = useState(() => window.location.pathname.startsWith('/practice/') ? window.location.pathname.split('/')[2] ?? '' : '')
  const [page, setPage] = useState<Page>(() => window.location.pathname.startsWith('/practice/') ? 'student' : 'home')
  const [returnPage, setReturnPage] = useState<Page>('home')
  const [language, setLanguage] = useState<Language>(() => readStored('hanzi-island-language', 'en'))
  const [words, setWords] = useState<VocabularyWord[]>(() => readStored('hanzi-island-vocabulary', vocabulary))
  const [practices, setPractices] = useState<SavedPractice[]>(() => readStored('hanzi-island-practices', []))
  const [folders, setFolders] = useState<PracticeFolder[]>(() => readStored('hanzi-island-folders', defaultPracticeFolders))
  const [selectedIds, setSelectedIds] = useState<string[]>(() => readStored('hanzi-island-selected', vocabulary.slice(0, 10).map((word) => word.id)))
  const [selectionLimit, setSelectionLimit] = useState<number | 'custom' | 'all'>(10)
  const [questionCount, setQuestionCount] = useState(10)
  const [activeGame, setActiveGame] = useState<GameId>('pinyin')
  const [practiceName, setPracticeName] = useState('')
  const [studentName, setStudentName] = useState('')
  const [teacherEmail, setTeacherEmail] = useState('')
  const [signedInEmail, setSignedInEmail] = useState<string | null>(null)
  const [cloudWorkspaceLoaded, setCloudWorkspaceLoaded] = useState(false)
  const [backendError, setBackendError] = useState('')
  const [resultsPractice, setResultsPractice] = useState<SavedPractice | null>(null)
  const [practiceResults, setPracticeResults] = useState<PracticeResult[]>([])
  const [resultsLoading, setResultsLoading] = useState(false)
  const [folderId, setFolderId] = useState('hsk-1')
  const [practiceSettings, setPracticeSettings] = useState<PracticeSettings>(defaultPracticeSettings)
  const [editingPracticeId, setEditingPracticeId] = useState<string | null>(null)
  const [session, setSession] = useState<VocabularyWord[]>([])
  const [questionIndex, setQuestionIndex] = useState(0)
  const [score, setScore] = useState(0)
  const [best, setBest] = useState(() => Number(readStored('hanzi-island-best', 0)))
  const [totalStars, setTotalStars] = useState(() => Number(readStored('chineseVocabularyStars', 0)))
  const [roundStars, setRoundStars] = useState(0)
  const [questionStars, setQuestionStars] = useState(0)
  const [completionBonusAwarded, setCompletionBonusAwarded] = useState(false)
  const [streak, setStreak] = useState(0)
  const [correctAnswers, setCorrectAnswers] = useState(0)
  const [answerRecords, setAnswerRecords] = useState<import('./types').PracticeAnswer[]>([])
  const [starPulse, setStarPulse] = useState(0)
  const [starPulseAmount, setStarPulseAmount] = useState(1)
  const [answer, setAnswer] = useState<string | null>(null)
  const [finished, setFinished] = useState(false)
  const [rate, setRate] = useState(1)
  const [exportOpen, setExportOpen] = useState(false)
  const [printWords, setPrintWords] = useState<VocabularyWord[]>([])
  const [printTitle, setPrintTitle] = useState('中文词汇练习')
  const [exportSettings, setExportSettings] = useState<ExportSettings | null>(null)
  const [printResult, setPrintResult] = useState<ExportResult | null>(null)
  const [printReturnPage, setPrintReturnPage] = useState<Page>('home')
  const rewardSession = useRef(new StarRewardSession())
  const answerLocked = useRef(false)
  const advanceLocked = useRef(false)

  const copy = text[language]
  const languageOption = languageOptions.find((option) => option.id === language)
  const currentWord = session[questionIndex] ?? session[0]
  const activeGameLabel = copy.games[activeGame]
  const selectedWords = words.filter((word) => selectedIds.includes(word.id))
  const pairGroups = matchingRounds(session)
  const gameQuestionCount = activeGame === 'matching' ? pairGroups.length : session.length

  useEffect(() => { document.documentElement.lang = languageOption?.locale ?? 'en' }, [languageOption])
  useEffect(() => {
    if (!supabase) return
    void supabase.auth.getSession().then(({ data }) => setSignedInEmail(data.session?.user.email ?? null))
    const { data } = supabase.auth.onAuthStateChange((_event, session) => setSignedInEmail(session?.user.email ?? null))
    return () => data.subscription.unsubscribe()
  }, [])
  useEffect(() => {
    if (!signedInEmail || !isSupabaseConfigured) {
      setCloudWorkspaceLoaded(false)
      return
    }
    let cancelled = false
    setBackendError('')
    void loadHostedWorkspace().then((remote) => {
      if (cancelled) return
      setWords((local) => {
        const merged = new Map(local.map((word) => [word.id, word]))
        for (const word of remote.words) merged.set(word.id, word)
        return [...merged.values()]
      })
      setFolders((local) => {
        const merged = new Map(local.map((folder) => [folder.id, folder]))
        for (const folder of remote.folders) merged.set(folder.id, folder)
        return [...merged.values()]
      })
      setPractices((local) => {
        const merged = new Map(local.map((practice) => [practice.id, practice]))
        for (const practice of remote.practices) merged.set(practice.id, practice)
        return [...merged.values()]
      })
      setCloudWorkspaceLoaded(true)
    }).catch((error) => {
      if (!cancelled) setBackendError(error instanceof Error ? error.message : '无法同步教师工作区。')
    })
    return () => { cancelled = true }
  }, [signedInEmail])
  useEffect(() => {
    if (!signedInEmail || !cloudWorkspaceLoaded) return
    const timer = window.setTimeout(() => {
      void Promise.all([syncTeacherVocabulary(words), syncTeacherFolders(folders)]).catch((error) => {
        setBackendError(error instanceof Error ? error.message : '教师工作区同步失败。')
      })
    }, 500)
    return () => window.clearTimeout(timer)
  }, [signedInEmail, cloudWorkspaceLoaded, words, folders])
  useEffect(() => { saveStored('hanzi-island-language', language) }, [language])
  useEffect(() => { saveStored('hanzi-island-vocabulary', words) }, [words])
  useEffect(() => { saveStored('hanzi-island-practices', practices) }, [practices])
  useEffect(() => { saveStored('hanzi-island-folders', folders) }, [folders])
  useEffect(() => { saveStored('hanzi-island-selected', selectedIds) }, [selectedIds])
  useEffect(() => { saveStored('hanzi-island-best', best) }, [best])
  useEffect(() => { saveStored('chineseVocabularyStars', totalStars) }, [totalStars])
  useEffect(() => { setSelectedIds((current) => current.filter((id) => words.some((word) => word.id === id))) }, [words])
  useEffect(() => {
    if (typeof selectionLimit === 'number') setSelectedIds((current) => current.length > selectionLimit ? current.slice(0, selectionLimit) : current)
  }, [selectionLimit])
  useEffect(() => { if (score > best) setBest(score) }, [score, best])
  useEffect(() => { answerLocked.current = false; advanceLocked.current = false }, [activeGame, questionIndex])

  function resetStreak() {
    rewardSession.current.breakStreak()
    setStreak(0)
    setQuestionStars(0)
  }

  function awardCorrect(key: string) {
    const result = rewardSession.current.awardCorrect(key)
    if (result.duplicate) return 0
    setStreak(result.streak)
    setCorrectAnswers((current) => current + 1)
    const awarded = result.stars
    setTotalStars((current) => current + awarded)
    setRoundStars((current) => current + awarded)
    setQuestionStars(awarded)
    setStarPulseAmount(awarded)
    setStarPulse((current) => current + 1)
    return awarded
  }

  function awardCompletion() {
    const bonus = rewardSession.current.awardCompletion(activeGame)
    if (!bonus) return
    setTotalStars((current) => current + 3)
    setRoundStars((current) => current + 3)
    setQuestionStars(3)
    setCompletionBonusAwarded(true)
    setStarPulseAmount(3)
    setStarPulse((current) => current + 1)
  }

  function addOrUpdateWord(word: VocabularyWord) {
    setWords((current) => current.some((item) => item.id === word.id)
      ? current.map((item) => item.id === word.id ? word : item)
      : [...current, word])
  }

  function updateSelectedIds(ids: string[]) {
    setSelectedIds(typeof selectionLimit === 'number' ? ids.slice(0, selectionLimit) : ids)
  }

  function deleteWord(id: string) {
    setWords((current) => current.filter((word) => word.id !== id))
    setSelectedIds((current) => current.filter((item) => item !== id))
    setPractices((current) => current.map((practice) => ({ ...practice, wordIds: practice.wordIds.filter((item) => item !== id) })))
    if (signedInEmail && cloudWorkspaceLoaded) void deleteTeacherVocabulary([id]).catch((error) => setBackendError(String(error)))
  }

  function createFolder(name: string) {
    if (folders.some((folder) => folder.name.toLocaleLowerCase() === name.toLocaleLowerCase())) {
      window.alert('已存在同名文件夹。')
      return
    }
    setFolders((current) => [...current, { id: newId(), name, isBuiltIn: false, createdAt: new Date().toISOString() }])
  }

  function renameFolder(folder: PracticeFolder, name: string) {
    if (folders.some((item) => item.id !== folder.id && item.name.toLocaleLowerCase() === name.toLocaleLowerCase())) {
      window.alert('已存在同名文件夹。')
      return
    }
    setFolders((current) => current.map((item) => item.id === folder.id ? { ...item, name } : item))
  }

  function deleteFolder(folder: PracticeFolder) {
    if (folder.isBuiltIn || !window.confirm(`删除“${folder.name}”？其中的练习将移动到 HSK 1。`)) return
    setFolders((current) => current.filter((item) => item.id !== folder.id))
    setPractices((current) => current.map((practice) => practice.folderId === folder.id ? { ...practice, folderId: 'hsk-1', updatedAt: new Date().toISOString() } : practice))
  }

  function bulkDeleteWords(ids: string[]) {
    const deleted = new Set(ids)
    setWords((current) => current.filter((word) => !deleted.has(word.id)))
    setSelectedIds((current) => current.filter((id) => !deleted.has(id)))
    setPractices((current) => current.map((practice) => ({ ...practice, wordIds: practice.wordIds.filter((id) => !deleted.has(id)) })))
    if (signedInEmail && cloudWorkspaceLoaded) void deleteTeacherVocabulary(ids).catch((error) => setBackendError(String(error)))
  }

  function createPracticeFromVocabulary() {
    setEditingPracticeId(null)
    setPracticeName('')
    setPage('create')
  }

  async function publishSavedPractice(practice: SavedPractice) {
    if (!isSupabaseConfigured || !signedInEmail) {
      setBackendError(!isSupabaseConfigured ? '请先配置 Supabase 环境变量。' : '请先登录教师账号。')
      setPage('settings')
      return
    }
    try {
      const snapshotWords = practice.snapshot?.length ? practice.snapshot : practice.wordIds.map((id) => words.find((word) => word.id === id)).filter((word): word is VocabularyWord => Boolean(word))
      if (snapshotWords.length < 4) throw new Error('练习需要至少 4 个词汇才能发布。')
      const frozenSnapshot = snapshotWords.map((word, position) => ({ ...word, position, answer: word.chinese }))
      const hosted = await publishHostedPractice(practice, frozenSnapshot, folders.find((folder) => folder.id === practice.folderId)?.name)
      setPractices((current) => current.map((item) => item.id === practice.id ? { ...item, status: 'published', shareCode: hosted.shareCode, remoteId: hosted.id, snapshot: frozenSnapshot, updatedAt: new Date().toISOString() } : item))
      setBackendError('')
    } catch (error) {
      setBackendError(error instanceof Error ? error.message : '发布失败，请检查 Supabase 配置和权限。')
    }
  }

  async function copyPracticeLink(practice: SavedPractice) {
    if (!practice.shareCode || practice.status !== 'published') return
    const url = `${window.location.origin}/practice/${practice.shareCode}`
    try {
      await navigator.clipboard.writeText(url)
      window.alert(`练习链接已复制：\n${url}`)
    } catch {
      window.prompt('复制此学生练习链接：', url)
    }
  }

  async function viewPracticeResults(practice: SavedPractice) {
    if (!isSupabaseConfigured || !signedInEmail || !practice.remoteId) {
      setBackendError('查看跨设备成绩需要发布练习，并登录已配置的 Supabase 教师账号。')
      setPage('settings')
      return
    }
    setResultsPractice(practice)
    setPracticeResults([])
    setResultsLoading(true)
    setBackendError('')
    setPage('results')
    try {
      setPracticeResults(await listPracticeResults(practice.remoteId))
    } catch (error) {
      setBackendError(error instanceof Error ? error.message : '无法读取学生成绩。')
    } finally {
      setResultsLoading(false)
    }
  }

  function exportPracticeResult(result: PracticeResult) {
    const snapshot = resultsPractice?.snapshot ?? []
    const wordById = new Map(snapshot.map((word) => [word.id, word]))
    setPrintWords(snapshot)
    setPrintTitle(`${result.studentName} - ${resultsPractice?.name ?? '练习成绩'}`)
    setPrintResult({
      score: result.score,
      maxScore: result.maxScore,
      accuracy: result.accuracy,
      starsEarned: result.stars,
      incorrect: result.incorrect ?? result.answers.filter((answer) => !answer.correct).map((answer) => {
        const word = wordById.get(answer.itemId)
        return { chinese: word?.chinese ?? answer.chinese ?? '', pinyin: word?.pinyin ?? answer.pinyin ?? '', selected: answer.displayAnswer ?? answer.selectedAnswer, correct: answer.correctAnswer ?? word?.chinese ?? '' }
      }),
    })
    setPrintReturnPage('results')
    setExportOpen(true)
  }

  async function sendTeacherMagicLink() {
    if (!teacherEmail.trim()) throw new Error('请输入教师邮箱。')
    const { error } = await sendTeacherLink(teacherEmail.trim())
    if (error) throw error
  }

  async function signOutTeacher() {
    const { error } = await signOutHostedTeacher()
    if (error) throw error
  }

  function startGame(game: GameId, gameWords: VocabularyWord[], name: string, from: Page) {
    if (gameWords.length < 4) {
      window.alert('至少需要 4 个词汇，才能为四种游戏生成互不重复的选项。')
      return
    }
    const distinctPinyin = new Set(gameWords.map((word) => word.pinyin)).size
    const distinctChinese = new Set(gameWords.map((word) => word.chinese)).size
    const distinctAnswers = game === 'pinyin' ? distinctPinyin : game === 'word' ? distinctChinese : game === 'matching' ? Math.min(distinctChinese, distinctPinyin) : gameWords.length
    if (game !== 'flashcards' && distinctAnswers < 4) {
      window.alert('所选词汇中可区分的答案不足 4 个，请检查是否有重复汉字或拼音。')
      return
    }
    setReturnPage(from)
    setSession(shuffled(gameWords))
    setSelectedIds(gameWords.map((word) => word.id))
    setActiveGame(game)
    setPracticeName(name)
    setQuestionIndex(0)
    setScore(0)
    setAnswer(null)
    setFinished(false)
    setRoundStars(0)
    setQuestionStars(0)
    setCompletionBonusAwarded(false)
    setStreak(0)
    setCorrectAnswers(0)
    setAnswerRecords([])
    rewardSession.current.reset()
    setPage('game')
    answerLocked.current = false
    advanceLocked.current = false
  }

  function startQuickGame(game: GameId) {
    const quickWords = shuffled(words).slice(0, Math.min(questionCount, words.length))
    startGame(game, quickWords, '即兴练习', 'home')
  }

  function generatePractice() {
    if (selectedWords.length < 4) {
      window.alert('请至少选择 4 个词汇，才能生成四种游戏。')
      return
    }
    if (!practiceSettings.gameIds.length) {
      window.alert('请至少选择一种游戏。')
      return
    }
    const practiceWords = practiceSettings.questionCount === 'all' ? selectedWords : selectedWords.slice(0, practiceSettings.questionCount)
    if (practiceWords.length < 4) {
      window.alert('当前题目数量少于 4 个，请增加题数或选择更多词汇。')
      return
    }
    const now = new Date().toISOString()
    if (new Set(practiceWords.map((word) => word.pinyin)).size < 4 || new Set(practiceWords.map((word) => word.chinese)).size < 4) {
      window.alert('请选择至少 4 个汉字和拼音都不同的词汇，避免游戏出现重复选项。')
      return
    }
    const baseName = practiceName.trim() || `课堂练习 ${new Date().toLocaleDateString()}`
    const name = studentName.trim() ? `${studentName.trim()} - ${baseName}` : baseName
    const snapshot = practiceWords.map((word, position) => ({ ...word, position, answer: word.chinese }))
    let practiceId = editingPracticeId
    if (editingPracticeId) {
      if (!window.confirm('保存并重新生成会更新这个已保存练习，词汇库中的原始词条不会被覆盖。要继续吗？')) return
      setPractices((current) => current.map((practice) => practice.id === editingPracticeId
        ? { ...practice, name, language, folderId, studentName, settings: practiceSettings, wordIds: practiceWords.map((word) => word.id), snapshot, updatedAt: now }
        : practice))
    } else {
      practiceId = newId()
      setPractices((current) => [...current, { id: practiceId!, name, language, folderId, studentName, status: 'draft', settings: practiceSettings, wordIds: practiceWords.map((word) => word.id), snapshot, createdAt: now, updatedAt: now }])
    }
    setEditingPracticeId(practiceId)
    startGame(practiceSettings.gameIds[0], practiceWords, name, 'create')
  }

  function openPractice(practice: SavedPractice) {
    const practiceWords = practice.snapshot?.length ? practice.snapshot : practice.wordIds.map((id) => words.find((word) => word.id === id)).filter((word): word is VocabularyWord => Boolean(word))
    setLanguage(practice.language)
    setFolderId(practice.folderId ?? 'hsk-1')
    setStudentName(practice.studentName ?? '')
    setPracticeSettings(practice.settings ?? defaultPracticeSettings)
    startGame(practice.settings?.gameIds[0] ?? 'pinyin', practiceWords, practice.name, 'practices')
  }

  function editPractice(practice: SavedPractice) {
    const availableIds = practice.wordIds.filter((id) => words.some((word) => word.id === id))
    setLanguage(practice.language)
    setSelectedIds(availableIds)
    setPracticeName(practice.name)
    setStudentName(practice.studentName ?? '')
    setFolderId(practice.folderId ?? 'hsk-1')
    setPracticeSettings(practice.settings ?? defaultPracticeSettings)
    setEditingPracticeId(practice.id)
    setPage('create')
  }

  function duplicatePractice(practice: SavedPractice) {
    const now = new Date().toISOString()
    const duplicate = { ...practice, id: newId(), name: `${practice.name}（副本）`, createdAt: now, updatedAt: now }
    setPractices((current) => [duplicate, ...current])
  }

  function removePractice(practice: SavedPractice) {
    if (window.confirm(`确定删除练习“${practice.name}”吗？词汇库中的词条不会删除。`)) setPractices((current) => current.filter((item) => item.id !== practice.id))
  }

  function movePractice(practice: SavedPractice, nextFolderId: string) {
    if (!folders.some((folder) => folder.id === nextFolderId)) return
    setPractices((current) => current.map((item) => item.id === practice.id ? { ...item, folderId: nextFolderId, updatedAt: new Date().toISOString() } : item))
    if (practice.status === 'published' && signedInEmail) void moveHostedPractices(practice.id, nextFolderId).catch((error) => setBackendError(error instanceof Error ? error.message : '云端目录更新失败。'))
  }

  function submitAnswer(value: string) {
    if (answer !== null || answerLocked.current) return
    answerLocked.current = true
    setAnswer(value)
    const selectedWord = session.find((word) => word.id === value)
    if (currentWord && selectedWord) setAnswerRecords((current) => [...current, { itemId: currentWord.id, selectedAnswer: value, displayAnswer: activeGame === 'pinyin' ? selectedWord.pinyin : selectedWord.chinese, correct: value === currentWord.id, chinese: currentWord.chinese, pinyin: currentWord.pinyin, correctAnswer: activeGame === 'pinyin' ? currentWord.pinyin : currentWord.chinese }])
    if (value === currentWord?.id) {
      setScore((current) => current + 10)
      awardCorrect(`${activeGame}:${currentWord.id}`)
    } else resetStreak()
  }

  function completeMatching() {
    if (answer !== null || answerLocked.current) return
    answerLocked.current = true
    setAnswer('complete')
    setScore((current) => current + currentPairRound.length * 10)
  }

  function learnFlashcard() {
    if (answer !== null || answerLocked.current) return
    answerLocked.current = true
    setAnswer(currentWord?.id ?? 'learned')
    setScore((current) => current + 10)
    if (currentWord) {
      setAnswerRecords((current) => [...current, { itemId: currentWord.id, selectedAnswer: currentWord.chinese, displayAnswer: currentWord.translations[language], correct: true, chinese: currentWord.chinese, pinyin: currentWord.pinyin, correctAnswer: currentWord.translations[language] }])
      awardCorrect(`flashcards:${currentWord.id}`)
    }
  }

  function skipFlashcard() {
    if (answer !== null || answerLocked.current) return
    answerLocked.current = true
    resetStreak()
    setAnswer(`practice:${currentWord?.id ?? questionIndex}`)
    if (currentWord) setAnswerRecords((current) => [...current, { itemId: currentWord.id, selectedAnswer: '', correct: false, chinese: currentWord.chinese, pinyin: currentWord.pinyin, correctAnswer: currentWord.translations[language] }])
  }

  function correctPair(id: string) {
    const current = currentPairRound.find((word) => word.id === id)
    const awarded = awardCorrect(`matching:${id}`)
    if (current && awarded) setAnswerRecords((items) => [...items, { itemId: id, selectedAnswer: current.chinese, displayAnswer: current.chinese, correct: true, chinese: current.chinese, pinyin: current.pinyin, correctAnswer: current.chinese }])
  }

  function incorrectPair(firstId: string, secondId: string) {
    resetStreak()
    const current = currentPairRound.find((word) => word.id === firstId)
    const selected = currentPairRound.find((word) => word.id === secondId)
    if (current && selected) setAnswerRecords((items) => [...items, { itemId: current.id, selectedAnswer: selected.chinese, displayAnswer: selected.chinese, correct: false, chinese: current.chinese, pinyin: current.pinyin, correctAnswer: current.chinese }])
  }

  function switchGame(game: GameId) {
    if (!practiceSettings.gameIds.includes(game)) return
    const minimum = game === 'matching' ? 2 : game === 'flashcards' ? 1 : 4
    if (session.length < minimum) {
      window.alert(`此游戏至少需要 ${minimum} 个词汇。`)
      return
    }
    const distinctPinyin = new Set(session.map((word) => word.pinyin)).size
    const distinctChinese = new Set(session.map((word) => word.chinese)).size
    const distinctAnswers = game === 'pinyin' ? distinctPinyin : game === 'word' ? distinctChinese : game === 'matching' ? Math.min(distinctChinese, distinctPinyin) : session.length
    if (game !== 'flashcards' && distinctAnswers < 4) {
      window.alert('所选词汇中可区分的答案不足 4 个，请先调整词汇选择。')
      return
    }
    setSession(shuffled(session))
    setActiveGame(game)
    setQuestionIndex(0)
    setAnswer(null)
    setFinished(false)
    setScore(0)
    setCorrectAnswers(0)
    setAnswerRecords([])
    setRoundStars(0)
    resetStreak()
    setCompletionBonusAwarded(false)
    answerLocked.current = false
    advanceLocked.current = false
  }

  function nextQuestion() {
    if (answer === null || advanceLocked.current) return
    advanceLocked.current = true
    if (questionIndex + 1 >= gameQuestionCount) {
      awardCompletion()
      setFinished(true)
      return
    }
    setQuestionIndex((current) => current + 1)
    setAnswer(null)
    setQuestionStars(0)
  }

  function restartGame() {
    setSession(shuffled(session))
    setQuestionIndex(0)
    setScore(0)
    setAnswer(null)
    setFinished(false)
    setCorrectAnswers(0)
    setAnswerRecords([])
    setRoundStars(0)
    resetStreak()
    setCompletionBonusAwarded(false)
    answerLocked.current = false
    advanceLocked.current = false
  }

  function returnFromGame() {
    setPage(returnPage)
    setFinished(false)
  }

  function distractorsFor(word: VocabularyWord, field: 'pinyin' | 'chinese') {
    const seen = new Set([word[field]])
    return shuffled(session.filter((item) => {
      if (item.id === word.id || seen.has(item[field])) return false
      seen.add(item[field])
      return true
    })).slice(0, 3)
  }

  function requestExport(exportWords: VocabularyWord[], title: string) {
    if (exportWords.length === 0) {
      window.alert('请先选择至少一个词汇。')
      return
    }
    setPrintWords(exportWords)
    setPrintTitle(title)
    setPrintReturnPage(page)
    setPrintResult(page === 'game' && finished ? {
      score,
      maxScore: session.length * 10,
      accuracy: session.length ? Math.round((correctAnswers / session.length) * 100) : 0,
      starsEarned: roundStars,
      incorrect: answerRecords.filter((item) => !item.correct).map((item) => ({
        chinese: item.chinese ?? '',
        pinyin: item.pinyin ?? '',
        selected: item.displayAnswer ?? item.selectedAnswer,
        correct: item.correctAnswer ?? ''
        })),
    } : null)
    setExportOpen(true)
  }

  function beginPrint(settings: ExportSettings) {
    setExportSettings(settings)
    setExportOpen(false)
    setPage('print')
  }

  const currentPairRound = pairGroups[questionIndex] ?? []

  return <div className="app-shell" id="home">
    <Header language={language} rate={rate} stars={totalStars} starPulse={starPulse} starPulseAmount={starPulseAmount} onRateChange={setRate} onBack={page === 'game' ? returnFromGame : undefined} backLabel={copy.back} rateLabel={copy.rate} />
    {page !== 'student' && <nav className="site-nav" aria-label="主导航">{[
      { id: 'home' as const, label: '首页', icon: House },
      { id: 'vocabulary' as const, label: '词汇管理', icon: BookOpenCheck },
      { id: 'folders' as const, label: '练习文件夹', icon: FolderOpen },
      { id: 'create' as const, label: '创建练习', icon: ListPlus },
      { id: 'practices' as const, label: '我的练习', icon: FolderOpen },
      { id: 'settings' as const, label: '教师账号', icon: FolderOpen },
    ].map(({ id, label, icon: Icon }) => <button key={id} className={`site-nav-item ${page === id ? 'active' : ''}`} onClick={() => { setPage(id); if (id === 'create') { setEditingPracticeId(null); setPracticeName('') } }}><Icon size={15} /><span>{label}</span></button>)}</nav>}

    {page === 'home' && <main className="home-page">
      <section className="home-intro"><span className="home-kicker">CHINESE · PLAY · LEARN</span><h1>中文词汇<span>游戏</span></h1><p>{copy.subtitle}</p><div className="intro-stamp" aria-hidden="true"><span>汉</span><small>WORD<br />BY WORD</small></div></section>
      <section className="home-section language-section"><div className="section-heading"><div><span className="section-index">01</span><h2>{copy.chooseLanguage}</h2></div><span className="section-aside">{copy.studyLanguage}</span></div><LanguageSelector value={language} onChange={setLanguage} label={copy.chooseLanguage} /></section>
      <section className="home-section game-section"><div className="section-heading"><div><span className="section-index">02</span><h2>{copy.chooseGame}</h2></div><label className="count-control"><span>{copy.questionCount}</span><select value={questionCount} onChange={(event) => setQuestionCount(Number(event.target.value))} aria-label={copy.questionCount}><option value={10}>10</option><option value={20}>20</option></select></label></div><GameMenu onSelect={startQuickGame} language={language} copy={copy} /></section>
      <footer className="home-footer"><span>你好</span><span>nǐ hǎo</span><span>{words.length} 条词汇 · {practices.length} 个已保存练习</span></footer>
    </main>}

    {page === 'vocabulary' && <VocabularyManager words={words} language={language} rate={rate} selectedIds={selectedIds} onSelectedIdsChange={updateSelectedIds} onSaveWord={addOrUpdateWord} onAddWords={(added) => setWords((current) => [...current, ...added])} onDeleteWord={deleteWord} onBulkDelete={bulkDeleteWords} onCreatePractice={createPracticeFromVocabulary} selectionLimit={selectionLimit} onSelectionLimitChange={setSelectionLimit} />}

    {page === 'folders' && <FolderManager folders={folders} onCreate={createFolder} onRename={renameFolder} onDelete={deleteFolder} />}

    {page === 'create' && <PracticeBuilder words={words} selectedIds={selectedIds} onSelectionChange={updateSelectedIds} language={language} rate={rate} practiceName={practiceName} onNameChange={setPracticeName} onGenerate={generatePractice} onExport={() => requestExport(selectedWords, practiceName || '词汇练习')} editing={Boolean(editingPracticeId)} folders={folders} folderId={folderId} onFolderIdChange={setFolderId} studentName={studentName} onStudentNameChange={setStudentName} settings={practiceSettings} onSettingsChange={setPracticeSettings} />}

    {page === 'practices' && <SavedPractices practices={practices} folders={folders} canPublish={isSupabaseConfigured && Boolean(signedInEmail)} onOpen={openPractice} onEdit={editPractice} onDuplicate={duplicatePractice} onDelete={removePractice} onPublish={publishSavedPractice} onShare={copyPracticeLink} onMove={movePractice} onViewResults={viewPracticeResults} />}

    {page === 'results' && resultsPractice && <PracticeResults practiceName={resultsPractice.name} results={practiceResults} loading={resultsLoading} error={backendError} onBack={() => setPage('practices')} onExport={exportPracticeResult} />}

    {page === 'settings' && <TeacherAccess configured={isSupabaseConfigured} email={teacherEmail} onEmailChange={setTeacherEmail} signedInEmail={signedInEmail} initialError={backendError} onSendLink={sendTeacherMagicLink} onSignOut={signOutTeacher} />}

    {page === 'student' && <StudentPracticePage shareCode={shareCode} onBack={() => { window.history.replaceState(null, '', '/'); setShareCode(''); setPage('home') }} />}

    {page === 'game' && <main className="play-page">
      <div className="play-heading"><div><span className="play-kicker">{languageOption?.flag} {languageOption?.name} <span>/</span> {practiceName}</span><h1>{activeGameLabel}</h1></div><div className="game-header-actions"><Score score={score} label={copy.score} unit={copy.scoreUnit} best={best} bestLabel={copy.bestScore} /><button className="secondary-action" onClick={() => requestExport(session, practiceName)}><span>导出 PDF</span></button></div></div>
      <div className="game-switcher">{practiceSettings.gameIds.map((game) => <button key={game} className={activeGame === game ? 'active' : ''} onClick={() => switchGame(game)}>{copy.games[game]}</button>)}</div>
      <div className="progress-row"><strong>{copy.question} {questionIndex + 1} / {gameQuestionCount}</strong><div className="progress-track"><span style={{ width: `${((questionIndex + 1) / gameQuestionCount) * 100}%` }} /></div>{streak >= 2 && <span className="streak-counter">🔥 {streak}</span>}<span>{score} {copy.scoreUnit}</span></div>
      {finished ? <section className="completion-panel"><span className="completion-mark">🎉</span><p className="completion-kicker">{copy.scoreOutOf}: {score} / {session.length * 10}</p><h2>{copy.completeTitle}</h2><p>{copy.completeSubtitle}</p><div className="completion-stars" aria-label={`${roundStars} ${copy.stars}`}>{'⭐'.repeat(Math.min(roundStars, 24))}</div><p className="completion-stat">{copy.starsEarned}: <strong>{roundStars}</strong> {copy.stars}</p>{completionBonusAwarded && <p className="completion-stat completion-bonus">{copy.completionBonus}</p>}<p className="completion-stat">{copy.accuracy}: <strong>{session.length ? Math.round((correctAnswers / session.length) * 100) : 0}%</strong></p><p className="completion-stat">{copy.currentStars}: ⭐ <strong>{totalStars}</strong></p><div className="completion-actions"><button className="primary-action" onClick={restartGame}><RotateCcw size={16} />{copy.playAgain}</button><button className="secondary-action" onClick={() => { setEditingPracticeId(null); setPage('create') }}>继续学习</button><button className="secondary-action" onClick={() => requestExport(session, practiceName)}><span>导出结果 PDF</span></button><button className="secondary-action" onClick={() => setPage('home')}>返回首页</button></div></section> : <>
        <div className="play-layout"><div className="play-rail"><div className="rail-number">{String(questionIndex + 1).padStart(2, '0')}</div><span className="rail-line" /><span className="rail-game">{activeGameLabel}</span></div><div className="play-content">
          {currentWord && activeGame === 'pinyin' && <PinyinQuiz key={`${activeGame}-${questionIndex}`} word={currentWord} distractors={distractorsFor(currentWord, 'pinyin')} rate={rate} answer={answer} starsEarned={questionStars} showImages={practiceSettings.showImages} allowSpeech={practiceSettings.allowSpeech} onAnswer={submitAnswer} copy={copy} />}
          {currentWord && activeGame === 'word' && <WordQuiz key={`${activeGame}-${questionIndex}`} word={currentWord} distractors={distractorsFor(currentWord, 'chinese')} rate={rate} answer={answer} starsEarned={questionStars} showImages={practiceSettings.showImages} allowSpeech={practiceSettings.allowSpeech} onAnswer={submitAnswer} copy={copy} />}
          {activeGame === 'matching' && <MatchingGame key={`${activeGame}-${questionIndex}`} words={currentPairRound} answer={answer} starsEarned={questionStars} showImages={practiceSettings.showImages} onPairCorrect={correctPair} onWrongPair={incorrectPair} onComplete={completeMatching} copy={copy} />}
          {currentWord && activeGame === 'flashcards' && <FlashCards key={`${activeGame}-${questionIndex}`} word={currentWord} language={language} rate={rate} answer={answer} starsEarned={questionStars} showImages={practiceSettings.showImages} showPinyin={practiceSettings.showPinyin} allowSpeech={practiceSettings.allowSpeech} onLearned={learnFlashcard} onNeedPractice={skipFlashcard} copy={copy} />}
        </div></div>
        <div className="play-actions"><button className="secondary-action" onClick={restartGame}><RotateCcw size={15} /><span>{copy.restart}</span></button><button className="secondary-action return-action" onClick={returnFromGame}><ArrowLeft size={15} /><span>{copy.returnToGames}</span></button><button className="primary-action next-action" onClick={nextQuestion} disabled={answer === null}>{questionIndex + 1 === gameQuestionCount ? copy.completeTitle : copy.next}<ArrowRight size={16} /></button></div>
      </>}
    </main>}

    {page === 'print' && exportSettings && <PrintableDocument title={printTitle} words={printWords} language={exportSettings.language} mode={exportSettings.mode as ExportMode} showAnswers={exportSettings.showAnswers} fields={exportSettings.fields} result={printResult ?? undefined} onClose={() => setPage(printReturnPage)} />}
    {exportOpen && <PdfExportDialog language={language} result={printResult ?? undefined} onClose={() => setExportOpen(false)} onExport={beginPrint} />}
  </div>
}

export default App
