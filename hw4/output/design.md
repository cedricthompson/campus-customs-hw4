# Campus Customs: Design (Problem 10)

## What changed

**Visual system**
- One palette, defined as CSS variables: deep navy (`#0b2545`), Yale blue (`#00356b`), mid blue, white, and cool grays. **Yellow** (`#f2c230`) is used only for highlights: the hero underline, the main call to action, "Few left" badges, the ticker dots, and the active-filter count. **Dark green** is used only for availability ("In stock", the chat's online dot).
- Type: **Barlow Condensed** (bold, uppercase, italic for the brand) for headings, prices, and the wordmark: an athletic jersey feel. **Inter** for body text, for readability.
- Brand mark: a navy shield "CC" monogram with a yellow speed stripe, used in the nav, footer, and browser tab. Nav and footer carry a thin yellow-to-blue "track lane" stripe, and every section label starts with a short yellow dash.

**Storefront pages**
- **Home:** split hero with "Wear your blue. Move like a Bulldog.", a search bar, and a yellow "Shop the collection" button; a scrolling category ticker; "Find your fit" category tiles using real product photos and counts; "Fan favorites"; a "Train like a Bulldog" promo band; and a "Chat with Dan" card.
- **Shop:** navy banner header with the search bar; chip filters with yellow counts on the active chip.
- **Product cards:** category label, price at the bottom, a yellow "Few left" badge (20 or fewer units across all sizes; currently 4 products), a "Sold out" badge that appears only if a product runs out completely (none do today), and a "View details →" bar that slides up on hover.
- **Product page:** large sticky photo, big price with an "In stock" pill, color chips, size pills (sizes with 3 or fewer left are highlighted yellow with "Only 2 left"; sold-out sizes are struck through), and two new buttons, **Ask Dan about sizing** and **Find similar styles**, which open the chat and ask for you.
- **About / Log in / Create account:** banner header; cards with a yellow-and-navy top stripe. New navy footer with shop links and "Boola boola."

**Athletic theme (original illustrations, no stock photos)**
- Hero: a **runner in a Yale track singlet** on curved stadium lanes, with speed lines streaming behind, a bobbing stride, and a pulsing shadow.
- Promo band: a **person in a lunge stretch**, arms overhead, gently breathing.
- Diagonal "speed stripe" textures on the hero, banners, and chat header.

**Motion**
- Pages fade in on navigation; home sections fade up as they scroll into view; product cards and category tiles enter in a quick stagger.
- Hover: buttons lift, cards lift and zoom their photo, nav links get a sprinting yellow underline, and the logo tilts.
- Chat: the "Ask Dan" button pulses a yellow ring 3 times after load; the panel scales open; each message slides in; the close "×" spins.
- All motion turns off for shoppers whose device asks for **reduced motion**.

**Chat**
- Branded header (navy gradient, speed stripes, yellow underline, Dan avatar, green online dot); customer bubbles in a navy-to-blue gradient; Dan's bubbles in white cards; yellow "See all N on the page →" button; rounded input that highlights on focus.

## Why this should keep shoppers longer and help them buy

- **It looks like a real store.** A consistent brand mark, palette, and type tell shoppers the shop is legitimate and cared for, which builds the trust needed to buy apparel online.
- **The path to buying is obvious.** One yellow call to action per screen and a clear heading order (eyebrow → headline → action) show what to do next. Category tiles get shoppers into the right aisle in one tap.
- **Products sell themselves better.** Bigger photos, hover zoom, clear prices, and "Few left" / "Only 2 left" cues make items feel desirable and give a reason to decide now, while sold-out sizes are clearly marked so nobody is disappointed later.
- **Help is one click away.** "Ask Dan about sizing" on every product page and the "Chat with Dan" card answer the most common reason people hesitate (size and fit) without leaving the page.
- **Motion rewards exploring.** Fades, staggers, and the runner make browsing feel lively, so people scroll further and see more products, but it's subtle, fast (under 0.6s), and off for reduced-motion users, so it never slows shopping down.
- **The athletic story matches the products.** The runner and stretch scenes show hoodies, quarter-zips, and fleece as gear you move in, not just souvenirs, which helps shoppers picture wearing them.

## Files

`frontend/index.html` (fonts, title, theme color) · `frontend/public/favicon.svg` · `frontend/src/index.css` (full design system, rewritten) · new `components/BrandMark.tsx`, `components/AthleteArt.tsx` (runner + stretch illustrations), `components/Reveal.tsx` (scroll reveal), `chatEvents.ts` (open chat from any page) · updated `App.tsx` (page fade, footer), `NavBar.tsx`, `ProductCard.tsx`, `ChatWidget.tsx`, `pages/Home.tsx`, `pages/Products.tsx`, `pages/ProductDetail.tsx`, `pages/About.tsx`.
