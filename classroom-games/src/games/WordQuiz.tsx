import { Check, X } from 'lucide-react'
import { useState } from 'react'
import SpeechButton from '../components/SpeechButton'
import WordImage from '../components/WordImage'
import type { Language, VocabularyWord } from '../types'
import type { text } from '../data/translations'

type WordQuizProps = { word: VocabularyWord; distractors: VocabularyWord[]; rate: number; answer: string | null; starsEarned: number; showImages: boolean; allowSpeech: boolean; onAnswer: (id: string) => void; copy: (typeof text)[Language] }

export default function WordQuiz({ word, distractors, rate, answer, starsEarned, showImages, allowSpeech, onAnswer, copy }: WordQuizProps) {
  const [choices] = useState(() => {
    const options = [word, ...distractors.filter((item) => item.id !== word.id).slice(0, 3)]
    return options.sort(() => Math.random() - 0.5)
  })
  const correct = answer === word.id

  return (
    <section className="question-card">
      <p className="question-prompt">{copy.chooseChinese}</p>
      <div className="pinyin-prompt">{word.pinyin}</div>
      <div className="choice-list">{choices.map((choice, index) => {
        const isCorrect = answer !== null && choice.id === word.id
        const isWrong = answer === choice.id && !isCorrect
        return <div key={choice.id} className={`choice-row ${isCorrect ? 'correct' : ''} ${isWrong ? 'incorrect' : ''}`}>
          <button className="choice-pick" onClick={() => onAnswer(choice.id)} disabled={answer !== null}><span className="choice-letter">{String.fromCharCode(65 + index)}</span>{showImages && <WordImage image={choice.image} alt={choice.chinese} className="answer-image" />}<span className="choice-hanzi">{choice.chinese}</span></button>{allowSpeech && <SpeechButton value={choice.chinese} language="zh" rate={rate} label={choice.chinese} />}{isCorrect && <Check size={18} />}{isWrong && <X size={18} />}
        </div>
      })}</div>
      {answer !== null && <div className={`answer-feedback ${correct ? 'is-correct' : 'is-wrong'}`} role="status"><span>{correct ? <Check size={16} /> : <X size={16} />}</span><strong>{correct ? copy.correct : copy.incorrect}</strong>{!correct && <span>{copy.correctAnswer}: {word.chinese}</span>}{correct && <b>+10 {copy.scoreUnit}</b>}{correct && starsEarned > 0 && <span className="inline-star-award">+{starsEarned} ⭐</span>}</div>}
    </section>
  )
}