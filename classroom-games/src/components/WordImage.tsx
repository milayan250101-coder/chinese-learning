import { ImageOff } from 'lucide-react'
import { useState } from 'react'
import type { VocabularyImage } from '../types'

type WordImageProps = {
  image: VocabularyImage | null
  alt: string
  className?: string
}

export default function WordImage({ image, alt, className = '' }: WordImageProps) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null)

  if (!image || failedUrl === image.url) {
    return <span className={`word-image-placeholder ${className}`} role="img" aria-label={`${alt}：暂无图片`}><ImageOff size={20} /><small>暂无图片</small></span>
  }

  const imageUrl = className.includes('result-thumbnail') ? image.thumbnailUrl : image.url
  return <img className={`word-image ${className}`} src={imageUrl} alt={alt} loading={className.includes('print-image') ? 'eager' : 'lazy'} onError={() => setFailedUrl(imageUrl)} />
}