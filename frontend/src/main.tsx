import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { MantineProvider } from '@mantine/core'
import '@mantine/core/styles.css'
import '@mantine/notifications/styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MantineProvider defaultColorScheme="dark" theme={{ fontFamily: 'Inter, system-ui, Avenir, Helvetica, Arial, sans-serif' }}>
      <App />
    </MantineProvider>
  </StrictMode>,
)
