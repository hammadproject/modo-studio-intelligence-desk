export function cleanMessageContent(content: string) {
  return content
    .replace(/\u3010\s*sources?\s*:[^\u3011]+\u3011/gi, '')
    .replace(/\[\s*sources?\s*:\s*[^\]]+\]/gi, '')
    .replace(/\s+([.,;!?])/g, '$1')
    .trim()
}

export function plainTextPreview(message: string) {
  const plain = cleanMessageContent(message)
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/[`*_~>#|]/g, '')
    .replace(/^\s*(?:[-+] |\d+[.)]\s+)/gm, '')
    .replace(/\s+/g, ' ')
    .trim()

  return plain.length > 76 ? `${plain.slice(0, 73)}…` : plain
}
