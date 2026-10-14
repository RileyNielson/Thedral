const escapeHtml = (text) => text
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')

export const contentToHtml = (content) => {
  if (!content) return ''
  if (!/<\/?(?:p|strong|em|br|ul|ol|li|blockquote)\b/i.test(content)) {
    return content.split(/\n\n+/).map(paragraph => `<p>${escapeHtml(paragraph.trim())}</p>`).join('')
  }

  const parsed = new DOMParser().parseFromString(content, 'text/html')
  const allowedTags = new Set(['P', 'STRONG', 'EM', 'BR', 'UL', 'OL', 'LI', 'BLOCKQUOTE'])
  const sanitizeNode = (node) => {
    if (node.nodeType === Node.TEXT_NODE) return document.createTextNode(node.textContent || '')
    if (node.nodeType !== Node.ELEMENT_NODE) return document.createDocumentFragment()
    if (!allowedTags.has(node.tagName)) {
      const fragment = document.createDocumentFragment()
      for (const child of node.childNodes) fragment.append(sanitizeNode(child))
      return fragment
    }
    const clean = document.createElement(node.tagName.toLowerCase())
    for (const child of node.childNodes) clean.append(sanitizeNode(child))
    return clean
  }
  const container = document.createElement('div')
  for (const child of parsed.body.childNodes) container.append(sanitizeNode(child))
  return container.innerHTML
}

export const htmlToText = (html) => {
  if (!html) return ''
  const parsed = new DOMParser().parseFromString(html, 'text/html')
  const paragraphs = Array.from(parsed.body.querySelectorAll('p, li, blockquote'))
    .map(element => element.textContent.trim())
    .filter(Boolean)
  return (paragraphs.length ? paragraphs.join('\n\n') : parsed.body.textContent || '').trim()
}
