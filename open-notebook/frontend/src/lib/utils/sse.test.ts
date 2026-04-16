import { describe, expect, it } from 'vitest'

import { flushSSEBuffer, parseSSEChunk } from './sse'

describe('SSE parsing helpers', () => {
  it('parses multiple events from a single chunk', () => {
    const parsed = parseSSEChunk('', [
      'data: {"type":"dag_update","node_id":"n1"}',
      '',
      'data: {"type":"complete","answer":"done"}',
      '',
    ].join('\n') + '\n', JSON.parse)

    expect(parsed.buffer).toBe('')
    expect(parsed.events).toEqual([
      { type: 'dag_update', node_id: 'n1' },
      { type: 'complete', answer: 'done' },
    ])
  })

  it('retains incomplete payloads until the next chunk arrives', () => {
    const first = parseSSEChunk('', 'data: {"type":"dag_up', JSON.parse)
    expect(first.events).toEqual([])

    const second = parseSSEChunk(first.buffer, 'date","node_id":"n2"}\n\n', JSON.parse)
    expect(second.buffer).toBe('')
    expect(second.events).toEqual([{ type: 'dag_update', node_id: 'n2' }])
  })

  it('flushes a trailing event when the stream ends without a final blank line', () => {
    const trailing = flushSSEBuffer('data: {"type":"complete","answer":"final"}', JSON.parse)
    expect(trailing).toEqual([{ type: 'complete', answer: 'final' }])
  })
})
