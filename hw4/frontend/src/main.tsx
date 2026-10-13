import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './auth.tsx'
import { ChatSearchProvider } from './chatSearch.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ChatSearchProvider>
          <App />
        </ChatSearchProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
