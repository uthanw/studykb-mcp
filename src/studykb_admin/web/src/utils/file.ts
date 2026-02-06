export function getFileIcon(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase()
  switch (ext) {
    case 'md': return '\u{1F4DD}'
    case 'py': return '\u{1F40D}'
    case 'js':
    case 'ts': return '\u{1F4DC}'
    case 'json': return '\u{1F4CB}'
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'gif': return '\u{1F5BC}\uFE0F'
    default: return '\u{1F4C4}'
  }
}

export function isMarkdownFile(path: string): boolean {
  return path.endsWith('.md')
}
