import { ArrowRight, Copy, Pencil, Trash2 } from 'lucide-react'
import { languageOptions } from '../data/translations'
import type { PracticeFolder, SavedPractice } from '../types'
import { useState } from 'react'

type SavedPracticesProps = {
  practices: SavedPractice[]
  onOpen: (practice: SavedPractice) => void
  onEdit: (practice: SavedPractice) => void
  onDuplicate: (practice: SavedPractice) => void
  onDelete: (practice: SavedPractice) => void
  onViewResults: (practice: SavedPractice) => void
  folders: PracticeFolder[]
  canPublish: boolean
  onPublish: (practice: SavedPractice) => void
  onShare: (practice: SavedPractice) => void
  onMove: (practice: SavedPractice, folderId: string) => void
}

export default function SavedPractices({ practices, onOpen, onEdit, onDuplicate, onDelete, onViewResults, folders, canPublish, onPublish, onShare, onMove }: SavedPracticesProps) {
  const [folderFilter, setFolderFilter] = useState('all')
  const visiblePractices = practices.filter((practice) => folderFilter === 'all' || (practice.folderId ?? 'hsk-1') === folderFilter)
  return <main className="management-page">
    <header className="management-heading"><div><span className="tool-kicker">教师工作台 · {practices.length} 个练习</span><h1>我的练习</h1><p>草稿保存在当前浏览器；已发布练习可通过分享码在其他设备访问。</p></div><label className="practice-folder-filter">文件夹<select value={folderFilter} onChange={(event) => setFolderFilter(event.target.value)}><option value="all">全部文件夹</option>{folders.map((folder) => <option key={folder.id} value={folder.id}>{folder.name}</option>)}</select></label></header>
    {visiblePractices.length ? <div className="saved-practice-list">{[...visiblePractices].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)).map((practice) => {
      const language = languageOptions.find((option) => option.id === practice.language)
      return <article key={practice.id} className="saved-practice-row"><div className="saved-practice-mark">练</div><div className="saved-practice-info"><h2>{practice.name}</h2><p><span>{language?.flag} {language?.name}</span><span>{practice.wordIds.length} 个词汇</span><span>{folders.find((folder) => folder.id === practice.folderId)?.name ?? '未分类'}</span><span>{practice.studentName ? `学生：${practice.studentName}` : '未指定学生'}</span><span className={`practice-status ${practice.status === 'published' ? 'published' : ''}`}>{practice.status === 'published' ? '已发布' : '草稿'}</span><span>更新于 {new Date(practice.updatedAt).toLocaleDateString()}</span></p></div><div className="saved-practice-actions"><select className="practice-folder-select" aria-label={`移动${practice.name}到文件夹`} value={practice.folderId ?? ''} onChange={(event) => onMove(practice, event.target.value)}>{folders.map((folder) => <option key={folder.id} value={folder.id}>{folder.name}</option>)}</select><button className="primary-action" onClick={() => onOpen(practice)}>预览 <ArrowRight size={15} /></button>{practice.status === 'published' && <><button className="secondary-action" onClick={() => onShare(practice)}>分享链接</button><button className="secondary-action" onClick={() => onViewResults(practice)}>查看成绩</button></>}{<button className="secondary-action" disabled={!canPublish} title={canPublish ? (practice.status === 'published' ? '发布新的练习快照，现有学生链接保持不变' : '发布练习') : '需要配置 Supabase 并登录教师账号'} onClick={() => onPublish(practice)}>{practice.status === 'published' ? '发布新版本' : '发布'}</button>}<button className="icon-action" onClick={() => onEdit(practice)} title="编辑" aria-label={`编辑${practice.name}`}><Pencil size={16} /></button><button className="icon-action" onClick={() => onDuplicate(practice)} title="复制" aria-label={`复制${practice.name}`}><Copy size={16} /></button><button className="icon-action danger-action" onClick={() => onDelete(practice)} title="删除" aria-label={`删除${practice.name}`}><Trash2 size={16} /></button></div></article>
    })}</div> : <section className="empty-state"><span className="empty-state-mark">练</span><h2>还没有保存的练习</h2><p>在“创建练习”中选词并生成，之后就可以在这里继续使用。</p></section>}
  </main>
}