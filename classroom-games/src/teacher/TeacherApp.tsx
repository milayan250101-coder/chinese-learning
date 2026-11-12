import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  BookOpen,
  ArrowRight,
  FileText,
  Upload,
  CalendarDays,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  GraduationCap,
  Gamepad2,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquareText,
  NotebookPen,
  Search,
  Settings,
  UserRound,
  Users,
  Bell,
  LockKeyhole,
  LoaderCircle,
  BookMarked,
  Clock3,
  Sparkles,
  Plus,
  X,
  KeyRound,
  Copy,
  RefreshCw,
  ArrowLeft,
} from 'lucide-react'

const API_BASE = '/api'

type Teacher = {
  id?: number | string
  username?: string
  email?: string
}

type Student = {
  id: number | string
  display_name?: string
  student_code?: string
  email?: string
  notes?: string
  is_active?: boolean
  created_at?: string
  updated_at?: string
}

type StudentAccount = {
  id?: number
  student_id: number
  login_username: string
  is_active: boolean
  must_change_password: boolean
  last_login_at?: string | null
  created_at?: string
  temporary_password?: string
}

type StudentNote = {
  id: number | string
  student_id: number | string
  student_name: string
  title?: string
  filename?: string
  file_type?: string
  analysis_status?: string
  original_analysis_status?: string | null
  created_at?: string
}

type CourseLevel = {
  id: number | string
  name?: string
  title?: string
  level?: string
}

type Vocabulary = {
  simplified?: string
  traditional?: string
  pinyin?: string
  english?: string
  level?: string | number
  part_of_speech?: string
}

type PageId =
  | 'home'
  | 'curriculum'
  | 'students'
  | 'whiteboard'
  | 'calendar'
  | 'hsk'
  | 'esl'
  | 'games'
  | 'profile'
  | 'settings'

const navigation = [
  { id: 'curriculum', label: '我的课程体系', en: 'Curriculum', icon: BookOpen },
  { id: 'students', label: '学生管理', en: 'Students', icon: Users },
  { id: 'whiteboard', label: '教学白板', en: 'Whiteboard', icon: NotebookPen },
  { id: 'calendar', label: '日历与课程安排', en: 'Calendar', icon: CalendarDays },
  { id: 'hsk', label: 'HSK 搜索', en: 'HSK Search', icon: Search },
  { id: 'esl', label: 'ESL 讨论题库', en: 'ESL Topics', icon: MessageSquareText },
  { id: 'games', label: '我的游戏', en: 'My Games', icon: Gamepad2 },
  { id: 'profile', label: '我的个人主页', en: 'My Profile', icon: UserRound },
  { id: 'settings', label: '系统设置', en: 'Settings', icon: Settings },
] as const

async function apiRequest<T>(
  path: string,
  token: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `请求失败：${response.status}`)
  }

  return response.json() as Promise<T>
}

function getItems<T>(data: unknown): T[] {
  if (Array.isArray(data)) return data as T[]
  if (data && typeof data === 'object') {
    const object = data as { items?: T[]; students?: T[] }
    if (Array.isArray(object.items)) return object.items
    if (Array.isArray(object.students)) return object.students
  }
  return []
}

function LoginPage({ onLogin }: { onLogin: (username: string, password: string) => Promise<void> }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      await onLogin(username, password)
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败，请检查账号和密码。')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-decoration">
        <div className="brand-mark"><GraduationCap size={27} /></div>
        <div className="login-brand">Chinese Learning Platform</div>
        <div className="login-decoration-copy">
          <span className="eyebrow">YOUR TEACHING SPACE</span>
          <h1>让每一堂课，<br />都有迹可循。</h1>
          <p>集中管理课程、学生与教学资料，让备课和教学更有条理。</p>
          <div className="login-decoration-orb orb-one" />
          <div className="login-decoration-orb orb-two" />
        </div>
        <span className="login-footer">A smarter space for language teaching.</span>
      </section>

      <section className="login-panel">
        <form className="login-form" onSubmit={submit}>
          <div className="login-form-icon"><LockKeyhole size={22} /></div>
          <span className="eyebrow">TEACHER PORTAL</span>
          <h2>欢迎回来</h2>
          <p className="muted">请使用教师账号登录你的工作台。</p>

          <label htmlFor="teacher-username">教师账号</label>
          <input
            id="teacher-username"
            value={username}
            onChange={event => setUsername(event.target.value)}
            placeholder="请输入教师用户名"
            autoComplete="username"
            required
          />

          <label htmlFor="teacher-password">密码</label>
          <input
            id="teacher-password"
            type="password"
            value={password}
            onChange={event => setPassword(event.target.value)}
            placeholder="请输入密码"
            autoComplete="current-password"
            required
          />

          {error && <div className="error-message">{error}</div>}

          <button className="primary-button login-submit" disabled={loading}>
            {loading ? <><LoaderCircle className="spin" size={17} /> 正在登录…</> : '登录教师工作台'}
          </button>
          <p className="login-security">账号验证由教学平台后台完成。</p>
        </form>
      </section>
    </main>
  )
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="empty-state">
      <div className="empty-icon"><BookMarked size={24} /></div>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  )
}

function PageHeading({ title, subtitle, action }: {
  title: string
  subtitle: string
  action?: React.ReactNode
}) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      {action}
    </div>
  )
}

function HomePage({
  teacher,
  students,
  levels,
  notes,
  loading,
  notesLoading,
  notesError,
  onNavigate,
}: {
  teacher: Teacher | null
  students: Student[]
  levels: CourseLevel[]
  notes: StudentNote[]
  loading: boolean
  notesLoading: boolean
  notesError: string
  onNavigate: (page: PageId) => void
}) {
  const today = new Date()
  const dateText = new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(today)

  const completedCount = notes.filter(note =>
    note.analysis_status === 'completed' ||
    (note.analysis_status === 'duplicate' &&
      note.original_analysis_status === 'completed')
  ).length

  const statusText: Record<string, string> = {
    completed: '分析完成',
    analyzed: '分析完成',
    processing: '分析中',
    running: '分析中',
    failed: '分析失败',
    not_started: '待分析',
    duplicate: '重复资料',
  }

  const statusClass: Record<string, string> = {
    completed: 'done',
    analyzed: 'done',
    processing: 'running',
    running: 'running',
    failed: 'failed',
    not_started: 'pending',
    duplicate: 'duplicate',
  }

  function formatDate(value?: string) {
    if (!value) return '时间未记录'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return '时间未记录'
    return new Intl.DateTimeFormat('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  }

  return (
    <>
      <section className="welcome-banner">
        <div>
          <span className="eyebrow">TEACHER DASHBOARD</span>
          <h1>早上好，{teacher?.username || '老师'} <span>☀️</span></h1>
          <p>今天也为学生创造一点新的进步吧。</p>
          <div className="welcome-date"><CalendarDays size={15} /> {dateText}</div>
        </div>
        <div className="welcome-art"><GraduationCap size={76} strokeWidth={1.15} /></div>
      </section>

      <div className="section-title-row">
        <div>
          <h2>教学概览</h2>
          <p>根据当前教师账号下的真实数据统计</p>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue"><Users size={20} /></div>
          <span>学生总数</span>
          <strong>{loading ? '—' : students.length}</strong>
          <small>当前账号名下的学生</small>
        </div>
        <div className="stat-card">
          <div className="stat-icon teal"><BookMarked size={20} /></div>
          <span>课堂资料</span>
          <strong>{loading || notesLoading ? '—' : notes.length}</strong>
          <small>已上传的课堂资料</small>
        </div>
        <div className="stat-card">
          <div className="stat-icon violet"><Sparkles size={20} /></div>
          <span>已完成分析</span>
          <strong>{loading || notesLoading ? '—' : completedCount}</strong>
          <small>包含已完成分析的重复资料</small>
        </div>
        <div className="stat-card">
          <div className="stat-icon amber"><BookOpen size={20} /></div>
          <span>课程级别</span>
          <strong>{loading ? '—' : levels.length}</strong>
          <small>已建立的课程级别</small>
        </div>
      </div>

      <section className="content-card dashboard-section">
        <div className="card-heading">
          <div><h2>学生学习进度</h2><p>按学生查看课堂资料与分析情况</p></div>
          <Users size={19} />
        </div>
        {loading || notesLoading ? (
          <div className="loading-state">正在读取学生学习资料…</div>
        ) : students.length === 0 ? (
          <EmptyState title="还没有学生资料" description="添加学生后，这里会显示每位学生的课堂资料和分析进度。" />
        ) : (
          <div className="student-progress-list">
            {students.map(student => {
              const studentNotes = notes.filter(note => String(note.student_id) === String(student.id))
              const completed = studentNotes.filter(note =>
                note.analysis_status === 'completed' ||
                note.analysis_status === 'analyzed'
              ).length

              const processing = studentNotes.filter(note =>
                note.analysis_status === 'processing' ||
                note.analysis_status === 'running'
              ).length

              const failed = studentNotes.filter(note =>
                note.analysis_status === 'failed'
              ).length

              const duplicateNotes = studentNotes.filter(note =>
                note.analysis_status === 'duplicate'
              )

              const duplicate = duplicateNotes.length

              const duplicateCompleted = duplicateNotes.filter(note =>
                note.original_analysis_status === 'completed' ||
                note.original_analysis_status === 'analyzed'
              ).length

              const pending = studentNotes.filter(note =>
                !note.analysis_status ||
                note.analysis_status === 'not_started'
              ).length

              // 保持首页原有统计口径：原始分析已完成的重复资料也计入有效完成数。
              const successful = completed + duplicateCompleted
              const percentage = studentNotes.length
                ? Math.round(successful / studentNotes.length * 100)
                : 0

              return (
                <div className="student-progress-row" key={student.id}>
                  <div className="student-progress-avatar">
                    {(student.display_name || '学').slice(0, 1)}
                  </div>
                  <div className="student-progress-main">
                    <strong>{student.display_name || '未填写姓名'}</strong>

                    <div className="progress-track">
                      <span style={{ width: `${percentage}%` }} />
                    </div>

                    <div className="student-progress-summary">
                      <span>{studentNotes.length} 份课堂资料</span>
                      <span>有效完成率 {percentage}%</span>
                    </div>

                    <div className="student-progress-breakdown">
                      <span className="progress-detail done">分析完成 {completed}</span>
                      <span className="progress-detail running">分析中 {processing}</span>
                      <span className="progress-detail pending">待分析 {pending}</span>
                      <span className="progress-detail failed">分析失败 {failed}</span>
                      <span className="progress-detail duplicate">重复资料 {duplicate}</span>
                    </div>
                  </div>

                  <span className="progress-count">
                    {studentNotes.length ? `${successful}/${studentNotes.length}` : '暂无资料'}
                  </span>
                </div>
              )
            })}
          </div>
        )}
        {notesError && <p className="dashboard-hint">{notesError}</p>}
        <button className="text-action" onClick={() => onNavigate('students')}>
          查看学生管理 <ArrowRight size={15} />
        </button>
      </section>

      <section className="content-card dashboard-section">
        <div className="card-heading">
          <div><h2>最近资料分析</h2><p>最近上传的课堂资料及其真实分析状态</p></div>
          <Clock3 size={19} />
        </div>
        {notesLoading ? (
          <div className="loading-state">正在读取课堂资料…</div>
        ) : notes.length === 0 ? (
          <EmptyState title="暂无课堂资料记录" description="学生上传课堂资料后，资料及分析状态会显示在这里。" />
        ) : (
          <div className="recent-note-list">
            {notes.slice(0, 6).map(note => {
              const status = note.analysis_status || 'not_started'
              return (
                <div className="recent-note-row" key={`${note.student_id}-${note.id}`}>
                  <div className="recent-note-icon"><FileText size={19} /></div>
                  <div className="recent-note-main">
                    <strong>{note.title || note.filename || '未命名资料'}</strong>
                    <small>{note.student_name} · {formatDate(note.created_at)}</small>
                  </div>
                  <span className={`analysis-status ${statusClass[status] || 'pending'}`}>
                    {statusText[status] || status}
                  </span>
                </div>
              )
            })}
          </div>
        )}
        {notesError && <p className="dashboard-hint">{notesError}</p>}
      </section>

      <section className="content-card dashboard-section">
        <div className="card-heading">
          <div><h2>快捷操作</h2><p>快速进入常用教学工作区</p></div>
          <ClipboardList size={19} />
        </div>
        <div className="quick-actions">
          <button onClick={() => onNavigate('students')}>
            <Users size={20} /><span><strong>学生管理</strong><small>查看学生资料</small></span><ArrowRight size={16} />
          </button>
          <button onClick={() => onNavigate('curriculum')}>
            <BookOpen size={20} /><span><strong>我的课程体系</strong><small>查看课程级别与内容</small></span><ArrowRight size={16} />
          </button>
          <button onClick={() => onNavigate('whiteboard')}>
            <NotebookPen size={20} /><span><strong>教学白板</strong><small>进入白板工作区（建设中）</small></span><ArrowRight size={16} />
          </button>
          <button disabled title="React 教师端上传入口尚未接入">
            <Upload size={20} /><span><strong>上传课堂资料</strong><small>上传入口接入中</small></span><LockKeyhole size={15} />
          </button>
        </div>
      </section>
    </>
  )
}

function StudentsPage({ token }: { token: string }) {
  const [students, setStudents] = useState<Student[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [account, setAccount] = useState<StudentAccount | null>(null)
  const [accountMissing, setAccountMissing] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [saving, setSaving] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [actionError, setActionError] = useState('')
  const [credentials, setCredentials] = useState<{ username: string; password: string } | null>(null)
  const [notice, setNotice] = useState('')

  const [name, setName] = useState('')
  const [studentCode, setStudentCode] = useState('')
  const [email, setEmail] = useState('')
  const [notes, setNotes] = useState('')

  async function refreshStudents() {
    setLoading(true)
    setError('')
    try {
      const data = await apiRequest<unknown>('/students/?skip=0&limit=100', token)
      setStudents(getItems<Student>(data))
    } catch (err) {
      setError(err instanceof Error ? err.message : '学生资料加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refreshStudents()
  }, [token])

  async function openStudent(student: Student) {
    setSelectedStudent(student)
    setDetailLoading(true)
    setDetailError('')
    setActionError('')
    setCredentials(null)
    setNotice('')
    setAccount(null)
    setAccountMissing(false)

    try {
      const detail = await apiRequest<Student>(`/students/${student.id}`, token)
      setSelectedStudent(detail)

      try {
        const accountData = await apiRequest<StudentAccount>(
          `/student-auth/students/${student.id}/account`,
          token,
        )
        setAccount(accountData)
      } catch (err) {
        const message = err instanceof Error ? err.message.toLowerCase() : ''
        if (message.includes('404') || message.includes('not found')) {
          setAccountMissing(true)
        } else {
          throw err
        }
      }
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : '学生详情加载失败')
    } finally {
      setDetailLoading(false)
    }
  }

  function resetForm() {
    setName('')
    setStudentCode('')
    setEmail('')
    setNotes('')
  }

  async function updateStudent(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedStudent || !name.trim()) return

    setSaving(true)
    setError('')

    try {
      const updated = await apiRequest<Student>(
        `/students/${selectedStudent.id}`,
        token,
        {
          method: 'PATCH',
          body: JSON.stringify({
            display_name: name.trim(),
            student_code: studentCode.trim() || null,
            email: email.trim() || null,
            notes: notes.trim() || null,
          }),
        },
      )

      setSelectedStudent(updated)
      setStudents(current =>
        current.map(student => student.id === updated.id ? updated : student),
      )
      setFormOpen(false)
      setEditMode(false)
      setNotice('学生资料已更新。')
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新学生资料失败')
    } finally {
      setSaving(false)
    }
  }

  async function createStudent(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!name.trim()) return

    setSaving(true)
    setError('')

    try {
      const created = await apiRequest<Student>('/students/', token, {
        method: 'POST',
        body: JSON.stringify({
          display_name: name.trim(),
          student_code: studentCode.trim() || null,
          email: email.trim() || null,
          notes: notes.trim() || null,
        }),
      })

      resetForm()
      setFormOpen(false)
      setNotice('学生资料已创建。')
      await refreshStudents()
      await openStudent(created)
    } catch (err) {
      setError(err instanceof Error ? err.message : '添加学生失败')
    } finally {
      setSaving(false)
    }
  }

  async function createAccount() {
    if (!selectedStudent) return

    setActionLoading(true)
    setActionError('')
    setCredentials(null)

    try {
      const result = await apiRequest<StudentAccount>(
        `/student-auth/students/${selectedStudent.id}/account`,
        token,
        { method: 'POST', body: JSON.stringify({}) },
      )

      setAccount(result)
      setAccountMissing(false)
      setCredentials({
        username: result.login_username,
        password: result.temporary_password || '',
      })
      setNotice('学生登录账号创建成功。请及时保存临时密码。')
    } catch (err) {
      setActionError(err instanceof Error ? err.message : '创建学生账号失败')
    } finally {
      setActionLoading(false)
    }
  }

  async function resetPassword() {
    if (!selectedStudent || !account) return

    setActionLoading(true)
    setActionError('')
    setCredentials(null)

    try {
      const result = await apiRequest<StudentAccount>(
        `/student-auth/students/${selectedStudent.id}/account/reset-password`,
        token,
        { method: 'POST' },
      )

      setAccount({
        ...account,
        must_change_password: true,
        is_active: selectedStudent.is_active !== false,
      })
      setCredentials({
        username: result.login_username,
        password: result.temporary_password || '',
      })
      setNotice('临时密码已重置。学生下次登录需要修改密码。')
    } catch (err) {
      setActionError(err instanceof Error ? err.message : '重置密码失败')
    } finally {
      setActionLoading(false)
    }
  }

  const headingAction = selectedStudent ? (
    <button
      type="button"
      className="students-secondary-button"
      onClick={() => {
        setSelectedStudent(null)
        setCredentials(null)
        setNotice('')
        setActionError('')
      }}
    >
      <ArrowLeft size={15} /> 返回学生列表
    </button>
  ) : (
    <button
      type="button"
      className="primary-button"
      onClick={() => {
        setError('')
        setFormOpen(true)
      }}
    >
      <Plus size={16} /> 添加学生
    </button>
  )

  return (
    <>
      <PageHeading
        title={selectedStudent ? '学生详情' : '学生管理'}
        subtitle={selectedStudent ? '查看学生资料与独立登录账号。' : '查看和管理属于你的学生资料。'}
        action={headingAction}
      />

      {!selectedStudent ? (
        <section className="content-card students-card">
          {error && <div className="error-message">{error}</div>}
          {notice && <div className="students-notice">{notice}</div>}

          {loading ? (
            <div className="loading-state">
              <LoaderCircle className="spin" /> 正在加载学生资料…
            </div>
          ) : students.length === 0 ? (
            <EmptyState
              title="还没有学生资料"
              description="点击右上角“添加学生”，创建你的第一位学生。"
            />
          ) : (
            <div className="data-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>学生姓名</th>
                    <th>学生编号</th>
                    <th>邮箱</th>
                    <th>状态</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map(student => (
                    <tr key={student.id}>
                      <td>
                        <button
                          type="button"
                          className="student-name-button"
                          onClick={() => void openStudent(student)}
                        >
                          {student.display_name || '未填写'}
                        </button>
                      </td>
                      <td>{student.student_code || '—'}</td>
                      <td>{student.email || '—'}</td>
                      <td>
                        <span className={`status-pill ${student.is_active === false ? 'inactive' : ''}`}>
                          {student.is_active === false ? '已停用' : '正常'}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="students-text-button"
                          onClick={() => void openStudent(student)}
                        >
                          查看详情 <ArrowRight size={13} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : (
        <section className="content-card students-detail-card">
          {detailLoading ? (
            <div className="loading-state">
              <LoaderCircle className="spin" /> 正在加载学生详情…
            </div>
          ) : detailError ? (
            <div className="error-message">{detailError}</div>
          ) : (
            <>
              <div className="students-detail-heading">
                <div className="students-avatar"><UserRound size={25} /></div>
                <div>
                  <h2>{selectedStudent.display_name || '未填写姓名'}</h2>
                  <p>学生编号：{selectedStudent.student_code || '未设置'}</p>
                </div>
                <span className={`status-pill ${selectedStudent.is_active === false ? 'inactive' : ''}`}>
                  {selectedStudent.is_active === false ? '已停用' : '正常'}
                </span>
              </div>

              <div className="students-detail-actions">
                <button
                  type="button"
                  className="students-secondary-button"
                  onClick={() => {
                    setName(selectedStudent.display_name || '')
                    setStudentCode(selectedStudent.student_code || '')
                    setEmail(selectedStudent.email || '')
                    setNotes(selectedStudent.notes || '')
                    setEditMode(true)
                    setError('')
                    setFormOpen(true)
                  }}
                >
                  编辑资料
                </button>
              </div>

              <div className="students-info-grid">
                <div><span>邮箱</span><strong>{selectedStudent.email || '未填写'}</strong></div>
                <div><span>创建时间</span><strong>{selectedStudent.created_at ? new Date(selectedStudent.created_at).toLocaleDateString() : '—'}</strong></div>
                <div className="students-info-notes"><span>备注</span><strong>{selectedStudent.notes || '暂无备注'}</strong></div>
              </div>

              <div className="students-account-section">
                <div className="students-section-heading">
                  <div>
                    <h3><KeyRound size={16} /> 学生登录账号</h3>
                    <p>每位学生使用自己的用户名和密码登录。</p>
                  </div>
                </div>

                {accountMissing ? (
                  <div className="students-account-empty">
                    <p>这位学生还没有登录账号。</p>
                    <button
                      type="button"
                      className="primary-button"
                      disabled={actionLoading || selectedStudent.is_active === false}
                      onClick={() => void createAccount()}
                    >
                      {actionLoading ? <LoaderCircle size={15} className="spin" /> : <Plus size={15} />}
                      创建学生登录账号
                    </button>
                    {selectedStudent.is_active === false && (
                      <p className="students-hint">学生资料已停用，不能创建登录账号。</p>
                    )}
                  </div>
                ) : account ? (
                  <div className="students-account-info">
                    <div><span>登录用户名</span><strong>{account.login_username}</strong></div>
                    <div>
                      <span>账号状态</span>
                      <strong>{account.is_active ? '正常' : '已停用'}</strong>
                    </div>
                    <div>
                      <span>首次登录修改密码</span>
                      <strong>{account.must_change_password ? '是' : '否'}</strong>
                    </div>
                    <div>
                      <span>最近登录</span>
                      <strong>{account.last_login_at ? new Date(account.last_login_at).toLocaleString() : '尚未登录'}</strong>
                    </div>
                    <button
                      type="button"
                      className="students-secondary-button"
                      disabled={actionLoading || selectedStudent.is_active === false}
                      onClick={() => void resetPassword()}
                    >
                      {actionLoading ? <LoaderCircle size={15} className="spin" /> : <RefreshCw size={15} />}
                      重置临时密码
                    </button>
                  </div>
                ) : null}

                {actionError && <div className="error-message">{actionError}</div>}
                {notice && <div className="students-notice">{notice}</div>}

                {credentials && (
                  <div className="students-credentials">
                    <h4>请立即保存学生登录信息</h4>
                    <p>临时密码只在本次创建或重置后显示，请复制并安全地交给学生。</p>
                    <div><span>用户名</span><code>{credentials.username}</code></div>
                    <div><span>临时密码</span><code>{credentials.password || '接口未返回密码'}</code></div>
                    <button
                      type="button"
                      className="students-secondary-button"
                      onClick={() => {
                        void navigator.clipboard?.writeText(
                          `用户名：${credentials.username}\n临时密码：${credentials.password}`,
                        )
                      }}
                    >
                      <Copy size={14} /> 复制登录信息
                    </button>
                    <p className="students-hint">学生首次登录后必须修改密码。请不要把临时密码公开展示。</p>
                  </div>
                )}
              </div>
            </>
          )}
        </section>
      )}

      {formOpen && (
        <div
          className="students-modal-backdrop"
          onMouseDown={event => {
            if (event.target === event.currentTarget && !saving) setFormOpen(false)
          }}
        >
          <section className="students-modal" role="dialog" aria-modal="true" aria-labelledby="student-form-title">
            <div className="students-modal-heading">
              <div>
                <h2 id="student-form-title">{editMode ? '编辑学生资料' : '添加学生'}</h2>
                <p>{editMode ? '修改这位学生的基本资料。' : '填写学生基本资料，之后可以单独创建登录账号。'}</p>
              </div>
              <button
                type="button"
                className="students-close-button"
                aria-label="关闭"
                disabled={saving}
                onClick={() => {
                  setFormOpen(false)
                  setEditMode(false)
                  setError('')
                }}
              >
                <X size={19} />
              </button>
            </div>

            <form className="students-form" onSubmit={editMode ? updateStudent : createStudent}>
              <label>
                学生姓名 <span>*</span>
                <input
                  value={name}
                  onChange={event => setName(event.target.value)}
                  placeholder="请输入学生姓名"
                  maxLength={150}
                  required
                />
              </label>
              <label>
                学生编号
                <input
                  value={studentCode}
                  onChange={event => setStudentCode(event.target.value)}
                  placeholder="选填，例如 STU001"
                  maxLength={100}
                />
              </label>
              <label>
                邮箱
                <input
                  type="email"
                  value={email}
                  onChange={event => setEmail(event.target.value)}
                  placeholder="选填"
                  maxLength={255}
                />
              </label>
              <label>
                备注
                <textarea
                  value={notes}
                  onChange={event => setNotes(event.target.value)}
                  placeholder="选填，例如学习目标、上课安排等"
                  rows={3}
                />
              </label>

              {error && <div className="error-message">{error}</div>}

              <div className="students-form-actions">
                <button
                  type="button"
                  className="students-secondary-button"
                  disabled={saving}
                  onClick={() => {
                    setFormOpen(false)
                    setEditMode(false)
                    setError('')
                  }}
                >
                  取消
                </button>
                <button type="submit" className="primary-button" disabled={saving || !name.trim()}>
                  {saving ? <LoaderCircle size={15} className="spin" /> : <Plus size={15} />}
                  {saving ? '正在保存…' : editMode ? '保存修改' : '保存学生资料'}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </>
  )
}

function CurriculumPage({ token }: { token: string }) {
  const [levels, setLevels] = useState<CourseLevel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    apiRequest<unknown>('/master/levels', token)
      .then(data => { if (active) setLevels(getItems<CourseLevel>(data)) })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : '课程级别加载失败') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token])

  return (
    <>
      <PageHeading title="我的课程体系" subtitle="整理你的教学级别、课程单元与主题内容。" />
      <section className="content-card">
        <div className="card-heading"><div><h2>课程级别</h2><p>当前教师账号下的课程结构</p></div><BookOpen size={19} /></div>
        {loading ? <div className="loading-state"><LoaderCircle className="spin" /> 正在加载课程…</div> :
          error ? <div className="error-message">{error}</div> :
          levels.length === 0 ? <EmptyState title="课程体系还是空的" description="目前还没有建立课程级别。后续将在这里逐步连接课程单元、主题、词汇和语法。" /> :
          <div className="level-grid">{levels.map((level, index) => (
            <div className="level-card" key={level.id}>
              <span className="level-number">LEVEL {index + 1}</span>
              <h3>{level.name || level.title || level.level || `课程级别 ${index + 1}`}</h3>
              <p>课程级别</p>
            </div>
          ))}</div>
        }
      </section>
    </>
  )
}

function HSKPage({ token }: { token: string }) {
  const [keyword, setKeyword] = useState('')
  const [results, setResults] = useState<Vocabulary[]>([])
  const [searched, setSearched] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function search(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!keyword.trim()) return
    setLoading(true)
    setError('')
    setSearched(true)
    try {
      const params = new URLSearchParams({ keyword: keyword.trim(), page: '1', page_size: '50' })
      const data = await apiRequest<unknown>(`/hsk/vocabulary/?${params}`, token)
      setResults(getItems<Vocabulary>(data))
    } catch (err) {
      setError(err instanceof Error ? err.message : '搜索失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <PageHeading title="HSK 搜索" subtitle="搜索 HSK 词汇，后续可扩展语法和等级筛选。" />
      <section className="content-card">
        <form className="search-form" onSubmit={search}>
          <Search size={19} />
          <input value={keyword} onChange={event => setKeyword(event.target.value)} placeholder="输入汉字、拼音或英文释义…" />
          <button className="primary-button" disabled={loading}>{loading ? '搜索中…' : '搜索'}</button>
        </form>
        {error && <div className="error-message">{error}</div>}
        {searched && !loading && !error && results.length === 0 && <EmptyState title="没有找到匹配词汇" description="请尝试其他汉字、拼音或英文关键词。" />}
        {results.length > 0 && (
          <div className="data-table-wrap">
            <table className="data-table">
              <thead><tr><th>汉字</th><th>拼音</th><th>英文</th><th>等级</th></tr></thead>
              <tbody>{results.map((word, index) => (
                <tr key={`${word.simplified}-${index}`}>
                  <td><strong>{word.simplified || '—'}</strong>{word.traditional && word.traditional !== word.simplified ? <small className="traditional">{word.traditional}</small> : null}</td>
                  <td>{word.pinyin || '—'}</td><td>{word.english || '—'}</td><td>{word.level || '—'}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>
    </>
  )
}

function FrameworkPage({ page }: { page: Exclude<PageId, 'home' | 'curriculum' | 'students' | 'hsk'> }) {
  const content = {
    whiteboard: {
      title: '教学白板',
      subtitle: '为课堂讲解、书写和互动准备的工作空间。',
      icon: NotebookPen,
      heading: '白板工作区',
      description: '后续将加入自由书写、文本输入、绘图工具、清屏和课堂内容保存。',
    },
    calendar: {
      title: '日历与课程安排',
      subtitle: '集中查看课程时间和教学日程。',
      icon: CalendarDays,
      heading: '课程日历',
      description: '后续将加入月视图、周视图、日视图、课程安排和提醒。',
    },
    esl: {
      title: 'ESL 讨论题库',
      subtitle: '整理英语课堂讨论主题与口语练习内容。',
      icon: MessageSquareText,
      heading: '主题题库',
      description: '后续将加入主题分类、难度筛选、搜索和讨论问题管理。',
    },
    games: {
      title: '我的游戏',
      subtitle: '集中管理和进入你为学生准备的互动游戏。',
      icon: Gamepad2,
      heading: '我的游戏',
      description: '这里将逐步接入你开发和使用的教学游戏。',
    },
    profile: {
      title: '我的个人主页',
      subtitle: '展示你的教师资料与教学特色。',
      icon: UserRound,
      heading: '教师个人资料',
      description: '后续将加入头像、个人介绍、教学经历、课程特色和主页展示设置。',
    },
    settings: {
      title: '系统设置',
      subtitle: '管理教师工作台的个人设置。',
      icon: Settings,
      heading: '设置中心',
      description: '后续将逐步加入账户、安全、界面语言和通知设置。',
    },
  }[page]

  const Icon = content.icon

  return (
    <>
      <PageHeading title={content.title} subtitle={content.subtitle} />
      <section className="content-card framework-card">
        <div className="framework-icon"><Icon size={28} /></div>
        <span className="eyebrow">WORKSPACE</span>
        {page === 'games' ? (
          <>
            <h2>我的游戏</h2>
            <p>这里集中预留你为学生准备的互动游戏入口，后续再接入游戏。</p>
            <div className="my-games-grid">
              <article className="my-game-card">
                <div className="my-game-card-icon"><Gamepad2 size={23} /></div>
                <div className="my-game-card-content">
                  <h3>汉字小岛</h3>
                  <p>预留游戏入口，后续接入。</p>
                </div>
                <span className="my-game-status">即将接入</span>
              </article>
              <article className="my-game-card">
                <div className="my-game-card-icon"><Gamepad2 size={23} /></div>
                <div className="my-game-card-content">
                  <h3>我的自研游戏</h3>
                  <p>预留个人开发游戏入口，后续接入。</p>
                </div>
                <span className="my-game-status">即将接入</span>
              </article>
            </div>
            <span className="development-label"><Sparkles size={14} /> 游戏入口已预留，尚未连接游戏</span>
          </>
        ) : (
          <>
            <h2>{content.heading}</h2>
            <p>{content.description}</p>
            <span className="development-label"><Sparkles size={14} /> 页面框架已建立，功能将逐步开发</span>
          </>
        )}
      </section>
    </>
  )
}

export default function TeacherApp() {
  const [token, setToken] = useState(() => localStorage.getItem('teacher_access_token') || '')
  const [teacher, setTeacher] = useState<Teacher | null>(null)
  const [page, setPage] = useState<PageId>('home')
  const [collapsed, setCollapsed] = useState(false)
  const [authLoading, setAuthLoading] = useState(Boolean(localStorage.getItem('teacher_access_token')))
  const [dashboardLoading, setDashboardLoading] = useState(false)
  const [students, setStudents] = useState<Student[]>([])
  const [levels, setLevels] = useState<CourseLevel[]>([])
  const [dashboardNotes, setDashboardNotes] = useState<StudentNote[]>([])
  const [notesLoading, setNotesLoading] = useState(false)
  const [notesError, setNotesError] = useState('')

  const currentNav = useMemo(
    () => navigation.find(item => item.id === page),
    [page],
  )

  const loadTeacher = useCallback(async (accessToken: string) => {
    const data = await apiRequest<Teacher>('/auth/me', accessToken)
    setTeacher(data)
  }, [])

  useEffect(() => {
    if (!token) {
      setAuthLoading(false)
      return
    }
    let active = true
    loadTeacher(token)
      .catch(() => {
        localStorage.removeItem('teacher_access_token')
        if (active) {
          setToken('')
          setTeacher(null)
        }
      })
      .finally(() => { if (active) setAuthLoading(false) })
    return () => { active = false }
  }, [token, loadTeacher])

  useEffect(() => {
    if (!token) return
    let active = true
    setDashboardLoading(true)
    Promise.all([
      apiRequest<unknown>('/students/?skip=0&limit=100', token),
      apiRequest<unknown>('/master/levels', token),
    ]).then(([studentData, levelData]) => {
      if (!active) return
      setStudents(getItems<Student>(studentData))
      setLevels(getItems<CourseLevel>(levelData))
    }).catch(() => {
      // Individual pages show their own API errors; keep dashboard usable.
    }).finally(() => { if (active) setDashboardLoading(false) })
    return () => { active = false }
  }, [token])

  useEffect(() => {
    if (!token || students.length === 0) {
      setDashboardNotes([])
      setNotesLoading(false)
      setNotesError('')
      return
    }

    let active = true
    setNotesLoading(true)
    setNotesError('')

    Promise.allSettled(students.map(async student => {
      const data = await apiRequest<unknown>(
        `/student-knowledge/students/${student.id}/notes`,
        token,
      )
      return getItems<Omit<StudentNote, 'student_id' | 'student_name'>>(data)
        .map(note => ({
          ...note,
          student_id: student.id,
          student_name: student.display_name || '未填写姓名',
        }))
    })).then(results => {
      if (!active) return
      const successful = results
        .filter((result): result is PromiseFulfilledResult<StudentNote[]> => result.status === 'fulfilled')
        .flatMap(result => result.value)
      const failedCount = results.filter(result => result.status === 'rejected').length
      successful.sort((a, b) => {
        const aTime = a.created_at ? new Date(a.created_at).getTime() : 0
        const bTime = b.created_at ? new Date(b.created_at).getTime() : 0
        return bTime - aTime
      })
      setDashboardNotes(successful)
      if (failedCount > 0) {
        setNotesError(`${failedCount} 位学生的课堂资料读取失败，当前只显示成功读取的记录。`)
      }
    }).finally(() => {
      if (active) setNotesLoading(false)
    })

    return () => { active = false }
  }, [token, students])

  async function login(username: string, password: string) {
    const body = new URLSearchParams({ username, password })
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    })
    if (!response.ok) throw new Error('账号或密码不正确，请重新检查。')
    const data = await response.json() as { access_token: string }
    if (!data.access_token) throw new Error('登录响应中没有访问令牌。')
    localStorage.setItem('teacher_access_token', data.access_token)
    setToken(data.access_token)
    await loadTeacher(data.access_token)
  }

  function logout() {
    localStorage.removeItem('teacher_access_token')
    setToken('')
    setTeacher(null)
    setPage('home')
  }

  if (authLoading) {
    return <div className="full-loading"><LoaderCircle className="spin" /> 正在验证教师身份…</div>
  }

  if (!token || !teacher) {
    return <LoginPage onLogin={login} />
  }

  return (
    <div className={`teacher-shell ${collapsed ? 'sidebar-collapsed' : ''}`}>
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark"><GraduationCap size={22} /></div>
          {!collapsed && <div className="brand-copy"><strong>教学中枢</strong><small>CHINESE LEARNING</small></div>}
        </div>

        <button className="collapse-button" onClick={() => setCollapsed(value => !value)} title={collapsed ? '展开导航' : '收起导航'}>
          {collapsed ? <Menu size={19} /> : <ChevronLeft size={19} />}
          {!collapsed && <span>收起导航</span>}
        </button>

        <div className="nav-caption">{!collapsed && '工作空间'}</div>
        <nav className="sidebar-nav">
          <button className={`nav-item ${page === 'home' ? 'active' : ''}`} onClick={() => setPage('home')} title="工作台首页">
            <LayoutDashboard size={19} /><span>工作台首页</span>
          </button>
          {navigation.map(item => {
            const Icon = item.icon
            return (
              <button key={item.id} className={`nav-item ${page === item.id ? 'active' : ''}`} onClick={() => setPage(item.id)} title={item.label}>
                <Icon size={19} /><span>{item.label}</span>
              </button>
            )
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-user">
            <div className="avatar">{(teacher.username || 'T').slice(0, 1)}</div>
            {!collapsed && <div className="sidebar-user-copy"><strong>{teacher.username || '教师'}</strong><small>教师账户</small></div>}
          </div>
          <button className="logout-button" onClick={logout} title="退出登录"><LogOut size={18} />{!collapsed && <span>退出登录</span>}</button>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="breadcrumb">
            <span>教学工作台</span><ChevronRight size={15} />
            <strong>{page === 'home' ? '首页' : currentNav?.label}</strong>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" title="通知功能尚未接入"><Bell size={19} /></button>
            <div className="topbar-user"><div className="avatar small">{(teacher.username || 'T').slice(0, 1)}</div><span>{teacher.username || '教师'}</span><ChevronDown size={15} /></div>
          </div>
        </header>

        <main className="page-content">
          {page !== 'home' && (
            <button
              type="button"
              className="subpage-home-back"
              onClick={() => setPage('home')}
            >
              ← 返回工作台首页
            </button>
          )}
          {page === 'home' && <HomePage teacher={teacher} students={students} levels={levels} notes={dashboardNotes} loading={dashboardLoading} notesLoading={notesLoading} notesError={notesError} onNavigate={setPage} />}
          {page === 'students' && <StudentsPage token={token} />}
          {page === 'curriculum' && <CurriculumPage token={token} />}
          {page === 'hsk' && <HSKPage token={token} />}
          {page !== 'home' && page !== 'students' && page !== 'curriculum' && page !== 'hsk' && (
            <FrameworkPage page={page} />
          )}
          <footer className="page-footer">Chinese Learning Platform <span>·</span> 教师专属工作空间</footer>
        </main>
      </div>
    </div>
  )
}
