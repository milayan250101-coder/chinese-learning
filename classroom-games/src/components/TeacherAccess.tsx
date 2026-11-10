import { KeyRound, LogOut } from 'lucide-react'
import { useState } from 'react'

type TeacherAccessProps = {
  configured: boolean
  email: string
  onEmailChange: (email: string) => void
  signedInEmail: string | null
  initialError?: string
  onSendLink: () => Promise<void>
  onSignOut: () => Promise<void>
}

export default function TeacherAccess({ configured, email, onEmailChange, signedInEmail, initialError = '', onSendLink, onSignOut }: TeacherAccessProps) {
  const [loading, setLoading] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState(initialError)

  async function sendLink(event: React.FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setNotice('')
    try {
      await onSendLink()
      setNotice('登录链接已发送，请检查邮箱。')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '暂时无法发送登录链接。')
    } finally {
      setLoading(false)
    }
  }

  async function signOut() {
    setLoading(true)
    try {
      await onSignOut()
      setNotice('已退出教师账号。')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '退出失败。')
    } finally {
      setLoading(false)
    }
  }

  return <main className="management-page"><header className="management-heading"><div><span className="tool-kicker">账号与云端</span><h1>教师登录</h1><p>登录后可发布练习、生成跨设备链接并查看学生成绩。</p></div><KeyRound size={26} className="heading-icon" /></header>
    {!configured ? <section className="backend-notice"><h2>尚未连接 Supabase</h2><p>当前词库和练习继续保存在此浏览器。跨设备发布、学生提交及成绩同步需要 Supabase 项目。</p><ol><li>复制 `.env.example` 为 `.env.local`。</li><li>填写 `VITE_SUPABASE_URL` 和 `VITE_SUPABASE_ANON_KEY`。</li><li>在 Supabase SQL Editor 执行 `supabase/migrations/20261008000000_teacher_practice_platform.sql`。</li></ol><p>只填写公开 anon/publishable key；绝不要将 service role key 放入前端。</p></section> : signedInEmail ? <section className="teacher-session"><span className="session-check">✓</span><div><strong>已登录</strong><span>{signedInEmail}</span></div><button className="secondary-action" onClick={signOut} disabled={loading}><LogOut size={15} />退出登录</button></section> : <form className="teacher-login-form" onSubmit={sendLink}><label>教师邮箱<input type="email" value={email} onChange={(event) => onEmailChange(event.target.value)} required placeholder="teacher@example.com" /></label><p>我们会发送一次性登录链接，不会在前端保存密码。</p><button className="primary-action" disabled={loading || !email.trim()}><KeyRound size={15} />{loading ? '正在发送…' : '发送登录链接'}</button></form>}
    {notice && <p className="form-notice" role="status">{notice}</p>}{error && <p className="form-error" role="alert">{error}</p>}
  </main>
}