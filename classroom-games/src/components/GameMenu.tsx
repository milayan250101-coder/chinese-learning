import { BookOpenCheck, Languages, Layers, Link2 } from 'lucide-react'
import type { GameId, Language } from '../types'
import type { text } from '../data/translations'

type GameMenuProps = {
  onSelect: (game: GameId) => void
  language: Language | null
  copy: (typeof text)[Language]
}

const games: { id: GameId; icon: typeof Languages; number: string }[] = [
  { id: 'pinyin', icon: Languages, number: '01' },
  { id: 'word', icon: BookOpenCheck, number: '02' },
  { id: 'matching', icon: Link2, number: '03' },
  { id: 'flashcards', icon: Layers, number: '04' },
]

export default function GameMenu({ onSelect, language, copy }: GameMenuProps) {
  return (
    <section className={`game-menu ${language ? '' : 'locked'}`} aria-label={copy.chooseGame}>
      <div className="game-grid">
      {games.map(({ id, icon: Icon, number }) => (
        <button key={id} className={`game-card game-card-${number}`} onClick={() => onSelect(id)} disabled={!language}>
          <span className="game-card-top"><span className="game-number">{number}</span><span className="game-card-icon"><Icon size={20} strokeWidth={1.8} /></span></span>
          <strong>{copy.games[id]}</strong>
          <small>{copy.descriptions[id]}</small>
        </button>
      ))}
      </div>
      {!language && <p className="locked-note">{copy.selectLanguage}</p>}
    </section>
  )
}