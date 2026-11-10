import { ExternalLink, LoaderCircle, Search, X } from 'lucide-react'
import { useState } from 'react'
import type { VocabularyImage, VocabularyWord } from '../types'
import { searchWikimediaImages, type CommonsImageResult } from '../services/commonsSearch'
import WordImage from './WordImage'

type WikimediaSearchProps = {
  word: VocabularyWord
  onChoose: (image: VocabularyImage) => void
  onClose: () => void
}

export default function WikimediaSearch({ word, onChoose, onClose }: WikimediaSearchProps) {
  const [query, setQuery] = useState(`${word.chinese} ${word.translations.en}`)
  const [results, setResults] = useState<CommonsImageResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searched, setSearched] = useState(false)
  const [searchNote, setSearchNote] = useState('')

  async function search(event?: React.FormEvent) {
    event?.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError('')
    setSearchNote('')
    setSearched(true)
    try {
      const result = await searchWikimediaImages(word.chinese, word.translations.en, query.trim())
      setResults(result.results)
      if (result.usedQuery && result.usedQuery !== query.trim()) setSearchNote(`已使用备用关键词“${result.usedQuery}”找到结果。`)
      if (result.results.length === 0) setError('没有找到合适图片，请修改搜索关键词。')
    } catch {
      setError('图片搜索暂时不可用，请检查网络后重试；也可以直接输入图片 URL。')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  function choose(result: CommonsImageResult) {
    onChoose({ url: result.url, thumbnailUrl: result.thumbnailUrl, sourceUrl: result.sourceUrl, sourceName: result.sourceName, source: result.sourceName, license: result.license, creator: result.creator, pageUrl: result.sourceUrl })
  }

  return <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
    <section className="image-search-dialog" role="dialog" aria-modal="true" aria-labelledby="image-search-title">
      <header className="dialog-heading"><div><span className="tool-kicker">WIKIMEDIA COMMONS</span><h2 id="image-search-title">为「{word.chinese}」选择图片</h2></div><button className="icon-button" onClick={onClose} aria-label="关闭"><X size={18} /></button></header>
      <form className="image-search-form" onSubmit={search}><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} aria-label="搜索关键词" placeholder="中文词语或英文释义" /><button className="primary-action" type="submit" disabled={loading}>{loading ? <LoaderCircle className="spin" size={15} /> : <Search size={15} />}搜索</button></form>
      <p className="image-search-note">结果来自 Wikimedia Commons。选择前请核对图片内容、来源和许可条件。</p>
      {error && <p className="inline-notice" role="status">{error}</p>}
      {searchNote && <p className="form-notice" role="status">{searchNote}</p>}
      {loading && <div className="search-loading"><LoaderCircle className="spin" size={21} />正在搜索公开图片资料…</div>}
      {!loading && results.length > 0 && <div className="image-results">{results.map((result) => <article className="image-result" key={result.sourceUrl}>
        <WordImage image={{ url: result.url, thumbnailUrl: result.thumbnailUrl, sourceUrl: result.sourceUrl, sourceName: result.sourceName, source: result.sourceName, license: result.license, pageUrl: result.sourceUrl }} alt={result.title} className="result-thumbnail" />
        <div className="result-meta"><strong title={result.title}>{result.title}</strong><small>来源：{result.sourceName}</small><small>作者：{result.creator}</small><small>许可：{result.license}</small><a href={result.sourceUrl} target="_blank" rel="noreferrer">查看原始来源 <ExternalLink size={12} /></a></div>
        <button className="secondary-action" onClick={() => choose(result)}>选择图片</button>
      </article>)}</div>}
      {!loading && searched && results.length === 0 && !error && <p className="empty-message">没有找到结果。</p>}
      <footer className="dialog-footer">图片版权与署名要求以来源页面和对应许可为准。</footer>
    </section>
  </div>
}