import { useState } from 'react'
import { X } from 'lucide-react'
import { languageOptions } from '../data/translations'
import type { ExportFields, ExportMode, ExportResult, Language, VocabularyWord } from '../types'
import WordImage from './WordImage'

type PrintableDocumentProps = {
  title: string
  words: VocabularyWord[]
  language: Language
  mode: ExportMode
  showAnswers: boolean
  fields: ExportFields
  result?: ExportResult
  onClose: () => void
}

function ImageCredit({ word }: { word: VocabularyWord }) {
  if (!word.image) return <span className="print-image-credit">图片未设置</span>
  return <span className="print-image-credit">{word.image.source} · {word.image.license}{word.image.creator ? ` · ${word.image.creator}` : ''}{word.image.pageUrl && <> · <a href={word.image.pageUrl}>来源页</a></>}</span>
}

function PrintableWord({ word, language, index, workbook, fields }: { word: VocabularyWord; language: Language; index: number; workbook: boolean; fields: ExportFields }) {
  return <article className={`print-word ${workbook ? 'print-workbook-word' : ''}`}>
    <span className="print-number">{String(index + 1).padStart(2, '0')}</span>
    {fields.image && <div className="print-image-wrap"><WordImage image={word.image} alt={word.chinese} className="print-image" /><ImageCredit word={word} /></div>}
    <div className="print-word-content">
      {fields.chinese && <h2>{word.chinese}</h2>}
      {fields.pinyin && <p className="print-pinyin">{word.pinyin}</p>}
      {!workbook && <div className="print-translations">{languageOptions.filter((option) => fields[option.id]).map((option) => <p className="print-translation" key={option.id}><strong>{option.name}:</strong> {word.translations[option.id]}</p>)}</div>}
      {fields.speechHint && <p className="print-speech-hint">🔊 {word.chinese} · {word.translations[language]}</p>}
      {workbook && <p className="answer-blank">{String(index + 1)}. 中文：________________________________</p>}
    </div>
  </article>
}

export default function PrintableDocument({ title, words, language, mode, showAnswers, result, fields, onClose }: PrintableDocumentProps) {
  const [printing, setPrinting] = useState(false)
  const languageName = languageOptions.find((option) => option.id === language)?.name ?? language
  const showKey = mode === 'answers' || showAnswers

  async function printDocument() {
    setPrinting(true)
    await document.fonts.ready
    const images = Array.from(document.querySelectorAll<HTMLImageElement>('.print-view img'))
    await Promise.all(images.map((image) => image.decode().catch(() => undefined)))
    window.print()
    setPrinting(false)
  }

  return <section className="print-view">
    <div className="print-toolbar"><span><strong>打印预览</strong><small>{title} · {words.length} 个词 · {languageName}</small></span><div><button className="secondary-action" onClick={onClose}><X size={15} />关闭</button><button className="primary-action" onClick={printDocument} disabled={printing}>{printing ? '准备页面…' : '打印 / 保存 PDF'}</button></div></div>
    <div className="print-document">
      <header className="print-document-header"><span>中文词汇 · {languageName}</span><h1>{title}</h1><p>{mode === 'workbook' ? '学生练习册' : mode === 'answers' ? '教师答案版' : mode === 'results' ? '练习结果' : '词汇学习表'}</p></header>
      {mode === 'results' && result && fields.results && <section className="print-results-summary"><h2>练习结果</h2><p>得分：{result.score} / {result.maxScore}</p><p>正确率：{result.accuracy}%</p>{fields.stars && <p>本次获得：{'⭐'.repeat(Math.min(result.starsEarned, 24))} {result.starsEarned} 星</p>}</section>}
      {mode === 'results' && result && fields.errorAnalysis && result.incorrect?.length ? <section className="print-error-analysis"><h2>错题分析</h2>{result.incorrect.map((item, index) => <p key={`${item.chinese}-${index}`}>{item.chinese} · {item.pinyin} · 你的答案：{item.selected || '未答'} · 正确答案：{item.correct}</p>)}</section> : null}
      {fields.exercises && (mode === 'workbook' ? <section className="print-workbook"><h2>根据拼音写出汉字</h2><div className="print-word-list">{words.map((word, index) => <PrintableWord key={word.id} word={word} language={language} index={index} workbook fields={fields} />)}</div></section> : <div className="print-word-list">{words.map((word, index) => <PrintableWord key={word.id} word={word} language={language} index={index} workbook={false} fields={fields} />)}</div>)}
      {(showKey || fields.answers) && mode !== 'answers' && <section className="print-answer-key"><h2>教师答案</h2>{words.map((word, index) => <p key={word.id}>{fields.chinese && `${index + 1}. ${word.chinese}`}{fields.pinyin && ` · ${word.pinyin}`}{fields[language] && ` · ${word.translations[language]}`}</p>)}</section>}
      <footer className="print-document-footer">词汇练习 · 图片来源及许可信息随词条标注</footer>
    </div>
  </section>
}