import { Check, Link2, X } from 'lucide-react'
import { useState } from 'react'
import WordImage from '../components/WordImage'
import type { Language, VocabularyWord } from '../types'
import type { text } from '../data/translations'

type MatchingGameProps = { words: VocabularyWord[]; answer: string | null; starsEarned: number; showImages: boolean; onPairCorrect: (id: string) => void; onWrongPair: (firstId: string, secondId: string) => void; onComplete: () => void; copy: (typeof text)[Language] }

export default function MatchingGame({ words, answer, starsEarned, showImages, onPairCorrect, onWrongPair, onComplete, copy }: MatchingGameProps) {
  const [matched, setMatched] = useState<string[]>([])
  const [selected, setSelected] = useState<{ id: string; side: 'pinyin' | 'chinese' } | null>(null)
  const [wrong, setWrong] = useState(false)
  const meanings = [...words].reverse()
  const complete = matched.length === words.length

  function pick(id: string, side: 'pinyin' | 'chinese') {
    if (matched.includes(id) || complete || answer !== null) return
    setWrong(false)
    if (!selected || selected.side === side) {
      setSelected({ id, side })
      return
    }
    if (selected.id === id) {
      const nextMatched = [...matched, id]
      setMatched(nextMatched)
      setSelected(null)
      onPairCorrect(id)
      if (nextMatched.length === words.length) onComplete()
      return
    }
    setWrong(true)
    setSelected(null)
    onWrongPair(selected.id, id)
  }

  return (
    <section className="question-card matching-question">
      <p className="question-prompt">{copy.matchInstruction}</p>
      <div className="match-columns">
        <div>{words.map((word) => <button key={word.id} className={`match-choice ${selected?.id === word.id && selected.side === 'pinyin' ? 'selected' : ''} ${matched.includes(word.id) ? 'matched' : ''}`} onClick={() => pick(word.id, 'pinyin')} disabled={matched.includes(word.id) || answer !== null}><span>{word.pinyin}</span>{matched.includes(word.id) && <Check size={16} />}</button>)}</div>
        <span className="match-link"><Link2 size={18} /></span>
        <div>{meanings.map((word) => <button key={word.id} className={`match-choice match-chinese ${selected?.id === word.id && selected.side === 'chinese' ? 'selected' : ''} ${matched.includes(word.id) ? 'matched' : ''}`} onClick={() => pick(word.id, 'chinese')} disabled={matched.includes(word.id) || answer !== null}>{showImages && <WordImage image={word.image} alt={word.chinese} className="match-image" />}<span>{word.chinese}</span>{matched.includes(word.id) && <Check size={16} />}</button>)}</div>
      </div>
      <div className={`match-feedback ${wrong ? 'is-wrong' : complete ? 'is-correct' : ''}`} role="status">{wrong ? <><X size={15} />{copy.incorrect}</> : complete ? <><Check size={15} />{copy.matchComplete} <b>+{words.length * 10} {copy.scoreUnit}</b></> : <>{matched.length} / {words.length} {copy.matched}</>}{starsEarned > 0 && <strong className="inline-star-award">+{starsEarned} ⭐</strong>}</div>
    </section>
  )
}