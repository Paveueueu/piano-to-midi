// Polish plurals have three forms: 1 nagranie, 2–4 nagrania, 5+ nagrań (but 12–14 nagrań).
// Messages list them in that order; two-form messages fall back to one / many.
function polish(choice: number, choicesLength: number): number {
  const n = Math.abs(choice)
  if (choicesLength < 3) return n === 1 ? 0 : 1
  if (n === 1) return 0
  const tens = n % 100
  const ones = n % 10
  return ones >= 2 && ones <= 4 && (tens < 12 || tens > 14) ? 1 : 2
}

export default defineI18nConfig(() => ({
  pluralRules: { pl: polish },
}))
