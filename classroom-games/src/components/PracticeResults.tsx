import { ArrowLeft, Clock3, Trophy } from 'lucide-react'
import { useState } from 'react'
import type { PracticeResult } from '../types'

type PracticeResultsProps = {
  practiceName: string
  results: PracticeResult[]
  loading: boolean
  error: string
  onBack: () => void
  onExport: (result: PracticeResult) => void
}

function duration(result: PracticeResult) {
  const seconds = Math.max(0, Math.floor((new Date(result.endTime).getTime() - new Date(result.startTime).getTime()) / 1000))
  return `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`
}

export default function PracticeResults({ practiceName, results, loading, error, onBack, onExport }: PracticeResultsProps) {
  const [selected, setSelected] = useState<string | null>(null)
  const current = results.find((result) => result.id === selected)

  return <main className="management-page"><header className="management-heading"><div><button className="back-button" onClick={onBack}><ArrowLeft size={15} />返回练习列表</button><span className="tool-kicker">学生成绩 · {results.length} 份记录</span><h1>{practiceName}</h1><p>成绩由学生提交并由数据库校验答案，详情仅练习所属教师可见。</p></div><Trophy size={27} className="heading-icon" /></header>
    {error && <p className="form-error" role="alert">{error}</p>}
    {loading ? <p className="empty-message">正在读取成绩…</p> : current ? <section className="result-detail"><div className="result-detail-actions"><button className="secondary-action" onClick={() => setSelected(null)}><ArrowLeft size={14} />所有学生</button><button className="primary-action" onClick={() => onExport(current)}>导出成绩 PDF</button></div><h2>{current.studentName}</h2><p>{practiceName} · {new Date(current.endTime).toLocaleString()}</p><div className="result-metrics"><span>得分 <strong>{current.score} / {current.maxScore}</strong></span><span>正确率 <strong>{current.accuracy}%</strong></span><span>奖励 <strong>⭐ {current.stars}</strong></span><span><Clock3 size={14} /> {duration(current)}</span></div><div className="result-answer-list">{current.answers.map((answer, index) => <article key={answer.itemId} className={answer.correct ? 'answer-correct' : 'answer-incorrect'}><span>{index + 1}</span><strong>{answer.chinese}</strong><span>{answer.pinyin}</span><span>{answer.correct ? '✓ 正确' : `你的答案：${(answer.displayAnswer ?? answer.selectedAnswer) || '未答'} · 正确：${answer.correctAnswer}`}</span></article>)}</div></section> : results.length ? <div className="student-results-list">{results.map((result) => <button className="student-result-row" key={result.id} onClick={() => setSelected(result.id)}><span className="student-result-avatar">{result.studentName.slice(0, 1)}</span><span className="student-result-name"><strong>{result.studentName}</strong><small>{new Date(result.endTime).toLocaleString()}</small></span><strong>{result.accuracy}%</strong><span>⭐ {result.stars}</span><span>{result.score}/{result.maxScore}</span></button>)}</div> : <section className="empty-state"><h2>还没有学生提交成绩</h2><p>发布并分享练习链接后，学生提交结果会显示在这里。</p></section>}
  </main>
}