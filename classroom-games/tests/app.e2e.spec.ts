import { expect, test } from '@playwright/test'
import type { Language, VocabularyWord } from '../src/types'

const words: VocabularyWord[] = [
  { id: 'hello', chinese: '你好', pinyin: 'nǐ hǎo', translations: { en: 'Hello', de: 'Hallo', fr: 'Bonjour', es: 'Hola', it: 'Ciao' }, category: 'greetings', image: null },
  { id: 'apple', chinese: '苹果', pinyin: 'píngguǒ', translations: { en: 'Apple', de: 'Apfel', fr: 'Pomme', es: 'Manzana', it: 'Mela' }, category: 'food', image: null },
  { id: 'teacher', chinese: '老师', pinyin: 'lǎoshī', translations: { en: 'Teacher', de: 'Lehrer', fr: 'Enseignant', es: 'Profesor', it: 'Insegnante' }, category: 'people', image: null },
  { id: 'student', chinese: '学生', pinyin: 'xuéshēng', translations: { en: 'Student', de: 'Schüler', fr: 'Étudiant', es: 'Estudiante', it: 'Studente' }, category: 'people', image: null },
  { id: 'banana', chinese: '香蕉', pinyin: 'xiāngjiāo', translations: { en: 'Banana', de: 'Banane', fr: 'Banane', es: 'Plátano', it: 'Banana' }, category: 'food', image: null },
]

test.beforeEach(async ({ page }) => {
  await page.addInitScript((fixtureWords) => {
    localStorage.setItem('hanzi-island-language', 'en')
    localStorage.setItem('hanzi-island-vocabulary', JSON.stringify(fixtureWords))
    localStorage.setItem('hanzi-island-selected', JSON.stringify(fixtureWords.map((word) => word.id)))
    localStorage.setItem('hanzi-island-practices', '[]')
    localStorage.setItem('chineseVocabularyStars', '0')
  }, words)
  await page.goto('/')
})

test('automatic pinyin and five-language translation preserve manual edits', async ({ page }) => {
  await page.getByRole('button', { name: '词汇管理' }).click()
  await page.getByLabel('中文汉字').fill('长大')
  await page.getByRole('button', { name: '自动生成拼音' }).click()
  await expect(page.getByLabel('汉语拼音')).toHaveValue('zhǎngdà')
  await page.getByLabel('汉语拼音').fill('zhǎng dà (人工核对)')
  await page.getByRole('button', { name: '自动生成拼音' }).click()
  await expect(page.getByLabel('汉语拼音')).toHaveValue('zhǎng dà (人工核对)')
  await expect(page.getByRole('status').filter({ hasText: '手动修改，未覆盖' })).toBeVisible()

  await page.route('https://api.mymemory.translated.net/get**', async (route) => {
    const params = new URL(route.request().url()).searchParams
    const pair = params.get('langpair') ?? ''
    const values: Record<string, string> = {
      'zh-CN|en': 'Grow up', 'zh-CN|de': 'Erwachsen werden', 'zh-CN|fr': 'Grandir',
      'zh-CN|es': 'Crecer', 'zh-CN|it': '', 'en|it': 'Crescere',
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ responseStatus: 200, responseData: { translatedText: values[pair] ?? 'Crescere' } }) })
  })

  const fields = page.locator('.translation-fields input')
  await fields.nth(1).fill('Lehrerin / Lehrer')
  await page.getByRole('button', { name: '自动翻译' }).click()
  await expect(fields.nth(0)).toHaveValue('Grow up')
  await expect(fields.nth(1)).toHaveValue('Lehrerin / Lehrer')
  await expect(fields.nth(2)).toHaveValue('Grandir')
  await expect(fields.nth(3)).toHaveValue('Crecer')
  await expect(fields.nth(4)).toHaveValue('Crescere')

  await fields.nth(3).fill('crecer (revisado)')
  await page.getByRole('button', { name: '自动翻译' }).click()
  await expect(fields.nth(3)).toHaveValue('crecer (revisado)')
})

test('Commons image is selectable and remains attached after refresh', async ({ page }) => {
  await page.getByRole('button', { name: '词汇管理' }).click()
  await page.getByRole('button', { name: '为苹果搜索图片' }).click()
  const results = page.locator('.image-result')
  await expect(results.first()).toBeVisible({ timeout: 45_000 })
  await expect(results.first().getByText('来源：Wikimedia Commons')).toBeVisible()
  await expect(results.first().getByText(/许可：/)).toBeVisible()
  await expect(results.first().getByRole('link', { name: /查看原始来源/ })).toHaveAttribute('href', /wikimedia\.org/)
  await expect.poll(() => results.first().locator('img').evaluate((image: HTMLImageElement) => image.naturalWidth), { timeout: 30_000 }).toBeGreaterThan(0)
  await results.first().getByRole('button', { name: '选择图片' }).click()
  await expect(page.locator('.vocabulary-entry').filter({ hasText: '苹果' }).locator('img.entry-image')).toBeVisible()
  const savedImage = await page.evaluate(() => JSON.parse(localStorage.getItem('hanzi-island-vocabulary') ?? '[]').find((word: VocabularyWord) => word.chinese === '苹果')?.image)
  expect(savedImage).toMatchObject({ sourceName: 'Wikimedia Commons', license: expect.any(String) })
  expect(savedImage.thumbnailUrl).toContain('upload.wikimedia.org')

  await page.reload()
  await page.getByRole('button', { name: '词汇管理' }).click()
  await expect(page.locator('.vocabulary-entry').filter({ hasText: '苹果' }).locator('img.entry-image')).toBeVisible()
})

test('correct pinyin answers earn streak and completion stars once and export results', async ({ page }) => {
  await page.getByRole('button', { name: /Choose the pinyin/ }).click()
  for (let index = 0; index < words.length; index += 1) {
    const chinese = await page.locator('.prompt-word strong').innerText()
    const answer = words.find((word) => word.chinese === chinese)
    expect(answer).toBeTruthy()
    await page.locator('.choice-row').filter({ hasText: answer!.pinyin }).click()
    await expect(page.locator('.answer-feedback.is-correct')).toBeVisible()
    await page.getByRole('button', { name: index === words.length - 1 ? /Round complete/ : /Next question/ }).click()
  }

  await expect(page.locator('.completion-panel')).toContainText('50 / 50')
  await expect(page.locator('.completion-panel')).toContainText('11')
  await expect(page.locator('.star-total strong')).toHaveText('11')
  expect(await page.evaluate(() => localStorage.getItem('chineseVocabularyStars'))).toBe('11')

  await page.getByRole('button', { name: '导出结果 PDF' }).click()
  await page.getByRole('button', { name: '预览并打印' }).click()
  await expect(page.locator('.print-results-summary')).toContainText('50 / 50')
  await expect(page.locator('.print-results-summary')).toContainText('100%')
  await expect(page.locator('.print-results-summary')).toContainText('11 星')
  await page.getByRole('button', { name: '关闭' }).click()

  await page.reload()
  await expect(page.locator('.star-total strong')).toHaveText('11')
})

test('matching and flash cards award once, while needs-practice awards no star on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.locator('body')).toHaveJSProperty('scrollWidth', 390)
  await page.getByRole('button', { name: /Choose the pinyin/ }).click()
  await page.getByRole('button', { name: 'Pinyin matching' }).click()

  const firstPinyin = (await page.locator('.match-columns > div').first().locator('.match-choice').first().innerText()).trim()
  const matchingWord = words.find((word) => word.pinyin === firstPinyin)!
  const wrongWord = words.find((word) => word.id !== matchingWord.id)!
  await page.locator('.match-columns > div').first().locator('.match-choice').first().click()
  await page.locator('.match-chinese').filter({ hasText: wrongWord.chinese }).click()
  await expect(page.locator('.match-feedback.is-wrong')).toBeVisible()
  await expect(page.locator('.star-total strong')).toHaveText('0')

  await page.locator('.match-columns > div').first().locator('.match-choice').filter({ hasText: firstPinyin }).click()
  await page.locator('.match-chinese').filter({ hasText: matchingWord.chinese }).click()
  await expect(page.locator('.star-total strong')).toHaveText('1')

  await page.getByRole('button', { name: 'Flip cards' }).click()
  await page.locator('.flip-front').click()
  await page.getByRole('button', { name: 'Needs more practice' }).click()
  await expect(page.locator('.star-total strong')).toHaveText('1')
  await page.getByRole('button', { name: /Next question/ }).click()
  await page.locator('.flip-front').click()
  await page.getByRole('button', { name: /I know this/ }).click()
  await expect(page.locator('.star-total strong')).toHaveText('2')
})