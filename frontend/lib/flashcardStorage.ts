import { Flashcard, FlashcardDeck, FlashcardRating } from './types'

const STORAGE_KEY = 'lumina-flashcard-decks'

// ── SM-2 Algorithm ──────────────────────────────
// Implementation of the SuperMemo SM-2 spaced repetition algorithm.

export function sm2(card: Flashcard, rating: FlashcardRating): Flashcard {
  let { easeFactor, interval, repetitions } = card

  if (rating >= 3) {
    // Correct response
    if (repetitions === 0) {
      interval = 1
    } else if (repetitions === 1) {
      interval = 6
    } else {
      interval = Math.round(interval * easeFactor)
    }
    repetitions += 1
  } else {
    // Incorrect — reset
    repetitions = 0
    interval = 1
  }

  // Update ease factor
  easeFactor = easeFactor + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))
  if (easeFactor < 1.3) easeFactor = 1.3

  const now = new Date()
  const nextReview = new Date(now.getTime() + interval * 24 * 60 * 60 * 1000)

  return {
    ...card,
    easeFactor: Math.round(easeFactor * 100) / 100,
    interval,
    repetitions,
    nextReview: nextReview.toISOString(),
    lastReview: now.toISOString(),
  }
}

// ── Storage ──────────────────────────────

export function loadDecks(): FlashcardDeck[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const decks: FlashcardDeck[] = JSON.parse(raw)
    return decks.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
  } catch {
    return []
  }
}

export function saveDeck(deck: FlashcardDeck): void {
  if (typeof window === 'undefined') return
  const decks = loadDecks()
  const idx = decks.findIndex((d) => d.id === deck.id)
  deck.updatedAt = new Date().toISOString()
  if (idx >= 0) {
    decks[idx] = deck
  } else {
    decks.unshift(deck)
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(decks))
}

export function deleteDeck(deckId: string): void {
  if (typeof window === 'undefined') return
  const decks = loadDecks().filter((d) => d.id !== deckId)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(decks))
}

export function createDeck(
  topic: string,
  rawCards: { front: string; back: string; difficulty: number }[]
): FlashcardDeck {
  const now = new Date().toISOString()
  const cards: Flashcard[] = rawCards.map((c, i) => ({
    id: `${Date.now()}-${i}-${Math.random().toString(36).slice(2, 7)}`,
    front: c.front,
    back: c.back,
    difficulty: c.difficulty || 3,
    easeFactor: 2.5,
    interval: 0,
    repetitions: 0,
    nextReview: now,
  }))
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    topic,
    cards,
    createdAt: now,
    updatedAt: now,
    totalReviews: 0,
  }
}

export function getDueCards(deck: FlashcardDeck): Flashcard[] {
  const now = new Date()
  return deck.cards.filter((c) => new Date(c.nextReview) <= now)
}

export function getDeckStats(deck: FlashcardDeck) {
  const now = new Date()
  const due = deck.cards.filter((c) => new Date(c.nextReview) <= now).length
  const learned = deck.cards.filter((c) => c.repetitions >= 2).length
  const mastered = deck.cards.filter((c) => c.interval >= 21).length
  return { total: deck.cards.length, due, learned, mastered }
}
