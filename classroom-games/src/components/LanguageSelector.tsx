import { languageOptions } from '../data/translations'
import type { Language } from '../types'

type LanguageSelectorProps = {
  value: Language | null
  onChange: (language: Language) => void
  label: string
}

export default function LanguageSelector({ value, onChange, label }: LanguageSelectorProps) {
  return (
    <div className="language-picker" role="group" aria-label={label}>
      {languageOptions.map((option) => (
        <button key={option.id} className={`language-option ${value === option.id ? 'selected' : ''}`} onClick={() => onChange(option.id)} aria-pressed={value === option.id}>
          <span className="language-flag">{option.flag}</span><span>{option.name}</span>
        </button>
      ))}
    </div>
  )
}