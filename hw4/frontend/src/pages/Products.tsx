import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchProducts, type Product } from '../api'
import { useChatSearch } from '../chatSearch'
import ProductCard from '../components/ProductCard'

type SortKey = 'featured' | 'price_low' | 'price_high' | 'name'

const SORT_LABELS: Record<SortKey, string> = {
  featured: 'Featured',
  price_low: 'Price: low to high',
  price_high: 'Price: high to low',
  name: 'Name: A to Z',
}

// Order categories the way shoppers think about them, then anything else.
const CATEGORY_ORDER = [
  'Hoodies',
  'Crewnecks & sweatshirts',
  'T-shirts',
  'Quarter-zips',
  'Jackets & fleece',
  'Long-sleeve shirts',
]

const SPELLINGS: Record<string, string> = { grey: 'gray', tee: 't-shirt', tees: 't-shirt', tshirt: 't-shirt' }

function searchText(p: Product): string {
  return [p.name, p.category, p.garment_type, p.description, ...p.colors, ...p.search_tags]
    .join(' ')
    .toLowerCase()
}

function matches(p: Product, query: string): boolean {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  const text = searchText(p)
  return words.every((w) => text.includes(SPELLINGS[w] ?? w.replace(/s$/, '')))
}

export default function Products() {
  const [products, setProducts] = useState<Product[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { results, clearResults } = useChatSearch()

  // Filters live in the URL, so Back from a product page returns to the same view.
  const [params, setParams] = useSearchParams()
  const query = params.get('q') ?? ''
  const category = params.get('cat') ?? ''
  const sort = (params.get('sort') as SortKey) || 'featured'
  const inStockOnly = params.get('instock') === '1'

  // Build on the live address bar, which the router updates immediately, so quick
  // changes (pick a category, then a sort) don't overwrite each other.
  function update(changes: Record<string, string | null>) {
    const next = new URLSearchParams(window.location.search)
    for (const [k, v] of Object.entries(changes)) {
      if (v) next.set(k, v)
      else next.delete(k)
    }
    setParams(next, { replace: true })
  }

  function load() {
    setError(null)
    fetchProducts()
      .then(setProducts)
      .catch(() => setError('We couldn’t load products right now.'))
  }
  useEffect(load, [])


  const categories = useMemo(() => {
    const counts = new Map<string, number>()
    for (const p of products ?? []) counts.set(p.category, (counts.get(p.category) ?? 0) + 1)
    return [...counts.entries()].sort(
      (a, b) => (CATEGORY_ORDER.indexOf(a[0]) + 1 || 99) - (CATEGORY_ORDER.indexOf(b[0]) + 1 || 99),
    )
  }, [products])

  const visible = useMemo(() => {
    let list = (products ?? []).filter(
      (p) =>
        (!category || p.category === category) &&
        (!inStockOnly || p.total_stock > 0) &&
        (!query.trim() || matches(p, query)),
    )
    list = [...list]
    if (sort === 'price_low') list.sort((a, b) => a.price - b.price || a.name.localeCompare(b.name))
    else if (sort === 'price_high') list.sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))
    else if (sort === 'name') list.sort((a, b) => a.name.localeCompare(b.name))
    else list.sort((a, b) => Number(b.total_stock > 0) - Number(a.total_stock > 0)) // in stock first
    return list
  }, [products, category, inStockOnly, query, sort])

  const filtersActive = Boolean(query || category || inStockOnly)

  // Results from a chat search replace the catalogue view until cleared.
  if (results) {
    return (
      <>
        <div className="chat-results-head">
          <div>
            <p className="eyebrow">Results from chat</p>
            <h1>{results.label}</h1>
            <p className="muted">
              {results.products.length} {results.products.length === 1 ? 'item' : 'items'} for “
              {results.query}”
            </p>
          </div>
          <button className="button secondary" onClick={clearResults}>
            Show all products
          </button>
        </div>
        {results.products.length > 0 ? (
          <div className="grid">
            {results.products.map((p, i) => (
              <ProductCard key={p.product_id} product={p} index={i} />
            ))}
          </div>
        ) : (
          <div className="empty-results">
            <h2>No matches</h2>
            <p className="muted">
              We don’t carry anything matching that right now. Try asking the assistant about
              hoodies, crewnecks, T-shirts, or quarter-zips, or browse everything.
            </p>
            <button className="button" onClick={clearResults}>
              Browse all products
            </button>
          </div>
        )}
      </>
    )
  }

  return (
    <>
      <div className="shop-head">
        <div>
          <p className="eyebrow">Campus Customs shop</p>
          <h1>Shop Yale gear</h1>
        </div>
        <form className="search-bar" role="search" onSubmit={(e) => e.preventDefault()}>
          <svg viewBox="0 0 24 24" aria-hidden="true" className="search-icon">
            <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
            <path d="M16.5 16.5 L21 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <input
            type="search"
            value={query}
            onChange={(e) => update({ q: e.target.value || null })}
            placeholder="Search hoodies, colleges, colors…"
            aria-label="Search products"
          />
          {query && (
            <button type="button" className="search-clear" onClick={() => update({ q: null })} aria-label="Clear search">
              ×
            </button>
          )}
        </form>
      </div>

      <div className="filters" role="group" aria-label="Filter by category">
        <button
          className={`chip ${!category ? 'active' : ''}`}
          aria-pressed={!category}
          onClick={() => update({ cat: null })}
        >
          All {products && <span className="chip-count">{products.length}</span>}
        </button>
        {categories.map(([name, count]) => (
          <button
            key={name}
            className={`chip ${category === name ? 'active' : ''}`}
            aria-pressed={category === name}
            onClick={() => update({ cat: category === name ? null : name })}
          >
            {name} <span className="chip-count">{count}</span>
          </button>
        ))}
      </div>

      <div className="toolbar">
        <p className="muted" aria-live="polite">
          {products ? `Showing ${visible.length} of ${products.length} products` : ''}
        </p>
        <div className="toolbar-controls">
          <label className="check">
            <input
              type="checkbox"
              checked={inStockOnly}
              onChange={(e) => update({ instock: e.target.checked ? '1' : null })}
            />
            In stock only
          </label>
          <label className="sort">
            Sort by
            <select value={sort} onChange={(e) => update({ sort: e.target.value === 'featured' ? null : e.target.value })}>
              {(Object.keys(SORT_LABELS) as SortKey[]).map((k) => (
                <option key={k} value={k}>
                  {SORT_LABELS[k]}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {error && (
        <div className="empty-results">
          <h2>Products didn’t load</h2>
          <p className="muted">{error}</p>
          <button className="button" onClick={load}>
            Try again
          </button>
        </div>
      )}
      {!products && !error && <p className="muted">Loading products…</p>}

      {products && visible.length > 0 && (
        <div className="grid">
          {visible.map((p, i) => (
            <ProductCard key={p.product_id} product={p} index={i} />
          ))}
        </div>
      )}

      {products && visible.length === 0 && (
        <div className="empty-results">
          <h2>No products match{query ? ` “${query}”` : ''}</h2>
          <p className="muted">
            {category ? `Nothing in ${category} matches. ` : ''}Try a different word, like “hoodie”,
            “navy”, or a college name, or ask Handsome Dan in the chat.
          </p>
          <div className="empty-actions">
            {category && query && (
              <button className="button secondary" onClick={() => update({ cat: null })}>
                Search all categories
              </button>
            )}
            {filtersActive && (
              <button className="button" onClick={() => update({ q: null, cat: null, instock: null })}>
                Clear filters
              </button>
            )}
          </div>
        </div>
      )}
    </>
  )
}
