import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { fetchProduct, formatPrice, type Product } from '../api'
import { openChat } from '../chatEvents'
import { useChatSearch } from '../chatSearch'

export default function ProductDetail() {
  const { productId } = useParams()
  const location = useLocation()
  // Back goes to the listing the shopper came from (with their search and filters).
  const from = (location.state as { from?: string } | null)?.from
  const backTo = from?.startsWith('/products') ? from : '/products'
  const { clearResults } = useChatSearch()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!productId) return
    setProduct(null)
    setError(null)
    fetchProduct(productId)
      .then(setProduct)
      .catch(() => setError('We couldn’t find that product.'))
  }, [productId])

  if (error) {
    return (
      <>
        <p className="error">{error}</p>
        <Link to={backTo}>← Back to products</Link>
      </>
    )
  }
  if (!product) return <p className="muted">Loading…</p>

  return (
    <>
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link to={backTo}>← Back to products</Link>
        <span className="crumbs">
          {/* Breadcrumbs open the catalogue, so they also clear any chat results. */}
          <Link to="/products" onClick={clearResults}>
            Products
          </Link>
          <span aria-hidden="true">›</span>
          <Link to={`/products?cat=${encodeURIComponent(product.category)}`} onClick={clearResults}>
            {product.category}
          </Link>
          <span aria-hidden="true">›</span>
          <span aria-current="page">{product.name}</span>
        </span>
      </nav>
      <div className="detail">
        <div className="detail-image">
          <img src={product.image_url} alt={product.name} />
        </div>
        <div className="detail-info">
          <p className="eyebrow">{product.category}</p>
          <h1>{product.name}</h1>
          <div className="detail-price-row">
            <p className="detail-price">{formatPrice(product.price)}</p>
            {product.total_stock > 0 ? (
              <span className="stock-pill in">In stock</span>
            ) : (
              <span className="stock-pill out">Sold out</span>
            )}
          </div>
          <p className="detail-desc">{product.description}</p>

          {product.colors.length > 0 && (
            <div className="detail-colors">
              <span className="detail-label">Colors</span>
              <ul>
                {product.colors.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          )}

          {product.inventory && (
            <div className="detail-sizes">
              <span className="detail-label">Sizes &amp; stock</span>
              <ul className="sizes">
                {product.inventory.map((s) => (
                  <li key={s.size} className={s.quantity === 0 ? 'sold-out' : s.quantity <= 3 ? 'low' : ''}>
                    <span className="size">{s.size}</span>
                    <span className="qty">
                      {s.quantity === 0 ? 'Sold out' : s.quantity <= 3 ? `Only ${s.quantity} left` : `${s.quantity} left`}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="detail-actions">
            <button className="button" onClick={() => openChat(`Can you help me pick a size for the ${product.name}?`)}>
              Ask Dan about sizing
            </button>
            <button className="button secondary" onClick={() => openChat('Show me similar items')}>
              Find similar styles
            </button>
          </div>
          <p className="detail-note muted">Available at Campus Customs, 57 Broadway, New Haven.</p>
        </div>
      </div>
    </>
  )
}
