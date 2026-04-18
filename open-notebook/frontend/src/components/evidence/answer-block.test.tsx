import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { AnswerBlock } from './answer-block'

describe('AnswerBlock', () => {
  const response = {
    answer: '这是当前回答。',
    confidence: 0.84,
    evidence_cards: [],
    memory_updates: [],
    run_id: 'run:demo',
    suggested_followups: ['继续追问这个问题'],
    mode: 'text' as const,
  }

  it('disables suggested followups while submission is blocked', () => {
    const onSuggestedFollowup = vi.fn()

    render(
      <AnswerBlock
        response={response}
        disableSuggestedFollowups={true}
        onSuggestedFollowup={onSuggestedFollowup}
      />
    )

    const followupButton = screen.getByRole('button', { name: '继续追问这个问题' })
    expect(followupButton).toBeDisabled()

    fireEvent.click(followupButton)
    expect(onSuggestedFollowup).not.toHaveBeenCalled()
  })
})
