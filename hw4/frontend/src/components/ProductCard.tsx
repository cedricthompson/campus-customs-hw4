import type { CSSProperties } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { formatPrice, type Product } from '../api'

function shortDescription(text: string, max = 90): string {
  if (text.length <= max) return text
  return text.slice(0, text.lastIndexOf(' ', max)) + '…'
}

const FEW_LEFT = 20 // At or below this many across all sizes, show "Few left"

type CardProduct = Pick<
  Product,
  'product_id' | 'name' | 'price' | 'description' | 'image_url' | 'total_stock'
> & { category?: string }

export default function ProductCard({ product, index = 0 }: { product: CardProduct; index?: number }) {
  const location = useLocation()
  const soldOut = product.total_stock === 0
  const fewLeft = !soldOut && product.total_stock <= FEW_LEFT
  return (
    // Remember the listing (with its filters) so the detail page can link back to it.
    <Link
      to={`/products/${product.product_id}`}
      state={{ from: location.pathname + location.search }}
      className={`card ${soldOut ? 'is-sold-out' : ''}`}
      // Stagger the entrance animation, capped so long lists don't wait.
      style={{ '--i': Math.min(index, 11) } as CSSProperties}
    >
      <div className="card-image">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {soldOut && <span className="badge badge-muted">Sold out</span>}
        {fewLeft && <span className="badge badge-hot">Few left</span>}
        <span className="card-cta" aria-hidden="true">
          View details →
        </span>
      </div>
      <div className="card-body">
        {product.category && <p className="card-category">{product.category}</p>}
        <h3>{product.name}</h3>
        <p className="muted card-desc">{shortDescription(product.description)}</p>
        <p className="price">{formatPrice(product.price)}</p>
      </div>
    </Link>
  )
}
