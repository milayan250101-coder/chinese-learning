import { ArrowRight, Clock3 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { languageOptions } from '../data/translations'
import type { PracticeAnswer, VocabularyWord } from '../types'
import { loadPublishedPractice, startStudentAttempt, submitStudentAttempt, type HostedPractice } from '../services/hostedPracticeService'
import SpeechButton from './SpeechButton'
import WordImage from './WordImage'

type StudentPracticePageProps = { shareCode: string; onBack: () => void }
type HostedItem = { id: string; word: VocabularyWord }
type StudentReport = { score: number; maxScore: number; accuracy: number; stars: number; incorrect: { chinese: string; pinyin: string; translation: Record<string, string>; selected: string }[]; startTime?: string; endTime?: string }

function makeDistractors(items: HostedItem[], current: HostedItem, field: 'chinese' | 'pinyin') {
  return items.filter((item) => item.id !== current.id && item.word[field] !== current.word[field]).slice(0, 3)
}

export default function StudentPracticePage({ shareCode, onBack }: StudentPracticePageProps) {
  const [practice, setPractice] = useState<HostedPractice | null>(null)
  const [studentName, setStudentName] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [answers, setAnswers] = useState<PracticeAnswer[]>([])
  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const [report, setReport] = useState<StudentReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [startTime, setStartTime] = useState('')
  const [flipped, setFlipped] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    loadPublishedPractice(shareCode).then((data) => { if (!cancelled) setPractice(data) }).catch((cause) => { if (!cancelled) setError(cause instanceof Error ? cause.message : '无法加载此练习。') }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [shareCode])

  const items: HostedItem[] = practice?.items ?? []
  const current = items[index]
  const targetLanguage = practice?.language as keyof VocabularyWord['translations'] | undefined
  const languageName = languageOptions.find((option) => option.id === targetLanguage)?.name ?? ''
  const selectedGame = practice?.settings.gameIds?.[index % Math.max(practice.settings.gameIds.length, 1)] ?? 'pinyin'
  const choiceField = selectedGame === 'pinyin' ? 'pinyin' : 'chinese'
  const choices = current ? [current, ...makeDistractors(items, current, choiceField)].sort((left, right) => left.id.localeCompare(right.id)) : []

  async function begin() {
    if (!practice || !studentName.trim()) return
    setSubmitting(true)
    setError('')
    try {
      const started = new Date().toISOString()
      const id = await startStudentAttempt(shareCode, studentName)
      setStartTime(started)
      setSessionId(id)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '无法开始练习。')
    } finally {
      setSubmitting(false)
    }
  }

  async function submitCurrentAnswer(selectedId: string) {
    if (!current || !practice || answers.some((answer) => answer.itemId === current.id)) return
    const selectedItem = items.find((item) => item.id === selectedId)
    const selectedAnswer = selectedItem?.word.chinese ?? ''
    const nextAnswer: PracticeAnswer = { itemId: current.id, selectedAnswer, displayAnswer: selectedItem?.word[choiceField] ?? '', correct: selectedId === current.id }
    const updatedAnswers = [...answers, nextAnswer]
    setAnswers(updatedAnswers)
    setSelected(null)
    setFlipped(false)
    if (index + 1 < items.length) {
      setIndex((value) => value + 1)
      return
    }
    setSubmitting(true)
    try {
      const result = await submitStudentAttempt(sessionId, updatedAnswers.map((answer) => ({ itemId: answer.itemId, answer: answer.selectedAnswer, displayAnswer: answer.displayAnswer })))
      const completed = { ...result, startTime, endTime: new Date().toISOString() }
      setReport(completed)
      const currentStars = Number(window.localStorage.getItem('chineseVocabularyStars') ?? 0)
      window.localStorage.setItem('chineseVocabularyStars', String(currentStars + result.stars))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '提交成绩失败，请检查网络后重试。')
      setAnswers(answers)
    } finally {
      setSubmitting(false)
    }
  }

  async function advance() {
    if (!selected) return
    await submitCurrentAnswer(selected)
  }

  if (loading) return <main className="student-shell"><p>正在加载练习…</p></main>
  if (error && !practice) return <main className="student-shell"><button className="secondary-action" onClick={onBack}>返回</button><section className="student-error"><h1>无法打开练习</h1><p>{error}</p></section></main>
  if (!practice) return null

  if (!sessionId) return <main className="student-shell"><header className="student-intro"><span className="student-kicker">中文词汇练习</span><h1>{practice.name}</h1><p>老师：{practice.teacherName}</p><p>{items.length} 个词 · {languageName}</p></header><form className="student-name-form" onSubmit={(event) => { event.preventDefault(); void begin() }}><label>请输入你的名字<input value={studentName} onChange={(event) => setStudentName(event.target.value)} required maxLength={80} placeholder="例如：Alice" /></label><button className="primary-action" disabled={submitting || !studentName.trim()}>{submitting ? '正在开始…' : '开始练习'} <ArrowRight size={16} /></button></form>{error && <p className="form-error" role="alert">{error}</p>}</main>

  if (report) {
    const elapsed = Math.max(0, Math.floor((new Date(report.endTime ?? '').getTime() - new Date(report.startTime ?? '').getTime()) / 1000))
    const duration = `${Math.floor(elapsed / 60)} 分 ${elapsed % 60} 秒`
    return <main className="student-shell"><section className="student-report"><span className="completion-mark">🎉</span><span className="student-kicker">练习完成</span><h1>{studentName}</h1><h2>{practice.name}</h2><p className="student-report-score">得分 {report.score} / {report.maxScore}</p><p>正确率：{report.accuracy}%</p><p>获得：{'⭐'.repeat(Math.min(report.stars, 20))} {report.stars}</p><p><Clock3 size={14} /> 用时：{duration}</p>{report.incorrect.length > 0 && <section className="student-mistakes"><h3>需要复习</h3>{report.incorrect.map((item, row) => <article key={`${item.chinese}-${row}`}><strong>❌ {item.chinese}</strong><span>你的答案：{item.selected}</span><span>正确拼音：{item.pinyin}</span><span>{languageName}：{item.translation[targetLanguage!]}</span></article>)}</section>}<button className="primary-action" onClick={onBack}>完成</button></section></main>
  }

  if (!current) return <main className="student-shell"><p>此练习还没有题目。</p></main>
  const isFlashcard = selectedGame === 'flashcards'
  return <main className="student-shell"><header className="student-game-heading"><div><span className="student-kicker">{practice.name} · {studentName}</span><h1>第 {index + 1} / {items.length} 题</h1></div><strong>⭐ {index ? answers.reduce((sum, answer) => sum + Number(answer.correct), 0) : 0}</strong></header><div className="student-progress"><span style={{ width: `${((index + 1) / items.length) * 100}%` }} /></div>
    <section className="student-question">{isFlashcard ? <><button className={`student-flashcard ${flipped ? 'revealed' : ''}`} onClick={() => setFlipped((value) => !value)}><strong>{current.word.chinese}</strong>{practice.settings.showImages && current.word.image && <WordImage image={current.word.image} alt={current.word.chinese} className="student-image" />}{flipped && <>{practice.settings.showPinyin && <span>{current.word.pinyin}</span>}<span>{current.word.translations[targetLanguage!]}</span></>}</button>{practice.settings.allowSpeech && <div className="student-speech-controls"><SpeechButton value={current.word.chinese} language="zh" rate={1} label={current.word.chinese} /><SpeechButton value={current.word.translations[targetLanguage!]} language={targetLanguage!} rate={1} label={current.word.translations[targetLanguage!]} /></div>}<div className="student-choice-actions"><button className="primary-action" onClick={() => void submitCurrentAnswer(current.id)} disabled={!flipped || submitting}>我记住了</button><button className="secondary-action" onClick={() => void submitCurrentAnswer('')} disabled={!flipped || submitting}>还需要练习</button></div></> : <><p>{selectedGame === 'pinyin' ? '请选择正确的拼音' : selectedGame === 'matching' ? '将拼音与汉字匹配' : '根据拼音选择汉字'}</p><div className="student-word-prompt">{selectedGame === 'pinyin' ? current.word.chinese : current.word.pinyin}{practice.settings.showImages && current.word.image && <WordImage image={current.word.image} alt={current.word.chinese} className="student-image" />}</div><div className="student-choices">{choices.map((choice) => <div key={choice.id} className={`student-choice ${selected === choice.id ? 'selected' : ''}`}><button onClick={() => setSelected(choice.id)}>{choice.word[choiceField]}</button>{choiceField === 'chinese' && practice.settings.allowSpeech && <SpeechButton value={choice.word.chinese} language="zh" rate={1} label={choice.word.chinese} />}</div>)}</div><div className="student-choice-actions"><button className="primary-action" onClick={() => void advance()} disabled={!selected || submitting}>{index + 1 === items.length ? '提交练习' : '下一题'} <ArrowRight size={16} /></button></div></>}</section>{error && <p className="form-error" role="alert">{error}</p>}</main>
}