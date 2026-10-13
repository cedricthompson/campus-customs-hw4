export type SizeStock = {
  size: string
  quantity: number
}

export type Product = {
  product_id: string
  name: string
  category: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_url: string
  price: number
  total_stock: number
  inventory?: SizeStock[]
}

const NETWORK_ERROR = 'We can’t reach Campus Customs right now. Check your connection and try again.'
const SERVER_ERROR = 'Something went wrong on our end. Please try again.'

// Words that mean a message is for developers, not shoppers.
const TECHNICAL = /traceback|exception|error:|errno|sqlite|\.py\b|line \d|stack|undefined|null|\{|\}/i

// Only show the server's message if it's a short, plain sentence meant for shoppers.
function friendlyMessage(data: unknown, status: number): string {
  const detail = (data as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string' && detail.length < 200 && !TECHNICAL.test(detail)) return detail
  return status >= 500 ? SERVER_ERROR : 'Please check your input and try again.'
}

async function request(url: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init)
  } catch {
    throw new Error(NETWORK_ERROR)
  }
}

async function getJson<T>(url: string): Promise<T> {
  const res = await request(url)
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new Error(friendlyMessage(data, res.status))
  return data as T
}

export function fetchProducts(): Promise<Product[]> {
  return getJson<Product[]>('/api/products')
}

export function fetchProduct(productId: string): Promise<Product> {
  return getJson<Product>(`/api/products/${encodeURIComponent(productId)}`)
}

export type User = {
  id: number
  email: string
  name: string
  first_name: string | null
  last_name: string | null
}

async function postJson<T>(url: string, body?: unknown): Promise<T> {
  const res = await request(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new Error(friendlyMessage(data, res.status))
  return data as T
}

export function fetchCurrentUser(): Promise<User | null> {
  return getJson<User | null>('/api/auth/me')
}

export function login(email: string, password: string): Promise<User> {
  return postJson<User>('/api/auth/login', { email, password })
}

export function signup(fields: {
  first_name: string
  last_name: string
  email: string
  password: string
}): Promise<User> {
  return postJson<User>('/api/auth/signup', fields)
}

export function logout(): Promise<void> {
  return postJson('/api/auth/logout')
}

export function formatPrice(price: number): string {
  return `$${price.toFixed(2)}`
}

export type ChatProductCard = {
  product_id: string
  name: string
  price: number
  image_url: string
  total_stock: number
}

// A chat search's results for the Products page. Same card fields as Product.
export type PageResults = {
  label: string
  query: string
  products: Pick<
    Product,
    | 'product_id'
    | 'name'
    | 'category'
    | 'garment_type'
    | 'description'
    | 'colors'
    | 'price'
    | 'image_url'
    | 'total_stock'
  >[]
}

export type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  products?: ChatProductCard[]
  pageResults?: PageResults
  greeting?: boolean // Local welcome message, never sent to the server
  retryText?: string // Set on a local error bubble: the message to send again
}

type ChatReply = {
  reply: string
  products: ChatProductCard[]
  page_results: PageResults | null
}

// Where the shopper is. The server looks up the product's real details from the id.
export type PageContext = {
  path: string
  product_id?: string
}

// How many earlier messages to send so the agent can follow the conversation.
// Only used for guests; logged-in history is loaded from the database on the server.
const HISTORY_LIMIT = 12

export async function sendChatMessage(
  message: string,
  history: ChatMessage[],
  page: PageContext,
): Promise<ChatMessage> {
  const data = await postJson<ChatReply>('/api/chat', {
    message,
    history: history.slice(-HISTORY_LIMIT).map(({ role, content }) => ({ role, content })),
    page,
  })
  return {
    role: 'assistant',
    content: data.reply,
    products: data.products,
    pageResults: data.page_results ?? undefined,
  }
}

type SavedChatMessage = {
  role: 'user' | 'assistant'
  content: string
  products: ChatProductCard[]
  created_at: string
}

// The logged-in customer's saved chat (the server decides whose from the login cookie).
export async function fetchChatHistory(): Promise<ChatMessage[]> {
  const saved = await getJson<SavedChatMessage[]>('/api/chat/history')
  return saved.map(({ role, content, products }) => ({ role, content, products }))
}
