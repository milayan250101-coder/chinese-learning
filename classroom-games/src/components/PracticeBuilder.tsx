import { BookOpenCheck, Check, FileDown, Play, Volume2 } from 'lucide-react'
import { languageOptions } from '../data/translations'
import type { Language, VocabularyWord } from '../types'
import type { PracticeFolder, PracticeSettings } from '../types'
import SpeechButton from './SpeechButton'
import WordImage from './WordImage'

type PracticeBuilderProps = {
  words: VocabularyWord[]
  selectedIds: string[]
  onSelectionChange: (ids: string[]) => void
  language: Language
  rate: number
  practiceName: string
  onNameChange: (name: string) => void
  onGenerate: () => void
  onExport: () => void
  editing: boolean
  folders: PracticeFolder[]
  folderId: string
  onFolderIdChange: (id: string) => void
  studentName: string
  onStudentNameChange: (name: string) => void
  settings: PracticeSettings
  onSettingsChange: (settings: PracticeSettings) => void
}

export default function PracticeBuilder({ words, selectedIds, onSelectionChange, language, rate, practiceName, onNameChange, onGenerate, onExport, editing, folders, folderId, onFolderIdChange, studentName, onStudentNameChange, settings, onSettingsChange }: PracticeBuilderProps) {
  const canGenerate = selectedIds.length >= 4
  const allSelected = words.length > 0 && selectedIds.length === words.length

  function toggle(id: string) {
    onSelectionChange(selectedIds.includes(id) ? selectedIds.filter((item) => item !== id) : [...selectedIds, id])
  }

  return <main className="practice-builder">
    <header className="management-heading"><div><span className="tool-kicker">练习工作台 · {selectedIds.length} 个词</span><h1>{editing ? '编辑练习' : '创建练习'}</h1><p>从统一词库选择词汇，四种游戏都会使用同一组汉字、拼音、翻译和图片。</p></div><BookOpenCheck size={28} className="heading-icon" /></header>
    <section className="builder-settings"><label className="practice-name-field">练习名称<input value={practiceName} onChange={(event) => onNameChange(event.target.value)} placeholder="例如：HSK1 第1课、日常问候" maxLength={70} /></label><label className="practice-name-field">学生姓名<input value={studentName} onChange={(event) => onStudentNameChange(event.target.value)} placeholder="例如：Alice（可留空）" maxLength={60} /></label><label className="practice-name-field">文件夹<select value={folderId} onChange={(event) => onFolderIdChange(event.target.value)}>{folders.map((folder) => <option key={folder.id} value={folder.id}>{folder.name}</option>)}</select></label><div className="builder-actions"><button className="secondary-action" onClick={onExport} disabled={selectedIds.length === 0}><FileDown size={15} />导出 PDF</button><button className="primary-action" onClick={onGenerate} disabled={!canGenerate}><Play size={15} />{editing ? '保存并生成游戏' : '生成练习'}</button></div></section>
    <section className="practice-config"><fieldset><legend>包含的游戏</legend>{(['pinyin', 'word', 'matching', 'flashcards'] as const).map((game) => <label key={game}><input type="checkbox" checked={settings.gameIds.includes(game)} onChange={(event) => onSettingsChange({ ...settings, gameIds: event.target.checked ? [...settings.gameIds, game] : settings.gameIds.filter((item) => item !== game) })} />{({ pinyin: '看汉字选拼音', word: '看拼音选汉字', matching: '拼音/汉字连线', flashcards: '翻翻卡' } as const)[game]}</label>)}</fieldset><label>每个游戏题数<select value={settings.questionCount} onChange={(event) => onSettingsChange({ ...settings, questionCount: event.target.value === 'all' ? 'all' : Number(event.target.value) })}>{[10, 20, 30, 50, 100].map((count) => <option key={count} value={count}>{count}</option>)}<option value="all">全部所选词汇</option></select></label><label><input type="checkbox" checked={settings.showImages} onChange={(event) => onSettingsChange({ ...settings, showImages: event.target.checked })} />显示图片</label><label><input type="checkbox" checked={settings.showPinyin} onChange={(event) => onSettingsChange({ ...settings, showPinyin: event.target.checked })} />显示拼音</label><label><input type="checkbox" checked={settings.allowSpeech} onChange={(event) => onSettingsChange({ ...settings, allowSpeech: event.target.checked })} />允许发音</label></section>
    {!canGenerate && <p className="builder-warning" role="status">请至少选择 4 个词汇，才能生成四种游戏并提供互不重复的选择项。</p>}
    <div className="list-heading builder-list-heading"><div><h2>选择练习词汇</h2><p>未保存的修改不会覆盖词汇库；请先在“词汇管理”中保存词条编辑。</p></div><button className="text-button" onClick={() => onSelectionChange(allSelected ? [] : words.map((word) => word.id))}>{allSelected ? '取消全选' : '全选词汇'}</button></div>
    <div className="practice-word-grid">{words.map((word) => <article key={word.id} className={`practice-word-card ${selectedIds.includes(word.id) ? 'selected' : ''}`}><input id={`select-${word.id}`} type="checkbox" checked={selectedIds.includes(word.id)} onChange={() => toggle(word.id)} /><label htmlFor={`select-${word.id}`} className="practice-word-select"><span className="card-check"><Check size={13} /></span><strong className="practice-hanzi">{word.chinese}</strong><WordImage image={word.image} alt={word.chinese} className="practice-image" /><span className="practice-pinyin">{word.pinyin}</span><span className="practice-translation">{word.translations[language]}</span></label><div className="practice-card-translation"><SpeechButton value={word.chinese} language="zh" rate={rate} label={`播放${word.chinese}`} /><SpeechButton value={word.translations[language]} language={language} rate={rate} label={`播放${word.translations[language]}`} /></div></article>)}</div>
    <div className="builder-footnote"><Volume2 size={14} /><span>发音可用当前语音工具播放，内容来自选中的词条。</span><span className="builder-language">{languageOptions.find((option) => option.id === language)?.flag} {languageOptions.find((option) => option.id === language)?.name}</span></div>
  </main>
}