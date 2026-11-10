import { FileDown, X } from 'lucide-react'
import { useState } from 'react'
import { languageOptions } from '../data/translations'
import type { ExportFields, ExportMode, ExportResult, Language } from '../types'

export type ExportSettings = { language: Language; mode: ExportMode; showAnswers: boolean; fields: ExportFields }

const defaultFields: ExportFields = { chinese: true, pinyin: true, en: true, de: true, fr: true, es: true, it: true, image: true, speechHint: false, exercises: true, answers: false, results: true, stars: true, errorAnalysis: true }
const fieldOptions: { key: keyof ExportFields; label: string }[] = [
  { key: 'chinese', label: '中文' }, { key: 'pinyin', label: '拼音' }, { key: 'en', label: '英语' },
  { key: 'de', label: '德语' }, { key: 'fr', label: '法语' }, { key: 'es', label: '西班牙语' },
  { key: 'it', label: '意大利语' }, { key: 'image', label: '图片' }, { key: 'speechHint', label: '发音提示' },
  { key: 'exercises', label: '游戏练习' }, { key: 'answers', label: '答案' }, { key: 'results', label: '成绩' },
  { key: 'stars', label: '星星' }, { key: 'errorAnalysis', label: '错题分析' },
]

type PdfExportDialogProps = {
  language: Language
  result?: ExportResult
  onClose: () => void
  onExport: (settings: ExportSettings) => void
}

export default function PdfExportDialog({ language, result, onClose, onExport }: PdfExportDialogProps) {
  const [selectedLanguage, setSelectedLanguage] = useState(language)
  const [mode, setMode] = useState<ExportMode>(result ? 'results' : 'study')
  const [fields, setFields] = useState<ExportFields>(defaultFields)

  return <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><section className="export-dialog" role="dialog" aria-modal="true" aria-labelledby="export-title">
    <header className="dialog-heading"><div><span className="tool-kicker">PRINT · PDF</span><h2 id="export-title">导出词汇和练习</h2></div><button className="icon-button" onClick={onClose} aria-label="关闭"><X size={18} /></button></header>
    <label className="export-language">翻译语言<select value={selectedLanguage} onChange={(event) => setSelectedLanguage(event.target.value as Language)}>{languageOptions.map((option) => <option key={option.id} value={option.id}>{option.flag} {option.name}</option>)}</select></label>
    <fieldset className="export-modes"><legend>导出内容</legend>
      <label><input type="radio" name="export-mode" checked={mode === 'study'} onChange={() => setMode('study')} /><span><strong>词汇学习表</strong><small>汉字、图片、拼音和所选语言翻译</small></span></label>
      <label><input type="radio" name="export-mode" checked={mode === 'workbook'} onChange={() => setMode('workbook')} /><span><strong>学生练习册</strong><small>题目、图片和书写答题区域</small></span></label>
      <label><input type="radio" name="export-mode" checked={mode === 'answers'} onChange={() => setMode('answers')} /><span><strong>教师答案版</strong><small>包含汉字、拼音、图片和翻译</small></span></label>
      {result && <label><input type="radio" name="export-mode" checked={mode === 'results'} onChange={() => setMode('results')} /><span><strong>练习结果</strong><small>包含得分、正确率、本次星星和词汇表</small></span></label>}
    </fieldset>
    <fieldset className="export-fields"><legend>包含字段（可多选）</legend><div>{fieldOptions.map(({ key, label }) => <label key={key}><input type="checkbox" checked={fields[key]} onChange={(event) => setFields((current) => ({ ...current, [key]: event.target.checked }))} /><span>{label}</span></label>)}</div></fieldset>
    <p className="export-note">将打开系统打印对话框；选择“另存为 PDF”。中文显示依赖系统可用的中文字体，打印前会等待字体和图片加载。</p>
    <footer className="dialog-actions"><button className="secondary-action" onClick={onClose}>取消</button><button className="primary-action" onClick={() => onExport({ language: selectedLanguage, mode, showAnswers: fields.answers || mode === 'answers', fields })}><FileDown size={15} />生成 PDF</button></footer>
  </section></div>
}