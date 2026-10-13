// Lets any page open Handsome Dan's chat, optionally asking a question right away.
const EVENT = 'cc:open-chat'

export function openChat(question?: string) {
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { question } }))
}

export function onOpenChat(handler: (question?: string) => void): () => void {
  const listener = (e: Event) => handler((e as CustomEvent<{ question?: string }>).detail?.question)
  window.addEventListener(EVENT, listener)
  return () => window.removeEventListener(EVENT, listener)
}
