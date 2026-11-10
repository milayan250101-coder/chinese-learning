import { supabase } from './supabaseClient'
import type { PracticeFolder, PracticeResult, PracticeSettings, SavedPractice, VocabularyWord } from '../types'

export type HostedPractice = {
  id: string
  shareCode: string
  name: string
  teacherName: string
  language: string
  settings: PracticeSettings
  items: { id: string; word: VocabularyWord }[]
}

export type HostedWorkspace = {
  words: VocabularyWord[]
  folders: import('../types').PracticeFolder[]
  practices: SavedPractice[]
}

function requireSupabase() {
  if (!supabase) throw new Error('跨设备发布需要在 .env.local 配置 Supabase URL 和 anon key。')
  return supabase
}

async function requireTeacherId() {
  const client = requireSupabase()
  const { data, error } = await client.auth.getUser()
  if (error || !data.user) throw new Error('请登录教师账号后同步云端数据。')
  const { error: profileError } = await client.from('teachers').upsert({ id: data.user.id, display_name: String(data.user.user_metadata?.full_name ?? data.user.email ?? 'Teacher') })
  if (profileError) throw profileError
  return { client, teacherId: data.user.id }
}

export async function signInTeacher(email: string) {
  const client = requireSupabase()
  return client.auth.signInWithOtp({ email, options: { emailRedirectTo: window.location.origin } })
}

export async function signOutTeacher() {
  const client = requireSupabase()
  return client.auth.signOut()
}

export async function loadHostedWorkspace(): Promise<HostedWorkspace> {
  const client = requireSupabase()
  const { data: authData, error: authError } = await client.auth.getUser()
  if (authError || !authData.user) throw new Error('请登录教师账号后读取云端工作区。')
  const teacherId = authData.user.id
  const [folderRows, vocabularyRows, practiceRows] = await Promise.all([
    client.from('folders').select('id, local_id, name, is_built_in, created_at').eq('teacher_id', teacherId),
    client.from('vocabularies').select('id, local_id, chinese, pinyin, translations, image, provenance, updated_at').eq('teacher_id', teacherId),
    client.from('practices').select('id, local_id, folder_id, student_name, name, language, settings, status, share_code, created_at, updated_at').eq('teacher_id', teacherId).order('updated_at', { ascending: false }),
  ])
  if (folderRows.error) throw folderRows.error
  if (vocabularyRows.error) throw vocabularyRows.error
  if (practiceRows.error) throw practiceRows.error

  const folderByRemoteId = new Map((folderRows.data ?? []).map((folder) => [folder.id, folder.local_id]))
  const seenLocalPracticeIds = new Set<string>()
  const remotePractices = (practiceRows.data ?? []).filter((practice) => {
    if (seenLocalPracticeIds.has(practice.local_id)) return false
    seenLocalPracticeIds.add(practice.local_id)
    return true
  })
  const remotePracticeIds = remotePractices.map((practice) => practice.id)
  const itemRows = remotePracticeIds.length
    ? await client.from('practice_items').select('practice_id, position, snapshot, correct_answer').in('practice_id', remotePracticeIds).order('position')
    : { data: [], error: null }
  if (itemRows.error) throw itemRows.error

  const snapshotsByPractice = new Map<string, SavedPractice['snapshot']>()
  for (const item of itemRows.data ?? []) {
    const snapshot = [...(snapshotsByPractice.get(item.practice_id) ?? []), { ...(item.snapshot as VocabularyWord), position: item.position, answer: item.correct_answer }]
    snapshotsByPractice.set(item.practice_id, snapshot)
  }

  return {
    folders: (folderRows.data ?? []).map((folder) => ({ id: folder.local_id, name: folder.name, isBuiltIn: folder.is_built_in, createdAt: folder.created_at })),
    words: (vocabularyRows.data ?? []).map((word) => {
      const provenance = (word.provenance ?? {}) as { pinyin?: 'automatic' | 'manual'; translations?: VocabularyWord['translationSources'] }
      return { id: word.local_id, chinese: word.chinese, pinyin: word.pinyin, translations: word.translations as VocabularyWord['translations'], translationSources: provenance.translations, pinyinSource: provenance.pinyin, category: 'custom', image: word.image as VocabularyWord['image'] }
    }),
    practices: remotePractices.map((practice) => ({
      id: practice.local_id,
      remoteId: practice.id,
      name: practice.name,
      language: practice.language as SavedPractice['language'],
      folderId: folderByRemoteId.get(practice.folder_id) ?? 'hsk-1',
      studentName: practice.student_name ?? '',
      wordIds: snapshotsByPractice.get(practice.id)?.map((word) => word.id) ?? [],
      snapshot: snapshotsByPractice.get(practice.id),
      settings: practice.settings as SavedPractice['settings'],
      status: practice.status as SavedPractice['status'],
      shareCode: practice.share_code ?? undefined,
      createdAt: practice.created_at,
      updatedAt: practice.updated_at,
    })),
  }
}

export async function syncTeacherVocabulary(words: VocabularyWord[]) {
  const { client, teacherId } = await requireTeacherId()
  const rows = words.map((word) => ({
    teacher_id: teacherId,
    local_id: word.id,
    chinese: word.chinese,
    pinyin: word.pinyin,
    translations: word.translations,
    image: word.image,
    provenance: { pinyin: word.pinyinSource ?? 'manual', translations: word.translationSources ?? {} },
    updated_at: new Date().toISOString(),
  }))
  if (!rows.length) return
  const { error } = await client.from('vocabularies').upsert(rows, { onConflict: 'teacher_id,local_id' })
  if (error) throw error
}

export async function deleteTeacherVocabulary(localIds: string[]) {
  if (!localIds.length) return
  const { client, teacherId } = await requireTeacherId()
  const { error } = await client.from('vocabularies').delete().eq('teacher_id', teacherId).in('local_id', localIds)
  if (error) throw error
}

export async function syncTeacherFolders(folders: PracticeFolder[]) {
  const { client, teacherId } = await requireTeacherId()
  const { data: existingFolders, error: listError } = await client.from('folders').select('id, local_id').eq('teacher_id', teacherId)
  if (listError) throw listError
  const rows = folders.map((folder) => ({ teacher_id: teacherId, local_id: folder.id, name: folder.name, is_built_in: folder.isBuiltIn }))
  if (rows.length) {
    const { error } = await client.from('folders').upsert(rows, { onConflict: 'teacher_id,local_id' })
    if (error) throw error
  }
  const retained = new Set(folders.map((folder) => folder.id))
  const removed = (existingFolders ?? []).filter((folder) => !retained.has(folder.local_id))
  for (const folder of removed) {
    const { error } = await client.from('folders').delete().eq('id', folder.id).eq('teacher_id', teacherId)
    if (error) throw error
  }
}

export async function moveHostedPractices(localPracticeId: string, folderLocalId: string) {
  const { client, teacherId } = await requireTeacherId()
  const { data: folder, error: folderError } = await client.from('folders').select('id').eq('teacher_id', teacherId).eq('local_id', folderLocalId).maybeSingle()
  if (folderError) throw folderError
  if (!folder) throw new Error('云端找不到目标文件夹，请重新同步后再试。')
  const { error } = await client.from('practices').update({ folder_id: folder.id, updated_at: new Date().toISOString() }).eq('teacher_id', teacherId).eq('local_id', localPracticeId)
  if (error) throw error
}

export async function publishPractice(practice: SavedPractice, words: VocabularyWord[], folderNameOverride?: string) {
  const client = requireSupabase()
  const { data: authData, error: authError } = await client.auth.getUser()
  if (authError || !authData.user) throw new Error('请先登录教师账号，再发布练习。')
  const teacherId = authData.user.id
  const teacherName = String(authData.user.user_metadata?.full_name ?? authData.user.email ?? 'Teacher')
  const { error: profileError } = await client.from('teachers').upsert({ id: teacherId, display_name: teacherName })
  if (profileError) throw profileError

  const folderName = folderNameOverride ?? (practice.folderId?.startsWith('hsk-')
    ? practice.folderId.toUpperCase().replace('-', ' ')
    : 'My folders')
  let { data: folder } = await client.from('folders').select('id').eq('teacher_id', teacherId).eq('local_id', practice.folderId ?? 'hsk-1').maybeSingle()
  if (!folder) {
    const { data, error } = await client.from('folders').insert({ teacher_id: teacherId, local_id: practice.folderId ?? 'hsk-1', name: folderName }).select('id').single()
    if (error) throw error
    folder = data
  }

  const student = practice.studentName?.trim()
    ? await client.from('students').upsert({ teacher_id: teacherId, display_name: practice.studentName.trim() }, { onConflict: 'teacher_id,display_name' }).select('id').single()
    : { data: null, error: null }
  if (student.error) throw student.error

  const shareCode = crypto.randomUUID().replace(/-/g, '').slice(0, 12)
  const vocabularyRows = words.map((word) => ({
    teacher_id: teacherId,
    local_id: word.id,
    chinese: word.chinese,
    pinyin: word.pinyin,
    translations: word.translations,
    image: word.image,
    provenance: { pinyin: word.pinyinSource ?? 'manual', translations: word.translationSources ?? {} },
    updated_at: new Date().toISOString(),
  }))
  const { data: vocabularyRowsSaved, error: vocabularyError } = await client.from('vocabularies')
    .upsert(vocabularyRows, { onConflict: 'teacher_id,local_id' })
    .select('id, local_id')
  if (vocabularyError) throw vocabularyError
  const vocabularyIds = new Map((vocabularyRowsSaved ?? []).map((row) => [row.local_id, row.id]))
  const { data: created, error: practiceError } = await client.from('practices').insert({
    teacher_id: teacherId,
    local_id: practice.id,
    folder_id: folder.id,
    student_id: student.data?.id ?? null,
    name: practice.name,
    student_name: practice.studentName ?? null,
    language: practice.language,
    settings: practice.settings ?? {},
    status: 'draft',
    share_code: shareCode,
  }).select('id').single()
  if (practiceError) throw practiceError

  const items = words.map((word, position) => ({
    practice_id: created.id,
    vocabulary_id: vocabularyIds.get(word.id) ?? null,
    position,
    snapshot: word,
    correct_answer: word.chinese,
  }))
  const { error: itemsError } = await client.from('practice_items').insert(items)
  if (itemsError) {
    await client.from('practices').delete().eq('id', created.id)
    throw itemsError
  }
  const { error: publishError } = await client.from('practices').update({ status: 'published', published_at: new Date().toISOString() }).eq('id', created.id)
  if (publishError) {
    await client.from('practices').delete().eq('id', created.id)
    throw publishError
  }
  return { id: created.id, shareCode }
}

export async function loadPublishedPractice(shareCode: string) {
  const client = requireSupabase()
  const { data, error } = await client.rpc('get_published_practice', { input_share_code: shareCode })
  if (error) throw error
  if (!data) throw new Error('找不到此练习，或练习尚未发布。')
  return data as HostedPractice
}

export async function startStudentAttempt(shareCode: string, studentName: string) {
  const client = requireSupabase()
  const { data, error } = await client.rpc('start_practice_attempt', { input_share_code: shareCode, input_student_name: studentName.trim() })
  if (error) throw error
  return String(data)
}

export async function submitStudentAttempt(attemptId: string, answers: { itemId: string; answer: string; displayAnswer?: string }[]) {
  const client = requireSupabase()
  const { data, error } = await client.rpc('submit_practice_attempt', { input_attempt_id: attemptId, input_answers: answers })
  if (error) throw error
  return data as { score: number; maxScore: number; accuracy: number; stars: number; incorrect: { chinese: string; pinyin: string; translation: Record<string, string>; selected: string }[] }
}

export async function listPracticeResults(practiceId: string): Promise<PracticeResult[]> {
  const client = requireSupabase()
  const { data: resultRows, error } = await client.from('practice_results')
    .select('id, practice_id, student_name, started_at, completed_at, score, max_score, accuracy, stars, session_id')
    .eq('practice_id', practiceId)
    .order('completed_at', { ascending: false })
  if (error) throw error
  const results = await Promise.all((resultRows ?? []).map(async (row) => {
    const { data: answerRows, error: answerError } = await client.from('answers')
      .select('practice_item_id, selected_answer, display_answer, is_correct, practice_items(snapshot, correct_answer)')
      .eq('session_id', row.session_id)
      .order('answered_at', { ascending: true })
    if (answerError) throw answerError
    const answers = (answerRows ?? []).map((answer) => {
      const item = Array.isArray(answer.practice_items) ? answer.practice_items[0] : answer.practice_items
      const snapshot = item?.snapshot as VocabularyWord | undefined
      return {
        itemId: answer.practice_item_id,
        selectedAnswer: answer.display_answer ?? answer.selected_answer,
        correct: answer.is_correct,
        chinese: snapshot?.chinese ?? '',
        pinyin: snapshot?.pinyin ?? '',
        correctAnswer: item?.correct_answer ?? '',
      }
    })
    return {
      id: row.id,
      practiceId: row.practice_id,
      studentName: row.student_name,
      startTime: row.started_at,
      endTime: row.completed_at,
      score: row.score,
      maxScore: row.max_score,
      accuracy: Number(row.accuracy),
      stars: row.stars,
      answers,
      incorrect: answers.filter((answer) => !answer.correct).map((answer) => ({ chinese: answer.chinese, pinyin: answer.pinyin, selected: answer.selectedAnswer, correct: answer.correctAnswer })),
    } satisfies PracticeResult
  }))
  return results
}