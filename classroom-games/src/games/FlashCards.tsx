import { useState } from 'react'
import SpeechButton from '../components/SpeechButton'
import WordImage from '../components/WordImage'
import type { Language, VocabularyWord } from '../types'
import type { text } from '../data/translations'

type FlashCardsProps = { word: VocabularyWord; language: Language; rate: number; answer: string | null; starsEarned: number; showImages: boolean; showPinyin: boolean; allowSpeech: boolean; onLearned: () => void; onNeedPractice: () => void; copy: (typeof text)[Language] }

export default function FlashCards({ word, language, rate, answer, starsEarned, showImages, showPinyin, allowSpeech, onLearned, onNeedPractice, copy }: FlashCardsProps) {
  const [flipped, setFlipped] = useState(false)
  const learned = answer === word.id

  return (
    <section className="flash-stage">
      <div className={`flip-card ${flipped ? 'flipped' : ''}`}>
        <div className="flip-card-inner">
          <button type="button" className="flip-face flip-front" onClick={() => setFlipped(true)}><span className="flash-label">中文</span><strong>{word.chinese}</strong>{showImages && <WordImage image={word.image} alt={word.chinese} className="flash-image" />}<span className="flip-action">{copy.tapToFlip} <span>↗</span></span></button>
          <div className="flip-face flip-back"><span className="flash-label">中文 · {showPinyin ? 'PINYIN · ' : ''}{language.toUpperCase()}</span><div className="flash-chinese"><strong>{word.chinese}</strong>{allowSpeech && <SpeechButton value={word.chinese} language="zh" rate={rate} label={word.chinese} />}</div>{showImages && <WordImage image={word.image} alt={word.chinese} className="flash-image" />}{showPinyin && <span className="flash-pinyin">{word.pinyin}</span>}<div className="flash-translation"><strong>{word.translations[language]}</strong>{allowSpeech && <SpeechButton value={word.translations[language]} language={language} rate={rate} label={word.translations[language]} />}</div><button className="flip-action" onClick={() => setFlipped(false)}>{copy.tapToFlip} <span>↻</span></button></div>
        </div>
      </div>
      <div className="flash-review-actions"><button className={`learned-button ${learned ? 'learned' : ''}`} onClick={onLearned} disabled={!flipped || answer !== null}><span>{learned ? '✓' : '+'}</span>{learned ? copy.learned : copy.gotIt}{!learned && <><b>+10</b><b>+1 ⭐</b></>}{starsEarned > 0 && <span className="star-pop">+{starsEarned} ⭐</span>}</button>{flipped && <button className="secondary-action review-later-button" onClick={onNeedPractice} disabled={answer !== null}>{copy.needPractice}</button>}</div>
    </section>
  )
}