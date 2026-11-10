const displayOverrides: Record<string, string> = {
  你好: 'nǐ hǎo',
  谢谢: 'xièxie',
  再见: 'zàijiàn',
}

const properNounCapitalization: Record<string, string> = {
  重庆: 'Chóngqìng',
}

export async function generatePinyin(chinese: string) {
  const text = chinese.trim()
  if (!text) throw new Error('请输入中文后再生成拼音。')
  if (properNounCapitalization[text]) return properNounCapitalization[text]
  if (displayOverrides[text]) return displayOverrides[text]

  const { pinyin } = await import('pinyin-pro')
  return pinyin(text).replace(/\s+/g, '')
}