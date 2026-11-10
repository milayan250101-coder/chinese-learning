import { ArrowLeft, BookOpen, Volume2 } from 'lucide-react'
import { languageOptions } from '../data/translations'
import type { Language } from '../types'

type HeaderProps = {
  language: Language | null
  rate: number
  stars: number
  starPulse: number
  starPulseAmount: number
  onRateChange: (rate: number) => void
  onBack?: () => void
  backLabel: string
  rateLabel: string
}

export default function Header({ language, rate, stars, starPulse, starPulseAmount, onRateChange, onBack, backLabel, rateLabel }: HeaderProps) {
  const option = languageOptions.find((item) => item.id === language)

  return (
    <header className="topbar">
      <div className="topbar-left">
        {onBack && <button className="back-button" onClick={onBack}><ArrowLeft size={16} /><span>{backLabel}</span></button>}
        <a className="brand" href="#home" onClick={(event) => { if (onBack) { event.preventDefault(); onBack() } }}><span className="brand-mark"><BookOpen size={18} /></span><span>中文词汇游戏<span className="brand-dot">.</span></span></a>
      </div>
      <div className="topbar-right">
        {option && <span className="current-language"><span>{option.flag}</span>{option.name}</span>}
        <span className="star-total" aria-label={`累计 ${stars} 颗星星`}><span>⭐</span><strong>{stars}</strong>{starPulse > 0 && <span key={starPulse} className="star-pop">+{starPulseAmount} ⭐</span>}</span>
        <label className="rate-control"><Volume2 size={15} /><span>{rateLabel}</span><select value={rate} onChange={(event) => onRateChange(Number(event.target.value))} aria-label={rateLabel}><option value={0.75}>0.75×</option><option value={1}>1.0×</option><option value={1.25}>1.25×</option></select></label>
      </div>
    </header>
  )
}