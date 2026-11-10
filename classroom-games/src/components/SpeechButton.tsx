import { Volume2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { speechLocales } from '../data/translations'
import type { Language, SpeechLocale } from '../types'

type SpeechButtonProps = {
  value: string
  language: Language | 'zh'
  rate: number
  label?: string
}

let activeUtterance: SpeechSynthesisUtterance | null = null
let resetActiveButton: (() => void) | null = null

function stopCurrentSpeech() {
  window.speechSynthesis.cancel()
  resetActiveButton?.()
  resetActiveButton = null
  activeUtterance = null
}

export default function SpeechButton({ value, language, rate, label }: SpeechButtonProps) {
  const [speaking, setSpeaking] = useState(false)
  const ownUtterance = useRef<SpeechSynthesisUtterance | null>(null)

  useEffect(() => () => {
    if (ownUtterance.current && activeUtterance === ownUtterance.current) stopCurrentSpeech()
  }, [])

  function speak() {
    if (!('speechSynthesis' in window) || !value.trim()) return
    stopCurrentSpeech()

    const utterance = new SpeechSynthesisUtterance(value)
    ownUtterance.current = utterance
    utterance.lang = speechLocales[language] satisfies SpeechLocale
    utterance.rate = rate
    utterance.onstart = () => {
      if (activeUtterance === utterance) {
        resetActiveButton = () => setSpeaking(false)
        setSpeaking(true)
      }
    }
    utterance.onend = utterance.onerror = () => {
      if (activeUtterance === utterance) {
        activeUtterance = null
        resetActiveButton = null
        setSpeaking(false)
      }
    }
    activeUtterance = utterance
    window.speechSynthesis.speak(utterance)
  }

  return <button className={`speech-button ${speaking ? 'speaking' : ''}`} type="button" onClick={speak} aria-label={label ?? value} title={label ?? value}><Volume2 size={17} /></button>
}