// Campus Customs monogram: a navy shield badge with an italic "CC" and a yellow speed stripe.
export default function BrandMark({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true" className="brand-mark">
      <path d="M24 2 L44 9 V24 C44 36 35 43 24 46 C13 43 4 36 4 24 V9 Z" fill="#0b2545" stroke="#fff" strokeWidth="2.5" />
      <path d="M9 31 H39" stroke="#f2c230" strokeWidth="3" strokeLinecap="round" />
      <text x="24" y="27" textAnchor="middle" fontFamily="'Barlow Condensed', Arial, sans-serif" fontWeight="800" fontStyle="italic" fontSize="19" fill="#fff">
        CC
      </text>
    </svg>
  )
}
