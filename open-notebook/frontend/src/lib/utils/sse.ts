export interface ParsedSSEChunk<T> {
  events: T[]
  buffer: string
}

function parseEventBlock<T>(block: string, parseEvent: (payload: string) => T): T[] {
  const dataLines = block
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())

  if (dataLines.length === 0) {
    return []
  }

  return [parseEvent(dataLines.join('\n'))]
}

export function parseSSEChunk<T>(
  buffer: string,
  chunk: string,
  parseEvent: (payload: string) => T
): ParsedSSEChunk<T> {
  const combined = buffer + chunk
  const blocks = combined.split(/\r?\n\r?\n/)
  const nextBuffer = blocks.pop() ?? ''
  const events = blocks.flatMap((block) => parseEventBlock(block, parseEvent))

  return {
    events,
    buffer: nextBuffer,
  }
}

export function flushSSEBuffer<T>(
  buffer: string,
  parseEvent: (payload: string) => T
): T[] {
  const trimmed = buffer.trim()
  if (!trimmed) {
    return []
  }
  return parseEventBlock(trimmed, parseEvent)
}
