import { Check, Grid2X2, Languages, List, LoaderCircle, Pencil, Plus, Search, Sparkles, Trash2, Upload, X } from 'lucide-react'
import { useState } from 'react'
import { languageOptions } from '../data/translations'
import type { Language, VocabularyImage, VocabularyWord } from '../types'
import { generatePinyin } from '../services/pinyinService'
import { translateChineseWordToAll } from '../services/translationService'
import { searchWikimediaImages, type CommonsImageResult } from '../services/commonsSearch'
import SpeechButton from './SpeechButton'
import WikimediaSearch from './WikimediaSearch'
import WordImage from './WordImage'

type VocabularyManagerProps = {
  words: VocabularyWord[]
  language: Language
  rate: number
  selectedIds: string[]
  onSelectedIdsChange: (ids: string[]) => void
  onSaveWord: (word: VocabularyWord) => void
  onAddWords: (words: VocabularyWord[]) => void
  onDeleteWord: (id: string) => void
  onBulkDelete: (ids: string[]) => void
  onCreatePractice: () => void
  selectionLimit: number | 'custom' | 'all'
  onSelectionLimitChange: (limit: number | 'custom' | 'all') => void
}

type BatchStatus = { pinyin: string; translations: string; images: string; candidates: CommonsImageResult[] }

type Draft = {
  chinese: string
  pinyin: string
  pinyinSource: 'automatic' | 'manual'
  translations: Record<Language, string>
  translationSources: Record<Language, 'automatic' | 'manual'>
  category: string
}

const emptyTranslations = (): Record<Language, string> => ({ en: '', de: '', fr: '', es: '', it: '' })
const emptySources = (): Record<Language, 'automatic' | 'manual'> => ({ en: 'automatic', de: 'automatic', fr: 'automatic', es: 'automatic', it: 'automatic' })
const blankDraft = (): Draft => ({ chinese: '', pinyin: '', pinyinSource: 'automatic', translations: emptyTranslations(), translationSources: emptySources(), category: '' })

function createId() {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

export default function VocabularyManager({ words, language, rate, selectedIds, onSelectedIdsChange, onSaveWord, onAddWords, onDeleteWord, onBulkDelete, onCreatePractice, selectionLimit, onSelectionLimitChange }: VocabularyManagerProps) {
  const orderedLanguages = [...languageOptions].sort((left, right) => Number(right.id === language) - Number(left.id === language))
  const [draft, setDraft] = useState<Draft>(blankDraft)
  const [manualUrl, setManualUrl] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [searchWord, setSearchWord] = useState<VocabularyWord | null>(null)
  const [bulkText, setBulkText] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [pinyinStatus, setPinyinStatus] = useState('')
  const [translationStatus, setTranslationStatus] = useState('')
  const [pinyinLoading, setPinyinLoading] = useState(false)
  const [translationLoading, setTranslationLoading] = useState(false)
  const [plainBulkText, setPlainBulkText] = useState('')
  const [batchRunning, setBatchRunning] = useState(false)
  const [batchProgress, setBatchProgress] = useState({ done: 0, total: 0, current: '' })
  const [batchStatuses, setBatchStatuses] = useState<Record<string, BatchStatus>>({})
  const [customLimit, setCustomLimit] = useState('15')
  const [selectedLimitMessage, setSelectedLimitMessage] = useState('')
  const [view, setView] = useState<'list' | 'grid'>(() => window.localStorage.getItem('hanzi-island-vocabulary-view') === 'grid' ? 'grid' : 'list')

  function editWord(word: VocabularyWord) {
    setEditingId(word.id)
    setDraft({
      chinese: word.chinese,
      pinyin: word.pinyin,
      pinyinSource: word.pinyinSource ?? 'manual',
      translations: { ...word.translations },
      translationSources: Object.fromEntries(languageOptions.map(({ id }) => [id, word.translationSources?.[id] ?? (word.translations[id] ? 'manual' : 'automatic')])) as Record<Language, 'automatic' | 'manual'>,
      category: word.category,
    })
    setManualUrl(word.image?.source === 'Manual URL' ? word.image.url : '')
    setError('')
    setPinyinStatus('')
    setTranslationStatus('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function clearForm() {
    setEditingId(null)
    setDraft(blankDraft())
    setManualUrl('')
    setError('')
    setPinyinStatus('')
    setTranslationStatus('')
  }

  async function autoGeneratePinyin() {
    if (!draft.chinese.trim()) {
      setPinyinStatus('请先输入中文词语。')
      return
    }
    if (draft.pinyinSource === 'manual' && draft.pinyin.trim()) {
      setPinyinStatus('拼音已手动修改，未覆盖。清空拼音字段后可重新生成。')
      return
    }
    setPinyinLoading(true)
    try {
      const generated = await generatePinyin(draft.chinese)
      setDraft((current) => ({ ...current, pinyin: generated, pinyinSource: 'automatic' }))
      setPinyinStatus('已按词语上下文生成拼音，请核对声调。')
    } catch {
      setPinyinStatus('无法生成拼音，请检查输入是否为中文词语。')
    } finally {
      setPinyinLoading(false)
    }
  }

  async function autoTranslate() {
    if (!draft.chinese.trim()) {
      setTranslationStatus('请先输入中文词语。')
      return
    }
    setTranslationLoading(true)
    setTranslationStatus('正在逐个查询五种语言的翻译服务…')
    try {
      const result = await translateChineseWordToAll(draft.chinese.trim())
      const protectedCount = languageOptions.filter(({ id }) => result.translations[id] && draft.translationSources[id] === 'manual' && draft.translations[id].trim()).length
      const availableCount = Object.values(result.translations).filter(Boolean).length
      const generatedCount = availableCount - protectedCount
      setDraft((current) => {
        const translations = { ...current.translations }
        const translationSources = { ...current.translationSources }
        for (const option of languageOptions) {
          const generated = result.translations[option.id]
          const isManuallyProtected = current.translationSources[option.id] === 'manual' && Boolean(current.translations[option.id].trim())
          if (generated && !isManuallyProtected) {
            translations[option.id] = generated
            translationSources[option.id] = 'automatic'
          }
        }
        return { ...current, translations, translationSources }
      })
      const failedNames = result.failures.map((id) => languageOptions.find((option) => option.id === id)?.name ?? id)
      if (!generatedCount && !failedNames.length && protectedCount) setTranslationStatus('翻译服务已返回译文；现有手动内容均已保留，没有覆盖。')
      else if (!availableCount) setTranslationStatus('翻译服务暂不可用，未返回新译文；请检查网络或手动填写。')
      else if (failedNames.length) setTranslationStatus(`已生成 ${generatedCount} 种语言翻译；${failedNames.join('、')} 暂不可用，未覆盖手动内容。请核对自动译文。`)
      else setTranslationStatus(`已返回 ${generatedCount} 种语言的机器译文，手动修改项保持不变；请核对后保存。`)
    } catch {
      setTranslationStatus('翻译服务暂不可用，未返回新译文；请检查网络或手动填写。')
    } finally {
      setTranslationLoading(false)
    }
  }

  async function generateBulk() {
    const terms = [...new Set(plainBulkText.split(/[\n,，、]+/).map((value) => value.trim()).filter(Boolean))]
    const existing = new Set(words.map((word) => word.chinese))
    const uniqueTerms = terms.filter((word) => !existing.has(word))
    if (!uniqueTerms.length) {
      setNotice(terms.length ? '这些词已在词库中，未重复添加。' : '请先输入词语，每行一个或用逗号分隔。')
      return
    }
    setBatchRunning(true)
    setBatchProgress({ done: 0, total: uniqueTerms.length, current: '' })
    setBatchStatuses({})
    const imported: VocabularyWord[] = []
    for (const chinese of uniqueTerms) {
      setBatchProgress((current) => ({ ...current, current: chinese }))
      let pinyin = ''
      let translations: Record<Language, string> = { en: '', de: '', fr: '', es: '', it: '' }
      let image: VocabularyImage | null = null
      const status: BatchStatus = { pinyin: '处理中', translations: '处理中', images: '处理中', candidates: [] }
      setBatchStatuses((current) => ({ ...current, [chinese]: status }))
      try {
        pinyin = await generatePinyin(chinese)
        status.pinyin = '已生成'
      } catch {
        status.pinyin = '生成失败，可编辑'
      }
      try {
        const result = await translateChineseWordToAll(chinese)
        translations = { en: result.translations.en ?? '', de: result.translations.de ?? '', fr: result.translations.fr ?? '', es: result.translations.es ?? '', it: result.translations.it ?? '' }
        status.translations = result.failures.length ? `部分失败：${result.failures.join(', ')}` : '已生成，请核对'
      } catch {
        status.translations = '翻译失败，可单独重试'
      }
      try {
        const result = await searchWikimediaImages(chinese, translations.en)
        status.candidates = result.results.slice(0, 5)
        status.images = status.candidates.length ? `找到 ${status.candidates.length} 张候选，请选图` : '未找到，请手动搜索'
      } catch {
        status.images = '搜索失败，可重试'
      }
      const word: VocabularyWord = {
        id: createId(), chinese, pinyin, pinyinSource: 'automatic', translations,
        translationSources: { en: 'automatic', de: 'automatic', fr: 'automatic', es: 'automatic', it: 'automatic' },
        category: 'custom', image,
      }
      imported.push(word)
      onAddWords([word])
      setBatchStatuses((current) => ({ ...current, [chinese]: { ...status } }))
      setBatchProgress((current) => ({ ...current, done: current.done + 1 }))
    }
    setSelectedLimitMessage('')
    setPlainBulkText('')
    setBatchRunning(false)
    setNotice(`批量处理完成：新增 ${imported.length} 条。图片只显示候选，不会自动选用。`)
  }

  function setViewMode(next: 'list' | 'grid') {
    setView(next)
    window.localStorage.setItem('hanzi-island-vocabulary-view', next)
  }

  function toggleSelected(id: string) {
    const isSelected = selectedIds.includes(id)
    if (!isSelected && typeof selectionLimit === 'number' && selectedIds.length >= selectionLimit) {
      setSelectedLimitMessage(`已达到 ${selectionLimit} 个词的选择上限。`)
      return
    }
    setSelectedLimitMessage('')
    onSelectedIdsChange(isSelected ? selectedIds.filter((item) => item !== id) : [...selectedIds, id])
  }

  function invertSelection() {
    const inverse = words.filter((word) => !selectedIds.includes(word.id))
    const capped = typeof selectionLimit === 'number' ? inverse.slice(0, selectionLimit) : inverse
    onSelectedIdsChange(capped.map((word) => word.id))
  }

  function saveDraft(event: React.FormEvent) {
    event.preventDefault()
    if (!draft.chinese.trim() || !draft.pinyin.trim()) {
      setError('请填写中文汉字和带声调的拼音。')
      return
    }
    if (words.some((word) => word.id !== editingId && word.chinese === draft.chinese.trim())) {
      setError('词库中已存在相同汉字，请编辑现有词条以保持练习选项唯一。')
      return
    }
    const missing = languageOptions.find((option) => !draft.translations[option.id].trim())
    if (missing) {
      setError(`请填写${missing.name}翻译；不确定时可先核对后再保存。`)
      return
    }
    const previous = words.find((word) => word.id === editingId)
    let image: VocabularyImage | null = previous?.image ?? null
    if (manualUrl.trim()) image = { url: manualUrl.trim(), thumbnailUrl: manualUrl.trim(), sourceUrl: manualUrl.trim(), sourceName: 'Manual URL', source: 'Manual URL', license: '请核实图片来源与使用许可', pageUrl: manualUrl.trim() }
    const word: VocabularyWord = {
      id: editingId ?? createId(),
      chinese: draft.chinese.trim(),
      pinyin: draft.pinyin.trim(),
      pinyinSource: draft.pinyinSource,
      translations: Object.fromEntries(languageOptions.map(({ id }) => [id, draft.translations[id].trim()])) as Record<Language, string>,
      translationSources: draft.translationSources,
      category: draft.category.trim() || 'custom',
      image,
    }
    onSaveWord(word)
    setNotice(editingId ? '词汇已更新。' : '词汇已添加。')
    clearForm()
  }

  function importBulk() {
    const rows = bulkText.split('\n').map((line) => line.trim()).filter(Boolean)
    const imported: VocabularyWord[] = []
    let invalid = 0
    const knownChinese = new Set(words.map((word) => word.chinese))
    for (const row of rows) {
      const values = row.includes('|') ? row.split('|').map((value) => value.trim()) : row.split('\t').map((value) => value.trim())
      if (values.length < 7 || values.slice(0, 7).some((value) => !value)) {
        invalid += 1
        continue
      }
      if (knownChinese.has(values[0])) {
        invalid += 1
        continue
      }
      knownChinese.add(values[0])
      imported.push({
        id: createId(), chinese: values[0], pinyin: values[1], pinyinSource: 'manual',
        translations: { en: values[2], de: values[3], fr: values[4], es: values[5], it: values[6] },
        translationSources: { en: 'manual', de: 'manual', fr: 'manual', es: 'manual', it: 'manual' },
        category: 'custom', image: null,
      })
    }
    if (imported.length) onAddWords(imported)
    setNotice(`${imported.length} 条已导入${invalid ? `；${invalid} 行格式不完整，已跳过` : ''}。`)
    setBulkText('')
  }

  function selectImage(image: VocabularyImage) {
    if (searchWord) onSaveWord({ ...searchWord, image })
    setSearchWord(null)
  }

  function selectBatchImage(chinese: string, image: CommonsImageResult) {
    const word = words.find((item) => item.chinese === chinese)
    if (!word) return
    onSaveWord({ ...word, image: { url: image.url, thumbnailUrl: image.thumbnailUrl, sourceUrl: image.sourceUrl, sourceName: image.sourceName, source: image.sourceName, license: image.license, creator: image.creator, pageUrl: image.sourceUrl } })
    setBatchStatuses((current) => ({ ...current, [chinese]: { ...current[chinese], images: `已选择：${image.title}`, candidates: current[chinese]?.candidates ?? [] } }))
  }

  async function retryBatchService(chinese: string, service: 'pinyin' | 'translations' | 'images') {
    const word = words.find((item) => item.chinese === chinese)
    if (!word) return
    const current = batchStatuses[chinese] ?? { pinyin: '', translations: '', images: '', candidates: [] }
    setBatchStatuses((items) => ({ ...items, [chinese]: { ...current, [service]: '正在重试…' } }))
    if (service === 'pinyin') {
      if (word.pinyinSource === 'manual') {
        setBatchStatuses((items) => ({ ...items, [chinese]: { ...current, pinyin: '拼音为手动内容，未覆盖' } }))
        return
      }
      try {
        const pinyin = await generatePinyin(chinese)
        onSaveWord({ ...word, pinyin, pinyinSource: 'automatic' })
        setBatchStatuses((items) => ({ ...items, [chinese]: { ...current, pinyin: '已重新生成' } }))
      } catch {
        setBatchStatuses((items) => ({ ...items, [chinese]: { ...current, pinyin: '生成失败，可手动编辑' } }))
      }
      return
    }
    if (service === 'translations') {
      try {
        const result = await translateChineseWordToAll(chinese)
        const translations = { ...word.translations }
        for (const option of languageOptions) {
          if (word.translationSources?.[option.id] !== 'manual' && result.translations[option.id]) translations[option.id] = result.translations[option.id]!
        }
        onSaveWord({ ...word, translations })
        setBatchStatuses((items) => ({ ...items, [chinese]: { ...current, translations: result.failures.length ? `部分失败：${result.failures.join(', ')}` : '已重新生成，请核对' } }))
      } catch {
        setBatchStatuses((items) => ({ ...items, [chinese]: { ...current, translations: '翻译服务暂不可用' } }))
      }
      return
    }
    try {
      const result = await searchWikimediaImages(chinese, word.translations.en)
      setBatchStatuses((items) => ({ ...items, [chinese]: { ...current, candidates: result.results.slice(0, 5), images: result.results.length ? `找到 ${Math.min(result.results.length, 5)} 张候选，请选图` : '没有找到合适图片，请修改关键词' } }))
    } catch {
      setBatchStatuses((items) => ({ ...items, [chinese]: { ...current, images: '图片服务暂不可用' } }))
    }
  }

  function clearImage(word: VocabularyWord) {
    onSaveWord({ ...word, image: null })
  }

  return <main className="management-page">
    <header className="management-heading"><div><span className="tool-kicker">词汇数据库 · {words.length} 条</span><h1>词汇管理</h1><p>统一维护汉字、拼音、翻译和配图。保存后会同步到游戏和已保存练习。</p></div><span className="selection-count"><strong>{selectedIds.length}</strong> 条已选</span></header>

    <section className="editor-panel">
      <div className="panel-title"><div><span className="panel-symbol"><Plus size={17} /></span><div><h2>{editingId ? '编辑词汇' : '逐条添加词汇'}</h2><p>每种语言单独填写；拼音请保留正确声调。</p></div></div><div className="panel-title-actions"><button className="secondary-action" onClick={autoTranslate} disabled={translationLoading || !draft.chinese.trim()}>{translationLoading ? <LoaderCircle className="spin" size={14} /> : <Languages size={14} />}自动翻译</button>{editingId && <button className="secondary-action" onClick={clearForm}><X size={14} />取消编辑</button>}</div></div>
      <form onSubmit={saveDraft} className="word-editor">
        <div className="core-fields"><label>中文汉字<input value={draft.chinese} onChange={(event) => setDraft({ ...draft, chinese: event.target.value })} placeholder="例如：你好" required disabled={translationLoading || pinyinLoading} /></label><div className="pinyin-field"><label htmlFor="word-pinyin">汉语拼音</label><div className="pinyin-input-row"><input id="word-pinyin" value={draft.pinyin} onChange={(event) => setDraft({ ...draft, pinyin: event.target.value, pinyinSource: event.target.value.trim() ? 'manual' : 'automatic' })} placeholder="例如：nǐ hǎo" required disabled={pinyinLoading} /><button type="button" className="secondary-action auto-pinyin-button" onClick={autoGeneratePinyin} disabled={pinyinLoading || !draft.chinese.trim()}>{pinyinLoading ? <LoaderCircle className="spin" size={13} /> : <Sparkles size={13} />}自动生成拼音</button></div></div><label>主题（可选）<input value={draft.category} onChange={(event) => setDraft({ ...draft, category: event.target.value })} placeholder="日常问候" /></label></div>
        {pinyinStatus && <p className="service-status" role="status">{pinyinStatus}</p>}
        <div className="translation-fields">{orderedLanguages.map((option) => <label key={option.id}><span>{option.flag} {option.name}</span><input value={draft.translations[option.id]} onChange={(event) => setDraft({ ...draft, translations: { ...draft.translations, [option.id]: event.target.value }, translationSources: { ...draft.translationSources, [option.id]: 'manual' } })} placeholder={`${option.name} 翻译`} required disabled={translationLoading} /></label>)}</div>
        {translationStatus && <p className={`service-status ${translationStatus.includes('不可用') ? 'service-error' : ''}`} role="status">{translationStatus}</p>}
        <label className="image-url-field">图片 URL<input type="url" value={manualUrl} onChange={(event) => setManualUrl(event.target.value)} placeholder="可留空，保存后从词条搜索图片" /></label>
        {error && <p className="form-error" role="alert">{error}</p>}
        {notice && <p className="form-notice" role="status">{notice}</p>}
        <div className="editor-actions"><button type="submit" className="primary-action" disabled={translationLoading || pinyinLoading}><Check size={15} />{editingId ? '保存修改' : '添加词汇'}</button></div>
      </form>
    </section>

    <section className="bulk-panel"><div className="panel-title"><div><span className="panel-symbol panel-symbol-blue"><Upload size={16} /></span><div><h2>批量输入</h2><p>每行一条，顺序：中文 | 拼音 | English | Deutsch | Français | Español | Italiano</p></div></div></div><textarea value={bulkText} onChange={(event) => setBulkText(event.target.value)} placeholder={'早上好 | zǎoshang hǎo | Good morning | Guten Morgen | Bonjour | Buenos días | Buongiorno\n晚上好 | wǎnshang hǎo | Good evening | Guten Abend | Bonsoir | Buenas noches | Buonasera'} rows={3} /><div className="bulk-footer"><small>支持竖线分隔或从表格粘贴的制表符。批量导入不自动猜测翻译。</small><button className="secondary-action" onClick={importBulk} disabled={!bulkText.trim()}><Upload size={14} />导入词汇</button></div></section>

    <section className="bulk-panel auto-batch-panel"><div className="panel-title"><div><span className="panel-symbol"><Sparkles size={16} /></span><div><h2>批量生成词汇资料</h2><p>输入中文词语，逐条生成拼音与五语翻译，并搜索图片候选；图片须由老师选择。</p></div></div></div><textarea value={plainBulkText} onChange={(event) => setPlainBulkText(event.target.value)} placeholder={'你好\n谢谢\n老师\n学生\n苹果'} rows={4} disabled={batchRunning} /><div className="bulk-footer"><small>{batchProgress.total ? `进度 ${batchProgress.done} / ${batchProgress.total}${batchProgress.current ? ` · 正在处理：${batchProgress.current}` : ''}` : '支持每行一个词、逗号或顿号分隔。翻译/图片失败不会中断其他词。'}</small><button className="primary-action" onClick={generateBulk} disabled={batchRunning || !plainBulkText.trim()}>{batchRunning ? <LoaderCircle className="spin" size={15} /> : <Sparkles size={15} />}{batchRunning ? '正在生成…' : '批量生成'}</button></div>{batchProgress.total > 0 && <progress className="batch-progress" max={batchProgress.total} value={batchProgress.done} />}{Object.entries(batchStatuses).map(([chinese, status]) => <article className="batch-result" key={chinese}><div className="batch-result-heading"><strong>{chinese}</strong><span>{status.pinyin}</span><span>{status.translations}</span><span>{status.images}</span><div className="batch-retry-actions"><button className="text-button" onClick={() => void retryBatchService(chinese, 'pinyin')}>重试拼音</button><button className="text-button" onClick={() => void retryBatchService(chinese, 'translations')}>重试翻译</button><button className="text-button" onClick={() => void retryBatchService(chinese, 'images')}>重试图片</button></div></div>{status.candidates.length > 0 && <div className="batch-image-candidates">{status.candidates.map((candidate) => <button key={candidate.sourceUrl} className="batch-image-candidate" onClick={() => selectBatchImage(chinese, candidate)} title={`${candidate.title} · ${candidate.license}`}><img src={candidate.thumbnailUrl} alt={candidate.title} loading="lazy" /><span>选择此图片</span></button>)}</div>}</article>)}</section>

    <section className="vocabulary-list-section"><div className="list-heading"><div><h2>词汇库与练习选择</h2><p>已选择 {selectedIds.length} 个词；列表/网格共用同一选择结果。</p></div><div className="vocabulary-view-controls"><button className={`icon-action ${view === 'list' ? 'active' : ''}`} onClick={() => setViewMode('list')} aria-label="列表模式" title="列表"><List size={16} /></button><button className={`icon-action ${view === 'grid' ? 'active' : ''}`} onClick={() => setViewMode('grid')} aria-label="网格模式" title="网格"><Grid2X2 size={16} /></button></div></div>
      <div className="selection-toolbar"><div className="selection-actions"><button className="text-button" onClick={() => onSelectedIdsChange(words.slice(0, typeof selectionLimit === 'number' ? selectionLimit : words.length).map((word) => word.id))}>全选</button><button className="text-button" onClick={() => onSelectedIdsChange([])}>取消选择</button><button className="text-button" onClick={invertSelection}>反选</button><button className="text-button" disabled={!selectedIds.length} onClick={() => { if (window.confirm(`删除选中的 ${selectedIds.length} 个词汇？`)) onBulkDelete(selectedIds) }}>批量删除</button><button className="primary-action" disabled={!selectedIds.length} onClick={onCreatePractice}>批量加入练习</button></div><label className="limit-control">每次选择<select value={selectionLimit === 'all' ? 'all' : selectionLimit === 'custom' ? 'custom' : String(selectionLimit)} onChange={(event) => { const value = event.target.value; if (value === 'all' || value === 'custom') onSelectionLimitChange(value); else { const limit = Number(value); onSelectionLimitChange(limit); if (selectedIds.length > limit) onSelectedIdsChange(selectedIds.slice(0, limit)) } }}><option value="10">10</option><option value="20">20</option><option value="30">30</option><option value="50">50</option><option value="100">100</option><option value="all">不限</option><option value="custom">自定义</option></select></label>{selectionLimit === 'custom' && <input className="custom-limit-input" aria-label="自定义数量" type="number" min="1" max="1000" value={customLimit} onChange={(event) => { setCustomLimit(event.target.value); const value = Number(event.target.value); if (value > 0) { onSelectionLimitChange(value); if (selectedIds.length > value) onSelectedIdsChange(selectedIds.slice(0, value)) } }} />}</div>
      {selectedLimitMessage && <p className="form-error" role="status">{selectedLimitMessage}</p>}
      <div className={`vocabulary-list ${view === 'grid' ? 'vocabulary-grid' : 'vocabulary-table'}`}>{words.map((word) => <article className={`vocabulary-entry ${selectedIds.includes(word.id) ? 'entry-selected' : ''}`} key={word.id}>
        <label className="entry-checkbox" aria-label={`选择${word.chinese}`}><input type="checkbox" checked={selectedIds.includes(word.id)} onChange={() => toggleSelected(word.id)} /><span /></label>
        <WordImage image={word.image} alt={word.chinese} className="entry-image" />
        <div className="entry-main"><div className="entry-word"><strong>{word.chinese}</strong><SpeechButton value={word.chinese} language="zh" rate={rate} label={`播放${word.chinese}`} /><span className="entry-pinyin">{word.pinyin}</span><SpeechButton value={word.translations[language]} language={language} rate={rate} label={`播放${word.translations[language]}`} /></div><div className="entry-translations">{orderedLanguages.map((option) => <span key={option.id}><small>{option.id.toUpperCase()}</small>{word.translations[option.id]}</span>)}</div>{word.image && <div className="image-attribution"><span>{word.image.source} · {word.image.license}</span>{word.image.creator && <span> · {word.image.creator}</span>}{word.image.pageUrl && <a href={word.image.pageUrl} target="_blank" rel="noreferrer">来源</a>}</div>}</div>
        <div className="entry-actions"><button className="icon-action" onClick={() => setSearchWord(word)} title="搜索图片" aria-label={`为${word.chinese}搜索图片`}><Search size={16} /></button>{word.image && <button className="icon-action" onClick={() => clearImage(word)} title="清除图片" aria-label={`清除${word.chinese}图片`}><X size={16} /></button>}<button className="icon-action" onClick={() => editWord(word)} title="编辑词汇" aria-label={`编辑${word.chinese}`}><Pencil size={16} /></button><button className="icon-action danger-action" onClick={() => { if (window.confirm(`确定删除「${word.chinese}」？已保存练习也会移除此词。`)) onDeleteWord(word.id) }} title="删除词汇" aria-label={`删除${word.chinese}`}><Trash2 size={16} /></button></div>
      </article>)}</div>
      {words.length === 0 && <p className="empty-message">还没有词汇，请先添加或批量导入。</p>}
    </section>
    {searchWord && <WikimediaSearch word={searchWord} onChoose={selectImage} onClose={() => setSearchWord(null)} />}
  </main>
}