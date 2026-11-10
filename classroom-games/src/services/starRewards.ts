export type StarAward = {
  stars: number
  streak: number
  duplicate: boolean
}

export class StarRewardSession {
  private rewardedAnswers = new Set<string>()
  private completedExercises = new Set<string>()
  private correctStreak = 0

  reset() {
    this.rewardedAnswers.clear()
    this.completedExercises.clear()
    this.correctStreak = 0
  }

  breakStreak() {
    this.correctStreak = 0
  }

  awardCorrect(answerId: string): StarAward {
    if (this.rewardedAnswers.has(answerId)) {
      return { stars: 0, streak: this.correctStreak, duplicate: true }
    }
    this.rewardedAnswers.add(answerId)
    this.correctStreak += 1
    const streakBonus = this.correctStreak === 3 ? 1 : this.correctStreak === 5 ? 2 : 0
    return { stars: 1 + streakBonus, streak: this.correctStreak, duplicate: false }
  }

  awardCompletion(exerciseId: string) {
    if (this.completedExercises.has(exerciseId)) return 0
    this.completedExercises.add(exerciseId)
    return 3
  }
}