// Original illustration of Handsome Dan, Yale's bulldog mascot.
export default function HandsomeDan({ size = 120 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 200 200"
      role="img"
      aria-label="Handsome Dan, the Yale bulldog"
    >
      {/* Sweater */}
      <path d="M38 200 C40 160 70 145 100 145 C130 145 160 160 162 200 Z" fill="#00356b" />
      <path d="M70 150 Q100 170 130 150 L126 162 Q100 180 74 162 Z" fill="#fff" />
      <text x="100" y="192" textAnchor="middle" fontSize="26" fontWeight="800" fill="#fff" fontFamily="Georgia, serif">Y</text>

      {/* Ears */}
      <path d="M42 62 C28 40 40 28 62 40 L70 60 Z" fill="#8a6a50" />
      <path d="M158 62 C172 40 160 28 138 40 L130 60 Z" fill="#8a6a50" />

      {/* Head */}
      <ellipse cx="100" cy="92" rx="66" ry="58" fill="#f3e6d6" />
      {/* Brindle patches */}
      <path d="M48 70 C55 50 75 42 90 44 C82 56 70 66 52 82 Z" fill="#c9a888" />
      <path d="M150 74 C146 56 128 44 114 44 C120 58 134 66 148 84 Z" fill="#c9a888" />

      {/* Brow wrinkles */}
      <path d="M80 58 Q100 50 120 58" stroke="#b89878" strokeWidth="3" fill="none" strokeLinecap="round" />
      <path d="M86 66 Q100 60 114 66" stroke="#b89878" strokeWidth="3" fill="none" strokeLinecap="round" />

      {/* Eyes */}
      <circle cx="74" cy="84" r="9" fill="#2b2118" />
      <circle cx="126" cy="84" r="9" fill="#2b2118" />
      <circle cx="77" cy="81" r="3" fill="#fff" />
      <circle cx="129" cy="81" r="3" fill="#fff" />

      {/* Jowls */}
      <ellipse cx="78" cy="118" rx="30" ry="22" fill="#fbf4ea" />
      <ellipse cx="122" cy="118" rx="30" ry="22" fill="#fbf4ea" />

      {/* Nose */}
      <ellipse cx="100" cy="102" rx="16" ry="11" fill="#2b2118" />
      <ellipse cx="95" cy="99" rx="4" ry="2.5" fill="#5a4a3c" />

      {/* Underbite with teeth */}
      <path d="M78 128 Q100 144 122 128 Q100 136 78 128 Z" fill="#2b2118" />
      <path d="M84 130 L88 122 L92 132 Z" fill="#fff" />
      <path d="M116 130 L112 122 L108 132 Z" fill="#fff" />
    </svg>
  )
}
