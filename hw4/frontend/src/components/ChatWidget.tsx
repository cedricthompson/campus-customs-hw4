import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  fetchChatHistory,
  formatPrice,
  sendChatMessage,
  type ChatMessage,
  type PageContext,
  type PageResults,
} from '../api'
import { useAuth } from '../auth'
import { onOpenChat } from '../chatEvents'
import { useChatSearch } from '../chatSearch'
import HandsomeDan from './HandsomeDan'

function greetingFor(firstName: string | null | undefined): ChatMessage {
  const intro = firstName
    ? `Welcome back, ${firstName}! I'm Handsome Dan, and I'll remember our chat for next time.`
    : "Hi! I'm Handsome Dan, your Campus Customs shopping assistant."
  return {
    role: 'assistant',
    greeting: true,
    content:
      `${intro} I can find gear by type, color, or budget, check sizes and stock, ` +
      'and help you pick a gift.' +
      (firstName ? '' : ' Log in if you want me to remember our chat.'),
  }
}

const GENERAL_SUGGESTIONS = [
  'Show me hoodies',
  'What products are available?',
  'Help me find a gift',
  'Anything under $40?',
]
const PRODUCT_SUGGESTIONS = [
  'Does this come in another color?',
  'What sizes are in stock?',
  'Show me similar items',
]

// The current page, with the product id when a product page is open.
function pageContext(pathname: string): PageContext {
  const match = pathname.match(/^\/products\/([^/]+)$/)
  return match ? { path: pathname, product_id: decodeURIComponent(match[1]) } : { path: pathname }
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const { user } = useAuth()
  const [messages, setMessages] = useState<ChatMessage[]>([greetingFor(null)])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const sendingRef = useRef(false) // Blocks double submits before React re-renders
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const { showResults } = useChatSearch()
  const navigate = useNavigate()
  const location = useLocation()
  const onProductPage = pageContext(location.pathname).product_id !== undefined

  // Put chat search results on the Products page (no page reload). Drop any
  // catalogue filters from the URL so the page shows exactly the chat's results.
  function showOnPage(results: PageResults) {
    showResults(results)
    if (location.pathname !== '/products' || location.search) navigate('/products')
  }

  // Logging in loads that customer's saved chat; logging out clears the panel,
  // so the next person on this browser never sees the previous customer's messages.
  const userId = user?.id
  const firstName = user?.first_name || user?.name.split(' ')[0]
  const userIdRef = useRef(userId)
  useEffect(() => {
    userIdRef.current = userId
    let cancelled = false
    setMessages([greetingFor(userId ? firstName : null)])
    if (userId) {
      fetchChatHistory()
        .then((saved) => {
          if (!cancelled) setMessages([...saved, greetingFor(firstName)])
        })
        .catch(() => {})
    }
    return () => {
      cancelled = true
    }
  }, [userId, firstName])

  // Jump to the bottom when opening; glide to each new message after that.
  const wasOpen = useRef(false)
  useEffect(() => {
    const list = listRef.current
    if (!list) return
    list.scrollTo({ top: list.scrollHeight, behavior: wasOpen.current ? 'smooth' : 'auto' })
    wasOpen.current = open
  }, [messages, sending, open])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  // Other parts of the site ("Chat with Dan", "Ask Dan about sizing") can open the
  // chat and, optionally, ask a question right away.
  const sendRef = useRef<(text: string) => void>(() => {})
  useEffect(() => {
    sendRef.current = (text: string) => void send(text)
  })
  useEffect(
    () =>
      onOpenChat((question) => {
        setOpen(true)
        if (question) setTimeout(() => sendRef.current(question), 0)
      }),
    [],
  )

  async function send(text: string, isRetry = false) {
    if (!text || sendingRef.current) return
    sendingRef.current = true
    // Drop error bubbles; on a retry, also drop the failed copy of the message we're resending.
    let base = messages.filter((m) => !m.retryText)
    const lastMsg = base[base.length - 1]
    if (isRetry && lastMsg?.role === 'user' && lastMsg.content === text) base = base.slice(0, -1)
    // Earlier turns, without the greeting, so the agent can follow along.
    const history = base.filter((m) => !m.greeting)
    setMessages([...base, { role: 'user', content: text }])
    setInput('')
    setSending(true)
    const sentBy = userIdRef.current
    try {
      const reply = await sendChatMessage(text, history, pageContext(location.pathname))
      if (userIdRef.current !== sentBy) return // Logged in/out while waiting: drop the reply.
      setMessages((m) => [...m, reply])
      if (reply.pageResults) showOnPage(reply.pageResults)
    } catch (err) {
      if (userIdRef.current !== sentBy) return
      const reason = err instanceof Error ? err.message : ''
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: `Sorry, I couldn't answer that. ${reason || 'Please try again.'}`,
          retryText: text,
        },
      ])
    } finally {
      sendingRef.current = false
      setSending(false)
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    send(input.trim())
  }

  const hasConversation = messages.some((m) => m.role === 'user')
  const last = messages[messages.length - 1]
  const showSuggestions = !sending && (onProductPage || !hasConversation || last?.greeting)
  const suggestions = onProductPage ? PRODUCT_SUGGESTIONS : GENERAL_SUGGESTIONS

  return (
    <div className={`chat ${open ? 'is-open' : ''}`}>
      {open && (
        <section
          className="chat-panel"
          aria-label="Handsome Dan, Campus Customs shopping assistant"
          onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
        >
          <header className="chat-header">
            <span className="chat-avatar">
              <HandsomeDan size={36} />
            </span>
            <span className="chat-title">
              <strong>Handsome Dan</strong>
              <small>
                <i className="online-dot" aria-hidden="true" /> Campus Customs shopping assistant
              </small>
            </span>
            <button onClick={() => setOpen(false)} aria-label="Close chat">
              ×
            </button>
          </header>

          <div className="chat-messages" ref={listRef} aria-live="polite">
            {messages.map((m, i) => (
              <div key={i} className={`chat-turn ${m.role}`}>
                <div className="chat-row">
                  {m.role === 'assistant' && (
                    <span className="msg-avatar" aria-hidden="true">
                      <HandsomeDan size={26} />
                    </span>
                  )}
                  <div className={`bubble ${m.role} ${m.retryText ? 'error' : ''}`}>
                    <span className="sr-only">{m.role === 'user' ? 'You said: ' : 'Handsome Dan said: '}</span>
                    {m.content}
                  </div>
                </div>
                {m.retryText && (
                  <button className="chat-retry" onClick={() => send(m.retryText!, true)} disabled={sending}>
                    ↻ Try again
                  </button>
                )}
                {m.products && m.products.length > 0 && (
                  <div className="chat-cards">
                    {m.products.map((p) => (
                      <Link key={p.product_id} to={`/products/${p.product_id}`} className="chat-card">
                        <img src={p.image_url} alt="" />
                        <span className="chat-card-name">{p.name}</span>
                        <span className="chat-card-meta">
                          {formatPrice(p.price)}
                          {p.total_stock === 0 && ' · Sold out'}
                        </span>
                      </Link>
                    ))}
                  </div>
                )}
                {m.pageResults && (
                  <button
                    className="chat-see-page"
                    onClick={() => {
                      showOnPage(m.pageResults!)
                      setOpen(false)
                    }}
                  >
                    {m.pageResults.products.length > 0
                      ? `See all ${m.pageResults.products.length} on the page →`
                      : 'See results on the page →'}
                  </button>
                )}
              </div>
            ))}

            {sending && (
              <div className="chat-turn assistant">
                <div className="chat-row">
                  <span className="msg-avatar" aria-hidden="true">
                    <HandsomeDan size={26} />
                  </span>
                  <div className="bubble assistant typing" role="status">
                    <span className="sr-only">Handsome Dan is typing</span>
                    <span className="dot" />
                    <span className="dot" />
                    <span className="dot" />
                  </div>
                </div>
              </div>
            )}

            {showSuggestions && (
              <div className="chat-suggestions" aria-label="Suggested questions">
                {suggestions.map((s) => (
                  <button key={s} onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>

          <form className="chat-input" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={onProductPage ? 'Ask about this item…' : 'Ask about sizes, colors, gifts…'}
              aria-label="Message"
              maxLength={2000}
              enterKeyHint="send"
            />
            <button type="submit" disabled={sending || !input.trim()}>
              {sending ? '…' : 'Send'}
            </button>
          </form>
        </section>
      )}
      <button
        className="chat-toggle"
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? 'Close chat' : 'Ask Handsome Dan, the shopping assistant'}
        aria-expanded={open}
      >
        {open ? (
          '×'
        ) : (
          <>
            <span className="chat-toggle-face" aria-hidden="true">
              <HandsomeDan size={34} />
            </span>
            <span className="chat-toggle-label">Ask Dan</span>
          </>
        )}
      </button>
    </div>
  )
}
