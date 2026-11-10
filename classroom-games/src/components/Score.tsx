type ScoreProps = {
  score: number
  label: string
  unit: string
  best: number
  bestLabel: string
}

export default function Score({ score, label, unit, best, bestLabel }: ScoreProps) {
  return (
    <div className="score-stack" aria-live="polite"><div className="score-chip"><span className="score-star">★</span><span>{label}</span><strong>{score} {unit}</strong></div><span className="best-score">{bestLabel}: <strong>{best} {unit}</strong></span></div>
  )
}