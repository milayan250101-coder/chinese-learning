export type CommonsImageResult = {
  title: string
  thumbnailUrl: string
  url: string
  sourceUrl: string
  sourceName: 'Wikimedia Commons'
  license: string
  creator: string
}

type CommonsPage = {
  title: string
  imageinfo?: {
    thumburl?: string
    url?: string
    descriptionurl?: string
    extmetadata?: Record<string, { value?: string }>
  }[]
}

type CommonsResponse = { query?: { pages?: Record<string, CommonsPage> }; error?: { info?: string } }

const semanticQueries: Record<string, string[]> = {
  苹果: ['apple fruit'], 香蕉: ['banana fruit'], 老师: ['teacher classroom'], 学生: ['student classroom'],
  医院: ['hospital'], 银行: ['bank building'], 猫: ['cat animal'], 狗: ['dog animal'], 飞机: ['airplane aircraft'], 学校: ['school classroom'],
}

function plainText(value?: string) {
  if (!value) return ''
  const element = document.createElement('div')
  element.innerHTML = value
  return (element.textContent ?? '').replace(/\s+/g, ' ').trim()
}

async function queryCommons(query: string, signal?: AbortSignal): Promise<CommonsImageResult[]> {
  const params = new URLSearchParams({
    action: 'query', generator: 'search', gsrsearch: `filetype:bitmap ${query}`,
    gsrnamespace: '6', gsrlimit: '16', prop: 'imageinfo', iiprop: 'url|extmetadata',
    iiurlwidth: '480', format: 'json', origin: '*',
  })
  const response = await fetch(`https://commons.wikimedia.org/w/api.php?${params}`, { signal })
  if (!response.ok) throw new Error(`Wikimedia Commons 返回 HTTP ${response.status}。`)
  const data = await response.json() as CommonsResponse
  if (data.error) throw new Error(data.error.info || 'Wikimedia Commons 查询失败。')
  return Object.values(data.query?.pages ?? {}).flatMap((page) => {
    const info = page.imageinfo?.[0]
    if (!info?.url || !info.thumburl || !info.descriptionurl) return []
    return [{
      title: page.title.replace(/^File:/, ''),
      thumbnailUrl: info.thumburl,
      url: info.url,
      sourceUrl: info.descriptionurl,
      sourceName: 'Wikimedia Commons' as const,
      license: plainText(info.extmetadata?.LicenseShortName?.value) || '许可信息未提供，请打开来源页核实',
      creator: plainText(info.extmetadata?.Artist?.value) || plainText(info.extmetadata?.Credit?.value) || '作者信息未提供',
    }]
  })
}

export async function searchWikimediaImages(chinese: string, english: string, customQuery = '', signal?: AbortSignal) {
  const fallbacks = [...(semanticQueries[chinese.trim()] ?? []), english.trim(), chinese.trim()]
  const queries = [...new Set([customQuery.trim(), ...fallbacks].filter(Boolean))]
  let lastError: unknown
  for (const query of queries) {
    try {
      const results = await queryCommons(query, signal)
      if (results.length) return { results, usedQuery: query }
    } catch (error) {
      lastError = error
    }
  }
  if (lastError && queries.length === 1) throw lastError
  return { results: [], usedQuery: '' }
}