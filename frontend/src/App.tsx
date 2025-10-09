import { useEffect, useRef, useState } from 'react'
import { AppShell, Group, Stack, TextInput, PasswordInput, Button, Textarea, Paper, ScrollArea, Text, Title, Container, Card, Space } from '@mantine/core'
import { Notifications, notifications } from '@mantine/notifications'
import { IconPaperclip } from '@tabler/icons-react'

function UI() {
  const [openaiKey, setOpenaiKey] = useState('')
  const [sendgridKey, setSendgridKey] = useState('')
  const [fromEmail, setFromEmail] = useState('')
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [pitch, setPitch] = useState("I'm reaching out to connect and explore potential opportunities for collaboration. I have experience in technology solutions and would love to discuss how we might work together.")
  const logRef = useRef<HTMLDivElement | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  function appendLog(msg: string) {
    const time = new Date().toLocaleTimeString()
    const el = logRef.current
    if (el) {
      el.textContent += `[${time}] ${msg}\n`
      el.scrollTop = el.scrollHeight
    }
  }

  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const url = `${proto}://${window.location.host}/ws/progress`
      const ws = new WebSocket(url)
      wsRef.current = ws
      ws.onopen = () => appendLog('✅ WebSocket connected - Real-time updates enabled')
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data)
          // Format different event types for better readability
          switch (data.type) {
            case 'reply_received':
              appendLog(`📨 REPLY RECEIVED from ${data.from}`)
              appendLog(`   Subject: ${data.subject}`)
              break
            case 'reply_pipeline_started':
              appendLog(`🤖 Reply Pipeline ACTIVATED for ${data.from}`)
              appendLog(`   Processing automated response...`)
              break
            case 'reply_sent':
              appendLog(`✅ Auto-reply SENT to ${data.from}`)
              break
            case 'reply_error':
              appendLog(`❌ Reply pipeline error: ${data.error}`)
              break
            case 'cold_send_started':
              appendLog(`📤 Sending cold email to ${data.email}...`)
              break
            case 'cold_send_completed':
              appendLog(`✅ Cold email sent to ${data.email}`)
              break
            case 'cold_send_error':
              appendLog(`❌ Error sending to ${data.email}: ${data.error}`)
              break
            case 'bulk_started':
              appendLog(`📦 Bulk send started (${data.count} recipients)`)
              break
            case 'bulk_completed':
              appendLog(`✅ Bulk send completed (${data.count} emails)`)
              break
            default:
              appendLog('Event: ' + JSON.stringify(data))
          }
        } catch {
          appendLog('WS message: ' + ev.data)
        }
      }
      ws.onerror = () => appendLog('⚠️ WebSocket error')
      ws.onclose = () => appendLog('🔌 WebSocket closed')
    } catch (e: any) {
      appendLog('WS init error: ' + String(e))
    }
    return () => {
      try { wsRef.current?.close() } catch {}
      wsRef.current = null
    }
  }, [])

  async function saveKeys() {
    try {
      await fetch('/api/keys', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ openai_api_key: openaiKey, sendgrid_api_key: sendgridKey, from_email: fromEmail }) })
      notifications.show({ title: 'Keys saved', message: 'Saved for this session', color: 'green' })
    } catch (e: any) {
      notifications.show({ title: 'Error saving keys', message: String(e), color: 'red' })
    }
  }

  async function sendSingle() {
    if (!email) { notifications.show({ title: 'Enter recipient email', message: '', color: 'yellow' }); return }
    try {
      const res = await fetch('/api/cold/send', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, name, pitch }) })
      const j = await res.json()
      appendLog('Send result: ' + JSON.stringify(j))
      if (j.status === 'ok') notifications.show({ title: 'Sent', message: email, color: 'green' })
      else notifications.show({ title: 'Send error', message: j.error || 'Unknown', color: 'red' })
    } catch (e: any) {
      appendLog('Error: ' + e)
      notifications.show({ title: 'Network error', message: String(e), color: 'red' })
    }
  }

  async function uploadCsv(file: File | null) {
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    try {
      const res = await fetch('/api/cold/upload', { method: 'POST', body: fd })
      const j = await res.json()
      appendLog('Bulk: ' + JSON.stringify(j))
      if (j.status === 'ok') notifications.show({ title: 'Bulk started', message: `${j.count} queued`, color: 'green' })
      else notifications.show({ title: 'Bulk error', message: j.error || 'Unknown', color: 'red' })
    } catch (e: any) {
      appendLog('Upload error: ' + e)
      notifications.show({ title: 'Upload error', message: String(e), color: 'red' })
    }
  }

  const fileInputRef = useRef<HTMLInputElement | null>(null)

  return (
    <AppShell navbar={{ width: 420, breakpoint: 'md' }} padding="xl" header={{ height: 88 }}>
      <AppShell.Header>
        <Container size={1440} style={{ height: '100%' }}>
          <Stack h="100%" align="center" justify="center" gap={4}>
            <Title order={2} ta="center">Cold Email Agent</Title>
            <Text c="dimmed" size="sm" style={{ fontStyle: 'italic' }} ta="center">Simple, fast outreach</Text>
          </Stack>
        </Container>
      </AppShell.Header>
      <AppShell.Navbar>
        <Stack p="lg" gap="lg" style={{ height: '100%' }}>
          <Title order={4}>Settings</Title>
          <PasswordInput size="md" label="OpenAI API Key" placeholder="sk-..." value={openaiKey} onChange={(e) => setOpenaiKey(e.currentTarget.value)} />
          <PasswordInput size="md" label="SendGrid API Key" placeholder="SG...." value={sendgridKey} onChange={(e) => setSendgridKey(e.currentTarget.value)} />
          <TextInput size="md" label="From Email (Sender)" placeholder="you@example.com" value={fromEmail} onChange={(e) => setFromEmail(e.currentTarget.value)} />
          <Text size="xs" c="dimmed" style={{ marginTop: -8 }}>
            Use the email address verified in your SendGrid account. <a href="https://app.sendgrid.com/settings/sender_auth" target="_blank" rel="noopener noreferrer" style={{ color: '#228be6' }}>Set up sender verification</a>
          </Text>
          <Button size="md" fullWidth onClick={saveKeys}>Save Keys</Button>
          <Space h="md" />
          <Text size="xs" c="dimmed">Tip: Upload a CSV to send to many recipients at once.</Text>
        </Stack>
      </AppShell.Navbar>
      <AppShell.Main>
        <Container size={1440}>
          <Stack gap="xl" my="xl" align="stretch">
            <Card withBorder radius="md" p="xl" shadow="sm" style={{ width: '100%', maxWidth: 1200 }}>
              <Stack gap="md">
                <Title order={3}>Cold Outreach</Title>
                <Text c="dimmed" size="sm">Send a single email or attach a CSV to send in bulk.</Text>
                <TextInput size="md" label="Recipient Email" placeholder="name@company.com" value={email} onChange={(e) => setEmail(e.currentTarget.value)} />
                <TextInput size="md" label="Recipient Name (optional)" placeholder="John Doe" value={name} onChange={(e) => setName(e.currentTarget.value)} />
                <Textarea size="md" label="Pitch" value={pitch} onChange={(e) => setPitch(e.currentTarget.value)} minRows={5} />
                <Group gap="md">
                  <Button size="md" onClick={sendSingle}>Send</Button>
                  <input ref={fileInputRef} type="file" accept=".csv" style={{ display: 'none' }} onChange={(e) => uploadCsv(e.target.files?.[0] || null)} />
                  <Button variant="light" leftSection={<IconPaperclip size={18} />} onClick={() => fileInputRef.current?.click()}>
                    Attach CSV
                  </Button>
                </Group>
              </Stack>
            </Card>
            <Card withBorder radius="md" p="xl" shadow="sm" style={{ width: '100%', maxWidth: 1200 }}>
              <Title order={4} mb="sm">Activity</Title>
              <Paper withBorder p="xs">
                <ScrollArea h={300} type="always" offsetScrollbars>
                  <div ref={logRef} style={{ padding: 12, whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: 13 }} />
                </ScrollArea>
              </Paper>
            </Card>
          </Stack>
        </Container>
      </AppShell.Main>
    </AppShell>
  )
}

export default function App() {
  return (
    <>
      <Notifications />
      <UI />
    </>
  )
}
