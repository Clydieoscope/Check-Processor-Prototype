import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import CheckUpload from './CheckUpload.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <CheckUpload />
  </StrictMode>,
)
