import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/base.css'
import './styles/cohort-analysis.css'
import App from './App.tsx'
import './styles/compare-stability.css'
import './styles/twin-anatomy.css'
import './styles/twin-reliability.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
