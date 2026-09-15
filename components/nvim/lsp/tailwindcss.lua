return {
  cmd = { 'tailwindcss-language-server', '--stdio' },
  filetypes = { 'html', 'css', 'scss', 'javascript', 'javascriptreact', 'typescript', 'typescriptreact' },
  root_markers = { 'tailwind.config.js', 'tailwind.config.ts', '.git' }
}
