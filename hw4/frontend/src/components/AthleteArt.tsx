// Original athletic illustrations for the storefront. Flat shapes in the brand
// palette; motion is CSS (see .runner-*, .stretch-* in index.css) and turns off
// for shoppers who prefer reduced motion.

const SKIN = '#e6b591'
const HAIR = '#2b2118'
const NAVY = '#0b2545'
const BLUE = '#1f5fae'
const YELLOW = '#f2c230'
const WHITE = '#ffffff'

/** A runner in a Yale track singlet mid-stride on stadium lanes. */
export function RunnerScene() {
  return (
    <svg className="runner-scene" viewBox="0 0 440 360" role="img" aria-label="Illustration of a runner in a Yale track outfit">
      {/* Track lanes curving away */}
      <g className="runner-track">
        <path d="M-20 300 Q220 250 460 300 L460 360 L-20 360 Z" fill="rgba(255,255,255,0.10)" />
        <path d="M-20 300 Q220 250 460 300" stroke="rgba(255,255,255,0.55)" strokeWidth="3" fill="none" />
        <path d="M-20 325 Q220 280 460 325" stroke="rgba(255,255,255,0.35)" strokeWidth="2.5" fill="none" />
        <path d="M-20 350 Q220 310 460 350" stroke="rgba(255,255,255,0.22)" strokeWidth="2" fill="none" />
      </g>

      {/* Speed lines trailing the runner */}
      <g className="runner-speed" stroke={WHITE} strokeLinecap="round">
        <line x1="40" y1="140" x2="140" y2="140" strokeWidth="5" opacity="0.55" />
        <line x1="70" y1="170" x2="150" y2="170" strokeWidth="4" opacity="0.4" />
        <line x1="20" y1="200" x2="125" y2="200" strokeWidth="5" opacity="0.5" />
        <line x1="60" y1="230" x2="140" y2="230" strokeWidth="3" opacity="0.35" />
      </g>

      {/* Shadow */}
      <ellipse className="runner-shadow" cx="240" cy="292" rx="70" ry="8" fill="rgba(0,0,0,0.22)" />

      <g className="runner-body" strokeLinecap="round" strokeLinejoin="round">
        {/* Back arm */}
        <path d="M236 112 L200 132 L186 162" stroke={SKIN} strokeWidth="15" fill="none" />
        {/* Back leg, kicked up behind */}
        <path d="M222 190 L188 230 L146 236" stroke={SKIN} strokeWidth="18" fill="none" />
        <path d="M150 226 L128 238 L142 248 Z" fill={YELLOW} stroke={NAVY} strokeWidth="3" />

        {/* Shorts */}
        <path d="M205 172 L246 176 L250 204 L226 212 L208 200 Z" fill={WHITE} stroke={NAVY} strokeWidth="3" />
        <path d="M212 198 L246 202" stroke={BLUE} strokeWidth="4" />

        {/* Front leg, reaching forward */}
        <path d="M236 196 L282 222 L274 278" stroke={SKIN} strokeWidth="18" fill="none" />
        <path d="M264 272 L300 274 L298 286 L262 286 Z" fill={YELLOW} stroke={NAVY} strokeWidth="3" />

        {/* Singlet, leaning forward */}
        <path d="M232 98 L262 104 L252 178 L204 176 L214 112 Z" fill={NAVY} />
        <path d="M214 112 L204 176" stroke={YELLOW} strokeWidth="4" />
        <path d="M262 104 L252 178" stroke={YELLOW} strokeWidth="4" />
        <text x="234" y="152" textAnchor="middle" fontFamily="'Barlow Condensed', Arial, sans-serif" fontWeight="800" fontStyle="italic" fontSize="30" fill={WHITE}>
          Y
        </text>

        {/* Front arm, driving forward */}
        <path d="M252 112 L288 138 L310 112" stroke={SKIN} strokeWidth="15" fill="none" />

        {/* Head and neck */}
        <path d="M246 98 L250 84" stroke={SKIN} strokeWidth="13" />
        <circle cx="258" cy="68" r="21" fill={SKIN} />
        <path d="M238 66 C238 46 270 42 280 58 C270 54 258 56 252 62 C248 60 242 62 238 66 Z" fill={HAIR} />
        <path d="M240 60 C250 50 268 50 280 58" stroke={YELLOW} strokeWidth="5" fill="none" />
      </g>
    </svg>
  )
}

/** Someone in a deep lunge stretch, arms overhead: warming up before a run. */
export function StretchFigure() {
  return (
    <svg className="stretch-figure" viewBox="0 0 240 230" role="img" aria-label="Illustration of a person stretching before a run">
      <ellipse cx="118" cy="214" rx="86" ry="7" fill="rgba(11,37,69,0.12)" />
      <g className="stretch-body" strokeLinecap="round" strokeLinejoin="round">
        {/* Back leg, long lunge */}
        <path d="M112 128 L70 170 L30 206" stroke={SKIN} strokeWidth="16" fill="none" />
        <path d="M34 198 L14 210 L30 214 Z" fill={WHITE} stroke={NAVY} strokeWidth="3" />
        {/* Front leg, bent knee */}
        <path d="M118 130 L168 154 L166 204" stroke={SKIN} strokeWidth="16" fill="none" />
        <path d="M156 200 L190 202 L190 212 L156 212 Z" fill={WHITE} stroke={NAVY} strokeWidth="3" />
        {/* Joggers */}
        <path d="M100 116 L134 118 L140 140 L112 146 L98 134 Z" fill={'#5b6577'} />
        {/* Hoodie */}
        <path d="M100 62 L134 64 L136 122 L98 120 Z" fill={BLUE} />
        <path d="M104 96 L130 97" stroke={WHITE} strokeWidth="3" opacity="0.8" />
        {/* Arms reaching overhead */}
        <path d="M104 70 L92 34 L100 6" stroke={SKIN} strokeWidth="13" fill="none" />
        <path d="M130 70 L136 34 L124 6" stroke={SKIN} strokeWidth="13" fill="none" />
        <path d="M95 64 L92 46" stroke={BLUE} strokeWidth="15" />
        <path d="M133 66 L136 46" stroke={BLUE} strokeWidth="15" />
        {/* Head */}
        <circle cx="117" cy="48" r="16" fill={SKIN} />
        <path d="M101 46 C101 30 133 28 134 44 C126 38 110 38 101 46 Z" fill={HAIR} />
      </g>
    </svg>
  )
}
