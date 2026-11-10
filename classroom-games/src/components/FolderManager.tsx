import { FolderPlus, Pencil, Trash2 } from 'lucide-react'
import { useState } from 'react'
import type { PracticeFolder } from '../types'

type FolderManagerProps = {
  folders: PracticeFolder[]
  onCreate: (name: string) => void
  onRename: (folder: PracticeFolder, name: string) => void
  onDelete: (folder: PracticeFolder) => void
}

export default function FolderManager({ folders, onCreate, onRename, onDelete }: FolderManagerProps) {
  const [name, setName] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingName, setEditingName] = useState('')
  const ordered = [...folders].sort((left, right) => left.name.localeCompare(right.name, 'zh-CN', { numeric: true }))

  function createFolder(event: React.FormEvent) {
    event.preventDefault()
    if (!name.trim()) return
    onCreate(name.trim())
    setName('')
  }

  return <main className="management-page">
    <header className="management-heading"><div><span className="tool-kicker">课程组织 · {folders.length} 个文件夹</span><h1>练习文件夹</h1><p>HSK 1–6 已预设。新建目录用于按班级、学生或课程组织练习。</p></div></header>
    <form className="new-folder-form" onSubmit={createFolder}><label htmlFor="new-folder-name">新建文件夹</label><input id="new-folder-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="例如：Alice、暑期课程" maxLength={60} /><button className="primary-action" disabled={!name.trim()}><FolderPlus size={15} />创建文件夹</button></form>
    <div className="folder-list">{ordered.map((folder) => <article className="folder-row" key={folder.id}><span className="folder-icon">📁</span>{editingId === folder.id ? <form className="folder-rename-form" onSubmit={(event) => { event.preventDefault(); if (editingName.trim()) onRename(folder, editingName.trim()); setEditingId(null) }}><input autoFocus value={editingName} onChange={(event) => setEditingName(event.target.value)} maxLength={60} /><button className="primary-action">保存</button><button type="button" className="secondary-action" onClick={() => setEditingId(null)}>取消</button></form> : <><div className="folder-info"><strong>{folder.name}</strong><small>{folder.isBuiltIn ? '系统文件夹' : '自定义文件夹'}</small></div><div className="folder-actions"><button className="icon-action" title="重命名" aria-label={`重命名${folder.name}`} onClick={() => { setEditingId(folder.id); setEditingName(folder.name) }}><Pencil size={15} /></button><button className="icon-action danger-action" title="删除" aria-label={`删除${folder.name}`} disabled={folder.isBuiltIn} onClick={() => onDelete(folder)}><Trash2 size={15} /></button></div></>}</article>)}</div>
  </main>
}