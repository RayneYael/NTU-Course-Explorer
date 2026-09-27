import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Loaded at runtime rather than via <link> in index.html so the single-file bundle
// (html-inline) doesn't try to inline a remote stylesheet.
const fonts = document.createElement('link')
fonts.rel = 'stylesheet'
fonts.href =
  'https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Schibsted+Grotesk:wght@400;500;600;700&display=swap'
document.head.appendChild(fonts)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
