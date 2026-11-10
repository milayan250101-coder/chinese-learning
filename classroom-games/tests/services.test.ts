import assert from 'node:assert/strict'
import { test } from 'node:test'
import { generatePinyin } from '../src/services/pinyinService.ts'
import { translateChineseWord } from '../src/services/translationService.ts'
import { StarRewardSession } from '../src/services/starRewards.ts'

test('generates tone-marked, context-aware vocabulary pinyin', async () => {
  const examples: Record<string, string> = {
    你好: 'nǐ hǎo',
    谢谢: 'xièxie',
    再见: 'zàijiàn',
    老师: 'lǎoshī',
    学生: 'xuéshēng',
    银行: 'yínháng',
    音乐: 'yīnyuè',
    长大: 'zhǎngdà',
    长短: 'chángduǎn',
    重庆: 'Chóngqìng',
    行走: 'xíngzǒu',
    行为: 'xíngwéi',
  }

  for (const [word, expected] of Object.entries(examples)) {
    assert.equal(await generatePinyin(word), expected, word)
  }
})

test('rewards correct answers once and applies streak/completion bonuses once', () => {
  const rewards = new StarRewardSession()
  assert.equal(rewards.awardCorrect('pinyin:hello').stars, 1)
  assert.equal(rewards.awardCorrect('pinyin:thanks').stars, 1)
  assert.equal(rewards.awardCorrect('pinyin:teacher').stars, 2)
  assert.deepEqual(rewards.awardCorrect('pinyin:teacher'), { stars: 0, streak: 3, duplicate: true })
  assert.equal(rewards.awardCorrect('pinyin:student').stars, 1)
  assert.equal(rewards.awardCorrect('pinyin:apple').stars, 3)
  assert.equal(rewards.awardCompletion('pinyin'), 3)
  assert.equal(rewards.awardCompletion('pinyin'), 0)
})

test('breaks streak after an incorrect answer', () => {
  const rewards = new StarRewardSession()
  rewards.awardCorrect('one')
  rewards.awardCorrect('two')
  rewards.breakStreak()
  assert.deepEqual(rewards.awardCorrect('three'), { stars: 1, streak: 1, duplicate: false })
})

test('falls back through English when the direct translation is empty', async () => {
  const originalFetch = globalThis.fetch
  const requests: string[] = []
  globalThis.fetch = async (input) => {
    const url = new URL(String(input))
    const pair = url.searchParams.get('langpair') ?? ''
    requests.push(pair)
    const translatedText = pair === 'zh-CN|it' ? '' : pair === 'zh-CN|en' ? 'Hello' : 'Ciao'
    return new Response(JSON.stringify({ responseStatus: 200, responseData: { translatedText } }), { status: 200, headers: { 'Content-Type': 'application/json' } })
  }

  try {
    assert.equal(await translateChineseWord('你好', 'it'), 'Ciao')
    assert.deepEqual(requests, ['zh-CN|it', 'zh-CN|en', 'en|it'])
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('reports translation failure instead of returning an empty success', async () => {
  const originalFetch = globalThis.fetch
  globalThis.fetch = async () => new Response(JSON.stringify({ responseStatus: 200, responseData: { translatedText: '' } }), { status: 200 })
  try {
    await assert.rejects(translateChineseWord('你好', 'it'), /没有返回有效结果/)
  } finally {
    globalThis.fetch = originalFetch
  }
})