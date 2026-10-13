// Original silhouette of Yale's Gothic skyline, centered on Harkness Tower.
// Drawn in currentColor so the parent sets its color and opacity.

function Pinnacles({ x, y, w, count, h = 14 }: { x: number; y: number; w: number; count: number; h?: number }) {
  const step = count > 1 ? w / (count - 1) : 0
  return (
    <>
      {Array.from({ length: count }, (_, i) => {
        const cx = x + i * step
        return <path key={i} d={`M${cx - 3} ${y} L${cx} ${y - h} L${cx + 3} ${y} Z`} />
      })}
    </>
  )
}

function Battlement({ x, y, w, n = 8 }: { x: number; y: number; w: number; n?: number }) {
  const step = w / n
  return (
    <>
      {Array.from({ length: n }, (_, i) =>
        i % 2 === 0 ? <rect key={i} x={x + i * step} y={y - 6} width={step} height={6} /> : null,
      )}
    </>
  )
}

export default function CampusSkyline({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 1200 320"
      preserveAspectRatio="xMidYMax slice"
      aria-hidden="true"
      fill="currentColor"
    >
      {/* Far layer: rooftops and gables */}
      <g opacity="0.55">
        <path d="M0 320 V250 L40 225 L80 250 V235 H150 L185 205 L220 235 V250 H260 V320 Z" />
        <path d="M900 320 V240 L935 215 L970 240 V228 H1040 L1075 198 L1110 228 V245 H1200 V320 Z" />
        <rect x="300" y="245" width="120" height="75" />
        <path d="M300 245 L360 215 L420 245 Z" />
        <rect x="760" y="240" width="110" height="80" />
        <path d="M760 240 L815 210 L870 240 Z" />
      </g>

      {/* Left: library-style hall with a squat tower */}
      <rect x="120" y="230" width="220" height="90" />
      <Battlement x={120} y={230} w={220} n={16} />
      <rect x="205" y="160" width="50" height="70" />
      <Battlement x={205} y={160} w={50} n={6} />
      <Pinnacles x={207} y={154} w={46} count={4} h={16} />

      {/* Harkness Tower */}
      <g>
        {/* Base block */}
        <rect x="545" y="170" width="110" height="150" />
        <Battlement x={545} y={170} w={110} n={10} />
        {/* Second stage */}
        <rect x="560" y="105" width="80" height="65" />
        <Pinnacles x={560} y={105} w={80} count={5} h={18} />
        {/* Belfry */}
        <rect x="572" y="55" width="56" height="50" />
        <Pinnacles x={572} y={55} w={56} count={4} h={20} />
        {/* Upper lantern */}
        <rect x="584" y="18" width="32" height="37" />
        <Pinnacles x={584} y={18} w={32} count={3} h={16} />
        <path d="M594 18 L600 -2 L606 18 Z" />
        {/* Corner buttresses */}
        <rect x="538" y="190" width="10" height="130" />
        <rect x="652" y="190" width="10" height="130" />
        <path d="M538 190 L543 172 L548 190 Z" />
        <path d="M652 190 L657 172 L662 190 Z" />
      </g>

      {/* Long college ranges either side of the tower */}
      <rect x="340" y="250" width="205" height="70" />
      <Battlement x={340} y={250} w={205} n={14} />
      <rect x="655" y="245" width="215" height="75" />
      <Battlement x={655} y={245} w={215} n={14} />
      {/* Gables on the ranges */}
      <path d="M400 250 L425 222 L450 250 Z" />
      <path d="M720 245 L745 216 L770 245 Z" />
      <path d="M800 245 L825 220 L850 245 Z" />

      {/* Right: chapel with a slender spire */}
      <rect x="880" y="225" width="150" height="95" />
      <path d="M880 225 L955 185 L1030 225 Z" />
      <rect x="1040" y="175" width="34" height="145" />
      <path d="M1040 175 L1057 110 L1074 175 Z" />
      <rect x="1030" y="250" width="170" height="70" />
      <Battlement x={1030} y={250} w={170} n={12} />

      {/* Trees along the street */}
      <g>
        <circle cx="40" cy="285" r="28" />
        <circle cx="75" cy="292" r="22" />
        <circle cx="470" cy="290" r="24" />
        <circle cx="500" cy="296" r="18" />
        <circle cx="700" cy="292" r="22" />
        <circle cx="1120" cy="288" r="26" />
        <circle cx="1160" cy="294" r="20" />
      </g>

      {/* Ground */}
      <rect x="0" y="305" width="1200" height="15" />
    </svg>
  )
}
