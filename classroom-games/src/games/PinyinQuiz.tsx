import { Check, X } from 'lucide-react'
import { useState } from 'react'
import SpeechButton from '../components/SpeechButton'
import WordImage from '../components/WordImage'
import type { Language, VocabularyWord } from '../types'
import type { text } from '../data/translations'

type PinyinQuizProps = { word: VocabularyWord; distractors: VocabularyWord[]; rate: number; answer: string | null; starsEarned: number; showImages: boolean; allowSpeech: boolean; onAnswer: (id: string) => void; copy: (typeof text)[Language] }

export default function PinyinQuiz({ word, distractors, rate, answer, starsEarned, showImages, allowSpeech, onAnswer, copy }: PinyinQuizProps) {
  const [choices] = useState(() => {
    const options = [word, ...distractors.filter((item) => item.id !== word.id).slice(0, 3)]
    return options.sort(() => Math.random() - 0.5)
  })
  const correct = answer === word.id

  return (
    <section className="question-card">
      <p className="question-prompt">{copy.choosePinyin}</p>
      <div className="prompt-word"><strong>{word.chinese}</strong>{allowSpeech && <SpeechButton value={word.chinese} language="zh" rate={rate} label={word.chinese} />}</div>
      {showImages && <WordImage image={word.image} alt={word.chinese} className="quiz-image" />}
      <div className="choice-list">{choices.map((choice, index) => {
        const isCorrect = answer !== null && choice.id === word.id
        const isWrong = answer === choice.id && !isCorrect
        return <button key={choice.id} className={`choice-row ${isCorrect ? 'correct' : ''} ${isWrong ? 'incorrect' : ''}`} onClick={() => onAnswer(choice.id)} disabled={answer !== null}>
          <span className="choice-letter">{String.fromCharCode(65 + index)}</span><span className="choice-text">{choice.pinyin}</span>{isCorrect && <Check size={18} />}{isWrong && <X size={18} />}
        </button>
      })}</div>
      {answer !== null && <div className={`answer-feedback ${correct ? 'is-correct' : 'is-wrong'}`} role="status"><span>{correct ? <Check size={16} /> : <X size={16} />}</span><strong>{correct ? copy.correct : copy.incorrect}</strong>{!correct && <span>{copy.correctAnswer}: {word.pinyin}</span>}{correct && <b>+10 {copy.scoreUnit}</b>}{correct && starsEarned > 0 && <span className="inline-star-award">+{starsEarned} ⭐</span>}</div>}
    </section>
  )
}