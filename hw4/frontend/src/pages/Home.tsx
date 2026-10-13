import { useEffect, useMemo, useState, type CSSProperties, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { fetchProducts, type Product } from '../api'
import { openChat } from '../chatEvents'
import { useChatSearch } from '../chatSearch'
import { RunnerScene, StretchFigure } from '../components/AthleteArt'
import CampusSkyline from '../components/CampusSkyline'
import HandsomeDan from '../components/HandsomeDan'
import ProductCard from '../components/ProductCard'
import Reveal from '../components/Reveal'

const CATEGORY_ORDER = ['Hoodies', 'Crewnecks & sweatshirts', 'T-shirts', 'Quarter-zips', 'Jackets & fleece']
const TICKER = ['Hoodies', 'Crewnecks', 'Tees', 'Quarter-zips', 'Fleece jackets', 'Residential colleges', 'Varsity sports', 'Game day']

export default function Home() {
  const [products, setProducts] = useState<Product[]>([])
  const [query, setQuery] = useState('')
  const navigate = useNavigate()
  const { clearResults } = useChatSearch()

  // A typed search means the shopper wants the catalogue, not earlier chat results.
  function search(e: FormEvent) {
    e.preventDefault()
    clearResults()
    const q = query.trim()
    navigate(q ? `/products?q=${encodeURIComponent(q)}` : '/products')
  }

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch(() => setProducts([]))
  }, [])

  const featured = useMemo(() => products.filter((p) => p.total_stock > 0).slice(0, 4), [products])

  // One tile per category, with its real product count and a real product photo.
  const categories = useMemo(
    () =>
      CATEGORY_ORDER.map((name) => {
        const items = products.filter((p) => p.category === name)
        return { name, count: items.length, image: items.find((p) => p.total_stock > 0)?.image_url }
      }).filter((c) => c.count > 0),
    [products],
  )

  return (
    <>
      <section className="hero">
        <CampusSkyline className="hero-skyline" />
        <div className="hero-copy">
          <p className="eyebrow">57 Broadway · New Haven, CT</p>
          <h1>
            Wear your blue. <span className="hero-accent">Move like a Bulldog.</span>
          </h1>
          <p className="hero-lede">
            Campus Customs is your hometown shop for Yale gear: soft crewnecks, everyday tees,
            cozy hoodies, and quarter-zips built for crisp fall mornings on Old Campus, early runs
            along the Green, and every game day in between.
          </p>
          <form className="search-bar hero-search" role="search" onSubmit={search}>
            <svg viewBox="0 0 24 24" aria-hidden="true" className="search-icon">
              <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
              <path d="M16.5 16.5 L21 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search hoodies, colleges, colors…"
              aria-label="Search products"
            />
            <button type="submit" className="search-go">
              Search
            </button>
          </form>
          <div className="hero-actions">
            <Link to="/products" className="button accent">
              Shop the collection
            </Link>
            <Link to="/about" className="button ghost">
              Our story
            </Link>
          </div>
        </div>
        <div className="hero-art">
          <RunnerScene />
        </div>
      </section>

      <div className="ticker" aria-hidden="true">
        <div className="ticker-track">
          {[...TICKER, ...TICKER].map((t, i) => (
            <span key={i}>
              {t}
              <i className="ticker-dot" />
            </span>
          ))}
        </div>
      </div>

      {categories.length > 0 && (
        <Reveal>
          <section className="home-section">
            <div className="section-head">
              <div>
                <p className="eyebrow">Shop by category</p>
                <h2>Find your fit</h2>
              </div>
              <Link to="/products" className="text-link">
                All products →
              </Link>
            </div>
            <div className="category-tiles">
              {categories.map((c, i) => (
                <Link
                  key={c.name}
                  to={`/products?cat=${encodeURIComponent(c.name)}`}
                  className="category-tile"
                  style={{ '--i': i } as CSSProperties}
                  onClick={clearResults}
                >
                  {c.image && <img src={c.image} alt="" loading="lazy" />}
                  <span className="category-tile-label">
                    <strong>{c.name}</strong>
                    <small>{c.count} styles</small>
                  </span>
                </Link>
              ))}
            </div>
          </section>
        </Reveal>
      )}

      {featured.length > 0 && (
        <Reveal>
          <section className="home-section">
            <div className="section-head">
              <div>
                <p className="eyebrow">In stock now</p>
                <h2>Fan favorites</h2>
              </div>
              <Link to="/products" className="text-link">
                See everything →
              </Link>
            </div>
            <div className="grid">
              {featured.map((p, i) => (
                <ProductCard key={p.product_id} product={p} index={i} />
              ))}
            </div>
          </section>
        </Reveal>
      )}

      <Reveal>
        <section className="promo-band">
          <div className="promo-art">
            <StretchFigure />
          </div>
          <div className="promo-copy">
            <p className="eyebrow">Warm up in Yale blue</p>
            <h2>Train like a Bulldog</h2>
            <p>
              Hoodies for the warm-up, quarter-zips for the cool-down, and fleece for the walk home.
              Layers made for moving around campus.
            </p>
            <div className="hero-actions">
              <Link to="/products?cat=Hoodies" className="button" onClick={clearResults}>
                Shop hoodies
              </Link>
              <Link to="/products?cat=Quarter-zips" className="button secondary" onClick={clearResults}>
                Shop quarter-zips
              </Link>
            </div>
          </div>
        </section>
      </Reveal>

      <Reveal>
        <section className="highlights">
          <div>
            <span className="highlight-icon" aria-hidden="true">
              ★
            </span>
            <h3>For the whole Yale family</h3>
            <p>Students, alumni, parents, grandparents, and the youngest Bulldog fans.</p>
          </div>
          <div>
            <span className="highlight-icon" aria-hidden="true">
              ⚑
            </span>
            <h3>Rep your college</h3>
            <p>Residential college, varsity team, and graduate school designs all in one place.</p>
          </div>
          <div className="dan-card">
            <HandsomeDan size={88} />
            <div>
              <h3>Ask Handsome Dan</h3>
              <p>Not sure about a size, color, or gift? Yale's favorite bulldog will help you find it.</p>
              <button className="button small" onClick={() => openChat()}>
                Chat with Dan
              </button>
            </div>
          </div>
        </section>
      </Reveal>
    </>
  )
}
