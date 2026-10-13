# Campus Customs: Usability Improvements (Problem 9)

Four improvements: two front-end, two agent/backend. Everything below was built on the existing Problem 3, 7, and 8 code and verified in the running app (backend `uvicorn main:app --reload --port 8000` from `backend/`, site at http://localhost:5180).

**Starting point (reviewed before changes).** The Products page showed all 102 products in one grid with no search, filters, or sorting. The chat was a plain blue "Chat" button with a one-line greeting and a "Typing…" label; a failed request just printed the error text. The agent matched colors word for word ("blue" missed navy, royal blue, light blue), had no price sorting, size filter, or "other colors" lookup, and returned nothing helpful on zero matches. The backend accepted whitespace-only messages, showed Pydantic's raw error list on bad input, had no guard against duplicate or overlapping sends, sent up to 20 full messages of history, never closed its SQLite connections, and `chat_messages` had no index.

---

## 1. Enhanced Product Discovery and Shopping Experience

**Category:** Front-end

### What was implemented

- **Prominent search bar** at the top of the Products page (rounded, with a search icon and a clear "×" button), plus a second search box in the Home page banner that opens Products with the results. Search matches every word against the name, category, garment type, description, colors, and tags, and understands shopper spellings: "grey" = "gray", "tee"/"tees" = T-shirt, plural words ("hoodies").
- **Category filters from the real catalogue.** The catalogue has 22 different `garment_type` spellings; they are grouped into the 6 categories shoppers actually use: Hoodies (27), Crewnecks & sweatshirts (29), T-shirts (25), Quarter-zips (11), Jackets & fleece (8), Long-sleeve shirts (2). Every product falls into one (checked by an automated test). The categories are computed once in the backend (`db.category_for`) and sent with each product, so the website filters and the AI agent use the same groups. Shown as chips with live counts; "All" resets.
- **Sorting:** Featured (in-stock first), Price low → high, Price high → low, Name A → Z. Plus an **In stock only** checkbox.
- **Clearer product cards:** a category label above the name, image, name, price, short description, and a red "Sold out" tag when nothing is left.
- **Responsive grid:** 4 columns at desktop width (1280px), 3 on tablet (768px), 2 compact columns on phones (description hidden so image, name, and price stay readable). On phones the nav bar now fits in two short rows (brand + Log in/Create account, then Home/Products/About) instead of a tall stack that pushed products off the first screen.
- **Helpful no-match messages:** "No products match 'grey tee'", with a tip ("Try 'hoodie', 'navy', or a college name, or ask Handsome Dan") and buttons: **Search all categories** (when a category is limited) and **Clear filters**. A "Products didn't load" message has a **Try again** button.
- **Clear navigation to and from product pages:** search, category, sort, and in-stock are kept in the URL (`/products?cat=Hoodies&sort=price_high&q=navy`), so filtered views can be bookmarked and shared. The detail page has breadcrumbs (**Products › T-shirts › 2025 Yale Vs Harvard T Shirt**, where the category links to that filtered list) and a **← Back to products** link that returns to the exact filtered list the shopper came from.

### Why it helps

Shoppers can go from 102 items to the handful they want in one or two clicks (for example "Hoodies, price low to high, in stock"), compare prices quickly, and never lose their place when they open a product and come back. Phone shoppers see products immediately instead of a screen of navigation. Less hunting means less frustration and a better chance of a purchase.

### Files changed

| File | Change |
|---|---|
| `frontend/src/pages/Products.tsx` | Search bar, category chips with counts, sort, in-stock filter, URL-based filters, empty and error states (chat results view from Problem 7 kept) |
| `frontend/src/pages/ProductDetail.tsx` | Breadcrumbs; Back link returns to the filtered list; category label |
| `frontend/src/components/ProductCard.tsx` | Category label; passes the current list URL to the detail page |
| `frontend/src/pages/Home.tsx` | Search box in the banner |
| `frontend/src/api.ts` | `category` on products |
| `frontend/src/index.css` | Search bar, chips, toolbar, breadcrumbs, responsive grid, compact phone nav |
| `backend/db.py`, `backend/main.py` | `CATEGORIES` + `category_for()`; `category` on `/api/products` and `/api/products/{id}`; `GET /api/categories` |

### How it was tested

| Test | Result |
|---|---|
| Hoodies chip → Price high to low → In stock only | URL `?cat=Hoodies&sort=price_high&instock=1`; "Showing 27 of 102"; all cards Hoodies; prices $88 → $45 in order ✅ |
| Search "grey tee" while limited to Hoodies | "No products match 'grey tee'" with **Search all categories** and **Clear filters** ✅ |
| Click **Search all categories** | 17 gray T-shirts (database query also returns 17) ✅ |
| Open the first card | Breadcrumb "Products › T-shirts › 2025 Yale Vs Harvard T Shirt"; Back link = `/products?sort=price_high&instock=1&q=grey+tee` ✅ |
| Click **Back to products** | Same 17 results, search box still says "grey tee" ✅ |
| Phone (375px) | 2 columns, full-width search, swipeable chips, nav 91px tall with no links off-screen, no horizontal scrolling ✅ |
| Tablet (768px) | 3 columns, no horizontal scrolling ✅ |
| Desktop (1280px) | 4 columns, search and chips on one screen ✅ |
| Home banner search: typed "davenport", pressed Enter | Opened `/products?q=davenport` with the search box filled; 1 result, Davenport College Crewneck (the only Davenport product) ✅ |
| Breadcrumb category link (from a product opened out of chat results) | Opened `/products?cat=Quarter-zips`, "Showing 11 of 102", Quarter-zips chip active; chat results cleared ✅ |
| Products request made to fail once | "Products didn't load / We couldn't load products right now." with **Try again**; clicking it loaded all 102 ✅ |

**Bugs found and fixed during testing:** (1) choosing a category and then a sort within the same moment lost the category, because each change was built from a stale copy of the filters. Changes now build on the live URL, and the retest kept all three filters. (2) Found in the audit: on a filtered page (e.g. `?cat=Hoodies`), a chat search's results were cleared instantly by the filters in the URL, so Dan said "I've put them on the page" while the page still showed hoodies. Results are now cleared only by explicit catalogue actions (home search, breadcrumbs, "Show all products"), and chat results open on a clean `/products`; retest showed "Quarter-zips", 11 cards.

---

## 2. Improved AI Chat Interface and Customer Experience

**Category:** Front-end

### What was implemented

- **Clearly branded assistant:** the floating button is now "Ask Dan" with Handsome Dan's face (white-ringed navy pill), and the panel header shows Dan's avatar, **Handsome Dan**, and "Campus Customs shopping assistant" on a Yale-blue gradient.
- **Welcoming message that explains what Dan can do:** "Hi! I'm Handsome Dan, your Campus Customs shopping assistant. I can find gear by type, color, or budget, check sizes and stock, and help you pick a gift. Log in if you want me to remember our chat." Logged-in customers get "Welcome back, Test! … I'll remember our chat for next time."
- **Clickable suggested questions:** "Show me hoodies", "What products are available?", "Help me find a gift", "Anything under $40?". On a product page they switch to "Does this come in another color?", "What sizes are in stock?", "Show me similar items", and the input placeholder becomes "Ask about this item…".
- **Typing indicator:** three animated dots in a Dan bubble (with "Handsome Dan is typing" for screen readers) while a reply is on its way; Send shows "…" and is disabled.
- **Clear difference between customer and AI messages:** customer messages are navy bubbles on the right; Dan's are white bubbles on the left with his avatar; screen readers hear "You said:" / "Handsome Dan said:".
- **Automatic scrolling:** jumps to the latest message when the panel opens, then smoothly scrolls to each new message and the typing indicator.
- **Mobile-friendly:** under 600px wide the chat opens full screen with its own close button, the floating button hides, and the input uses 16px text so iPhones don't zoom in. Escape closes the chat on desktop; the input is focused when the chat opens.
- **Friendly errors with retry:** a failed request shows a soft red bubble ("Sorry, I couldn't answer that. We can't reach Campus Customs right now. Check your connection and try again.") with a **↻ Try again** button. The shopper's message stays visible, and retry resends it without duplicating it. Error text is never technical: the site only shows a server message if it is short and contains nothing developer-like (traceback, exception, error:, sqlite, .py, line numbers, braces); otherwise it shows a generic sentence.
- **No double sends:** a send lock blocks a second submission (button, Enter key, or suggestion click) while one is in progress.

### Why it helps

Shoppers immediately recognize who they're talking to and what Dan can do, and the suggestions give them a one-click way to start. The typing dots and clear bubbles show what's happening, and a dropped connection becomes a one-click retry instead of a dead end. On phones the chat is usable full screen instead of squeezed into a corner.

### Files changed

| File | Change |
|---|---|
| `frontend/src/components/ChatWidget.tsx` | Rebuilt UI around the existing send/history/page-results logic: branding, welcome, suggestions, typing dots, avatars, smooth scroll, retry, send lock |
| `frontend/src/api.ts` | Friendly error messages (network vs server); `retryText` on error bubbles |
| `frontend/src/chatSearch.tsx` | Stable callbacks (so pages can safely react to chat results) |
| `frontend/src/index.css` | Chat styles, typing animation, suggestions, error bubble, full-screen phone layout |

### How it was tested

| Test | Result |
|---|---|
| Open chat as a guest (desktop) | Dan header, welcome text, 4 suggestion chips, input focused ✅ |
| Click "Show me hoodies" | Typing dots visible (3 dots), Send disabled, suggestions hidden; reply "We have 27 hoodies in stock, ranging from $45 to $68…"; Products page shows 27 hoodie cards; message list scrolled to bottom ✅ |
| Simulated network failure on the next send ("Do you have anything in blue under $40?") | Red error bubble with friendly text and **↻ Try again**; question still shown ✅ |
| Click **Try again** (connection restored) | Error bubble removed, question appears once, real reply received ✅ |
| Logged in, open chat on Basic Hoodie Big Yale | Saved history reloaded (22 messages) + "Welcome back, Test!"; product suggestions shown; placeholder "Ask about this item…" ✅ |
| Click "Does this come in another color?" | "This hoodie comes in navy blue and white. For another color, the Yale Sports Hoodie Tennis also comes in heather gray." with both cards ✅ |
| Phone (375×812) | Panel exactly 375×812 (full screen), floating button hidden, input 16px ✅ |
| Phone: tapped "Anything under $40?" | Reply "25 items under $40… $32 T-shirts" (database: 25 products at $32, none others under $40); **See all 25 on the page →** closed the chat and showed 25 cards in 2 columns; floating button back ✅ |
| Server replies simulated in the browser: 502 friendly, 409 busy, 504 timeout, 400 bad input | Each shown as its friendly sentence with **↻ Try again** ✅ |
| Server replies with technical text: a 300-character traceback, `sqlite3.OperationalError: no such table: catalogue`, `KeyError: product_id in main.py line 42` | All shown as "Something went wrong on our end. Please try again."; no technical words displayed ✅ |
| Escape key with the chat focused | Chat closed ✅ |

---

## 3. More Accurate Product Recommendations

**Category:** Agent/backend

### What was implemented

- **Smarter search tool** (`search_products`) that understands everyday shopping language:
  - `category`: the 6 real categories, also accepting shopper words ("tees", "quarter zip", "sweaters").
  - `color` by **family**: "blue" matches navy, navy blue, royal blue, light blue; "gray"/"grey" includes charcoal; "white" includes ivory and cream; "pink" finds the closest real color (dusty coral). Matches the product's listed colors only, so a navy logo on a gray tee doesn't count as "blue".
  - `size`: only products in stock in that size ("gray hoodie in XL").
  - `min_price` / `max_price` and `sort` (`price_low` for "affordable/cheap/budget", `price_high` for "premium/nicest", `name`).
  - Returns true totals (`total_in_stock`, `total_including_sold_out`), so the agent never counts the 12-item sample.
- **Real alternatives when nothing matches:** the tool drops the most specific filter first (color → size → price → keyword → type) until real, in-stock products appear, and says which filters it dropped (`relaxed_filters`). For things we don't carry at all (sneakers, caps) it returns one real in-stock pick per category (`relaxed_filters: ["all"]`).
- **New tool `similar_products`:** for "Does this come in another color?" or "anything like this?", returns in-stock products in the same category, most similar first. (Each catalogue product has fixed colors; other colors are separate products.)
- **Automatic fact-check of every answer** (`@agent.output_validator` in `agent.py`) before it reaches the shopper:
  - Any **dollar amount** that no tool returned in this conversation (and that the shopper didn't type, like "under $60") is rejected.
  - Any **discount, "% off", or promo code** claim is rejected (Campus Customs has none).
  - **Product cards** for ids no tool returned are dropped.
  - On a rejection the model is told exactly what was wrong and must fix it (PydanticAI `ModelRetry`), so invented prices and discounts can't reach the page.
- **Prompt updates** (`prompts/prompt.md`, "Recommending products"): search before recommending; a table that turns everyday requests into filters ("affordable hoodies" → Hoodies + price_low; "anything in blue?" → color blue; "a gift for my dad" → one quick question or 2–3 options at different prices); how to use alternatives; how to answer "another color?" on a product page; and **read each request on its own terms** (only carry filters over when the shopper says "those/them/what about in XL?").
- Recommendations still flow through the Problem 7 structured response: `page_search` now also carries `category`, `size`, `min_price`, and `sort`, and the server runs the same search to fill the Products page.

### Why it helps

Shoppers get answers that match how they actually talk, and every name, price, color, size, and stock count comes from the catalogue. They aren't told about blue items that don't exist, discounts that don't exist, or "12 hoodies" when there are 27. When we don't have something, they get a useful real alternative instead of a dead end. That builds trust in the assistant and keeps customers shopping.

### Files changed

| File | Change |
|---|---|
| `backend/tools.py` | `search_products` (category, color families, size, min/max price, sort, alternatives); shared `_search_rows`; new `similar_products`; `page_listings` uses the new filters |
| `backend/agent.py` | `grounded_in_catalogue` output validator (prices, discounts, product ids) |
| `backend/models.py` | `SearchResults.alternatives` / `relaxed_filters`; `category` on `ProductSummary` / `ProductListing`; `PageSearch` gains `category`, `size`, `min_price`, `sort` |
| `backend/db.py` | `CATEGORIES`, `category_for()` |
| `backend/prompts/prompt.md` | "Recommending products" section; `similar_products` row; fresh-search rule |

### How it was tested

Chat questions through the API, with every price and count checked against the database:

| Shopper message | Agent's answer | Database |
|---|---|---|
| Show me affordable hoodies | Lowest-priced: Ua Gameday Double Knit Hood and Yale Sports Hoodie Tennis, $45; all 27 on the page | $45 is the lowest hoodie price ✅ |
| Do you have anything in blue? | 87 blue options; tees at $32; page "Blue items", 87 | 87 products list blue/navy ✅ |
| Do you have a pink hoodie? | No pink hoodies; offers navy, white, and gray hoodies as cards | 0 pink/coral hoodies ✅ |
| I need a baseball cap | We don't carry caps; suggests a tee and a hoodie | not in catalogue ✅ |
| Does this come in another color? (on Basic Hoodie Big Yale) | Navy blue and white; suggests the gray Tennis hoodie and charcoal Bulldog hoodies | colors match ✅ |
| Is there a student discount or promo code? What's the sale price of the Basic Hoodie Big Yale? | No student discounts or promo codes; $68 is the listed price, not a sale price | $68 ✅ |
| Help me find a gift | Three crewneck options ($45 and $58) plus a question about who it's for | prices match ✅ |
| "Show me hoodies" then "Do you have anything in blue under $40?" | 21 blue items under $40 (searched all categories) | 21 ✅ |
| "Show me hoodies" then "what about in XL?" | 21 hoodies in XL | 21 ✅ |

**Bug found and fixed during testing:** after "Show me hoodies", the question "anything in blue under $40?" was first treated as hoodies only, so it found nothing. The fresh-search rule fixed it while keeping real follow-ups like "what about in XL?" working.

Automated tests (`backend/tests/test_backend.py`) cover color families, "grey" = "gray", category words, sort order, the size filter, alternatives, `similar_products`, and the fact-check (invented price rejected, real price accepted, shopper-typed price allowed, discount rejected, unknown ids dropped, current product allowed).

---

## 4. Faster, Safer, and More Reliable AI Conversations

**Category:** Agent/backend

### What was implemented

- **Message validation:** `ChatRequest.message` strips invisible control characters and whitespace and rejects anything empty after that; 2,000-character limit; history turns are cleaned the same way.
- **Structured AI output validation:** `AgentOutput.reply` must be non-empty (capped at 2,000 characters); `product_ids` are de-duplicated and capped at 6; plus the catalogue fact-check from Improvement 3. Invalid output makes the model retry instead of reaching the shopper.
- **Graceful error handling, no technical details** (the live 429, 504, 502, and 500 responses were verified with automated tests that stub the AI call, not by waiting for real outages):
  - Bad requests (empty, too long, malformed JSON, wrong types) → HTTP 400 "Please type a message (up to 2,000 characters)." instead of Pydantic's error list.
  - Model timeouts → 504 "That took longer than expected. Please try again."
  - Model API errors → 502 friendly message; content-filter blocks → a polite decline (from Problem 5).
  - Any unexpected error anywhere → 500 "Something went wrong on our end. Please try again."; details go only to the server log.
  - Invalid product ids from the model are dropped (cards are built only from real catalogue rows).
- **Time and cost limits per message:** 30-second timeout and 1 retry per model call, 60 seconds for the whole answer, and at most 8 model requests / 10 tool calls (`UsageLimits`), so a confused run can't loop or run up cost.
- **No duplicate or overlapping sends:** besides the front-end lock, the server keeps one chat request in flight per shopper (logged-in customers keyed by id; guests by a random id put in their session cookie when the site loads). A second request while one is running gets 409 "I'm still working on your last message. One moment!" and isn't saved. A per-shopper cap of 12 messages a minute returns 429 with a friendly message.
- **Less history sent to the AI:** the last 12 messages (was 20 for customers), each shortened to 800 characters, with at most 6,000 characters in total, and always starting on a customer turn. Enough for follow-ups, without paying to resend long old answers.
- **Efficient database access:**
  - **Migration:** `CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages (user_id, id)` runs at startup, so loading a customer's history doesn't scan the whole table.
  - `get_db()` now **always closes its connection** (the old `with sqlite3.connect()` only committed and left it open), commits writes, and rolls back on errors.
  - Each search is one SQL query; category, color-family, and size filters run on the (at most 102) rows returned.
- **Kept from Problems 7–8 and re-verified:** customers only ever see their own history (user id from the signed session cookie; `?user_id=` is ignored); guests chat without logging in (history endpoint returns 401 for them, nothing saved); logged-in customers resume their saved chat.

### Why it helps

Shoppers get consistent answers and plain-language messages instead of stack traces or blank screens, and can't accidentally send a question twice. The business pays for less AI usage per message (shorter history, capped tool loops, timeouts), the database stays fast as chat history grows, and customer data stays private.

### Files changed

| File | Change |
|---|---|
| `backend/models.py` | `clean_text`; validators on `ChatRequest`, `ChatTurn`, `AgentOutput` |
| `backend/agent.py` | Timeouts, retries, `UsageLimits`, `trim_history`, output fact-check |
| `backend/main.py` | Friendly 400/500 handlers; one-in-flight guard and per-minute cap; 504 on timeout; startup index |
| `backend/auth.py` | Guests get a chat id when the site loads (`/api/auth/me`) |
| `backend/history.py` | Agent history reduced to 12 messages |
| `backend/db.py` | `get_db()` context manager that commits, rolls back, and closes |
| `backend/tests/test_backend.py` | **New** automated test suite (31 tests, standard library only, temp copy of the DB for write tests) |
| `frontend/src/api.ts` | Never shows non-shopper error text; network failures get a friendly message |

**Database migration:** one new index, `idx_chat_messages_user` on `chat_messages (user_id, id)`, created automatically and safely (`IF NOT EXISTS`) when the backend starts. No tables or columns changed.

### How it was tested

| Test | Result |
|---|---|
| `{"message": ""}`, `"    "`, 2,500 characters, malformed JSON, wrong types | All HTTP 400 "Please type a message (up to 2,000 characters)." ✅ |
| Guest `GET /api/chat/history` | 401 "Log in to see your saved chat." ✅ |
| Two identical sends 0.5s apart (guest, and logged-in Test User) | First 200; second 409 "I'm still working on your last message…"; only one exchange (+2 rows) saved ✅ |
| Test User `GET /api/chat/history?user_id=3` | Returned only Test User's own 24 messages, none of user 3's (checked message by message against the database) ✅ |
| Logged in again in the browser | Saved chat reloaded with "Welcome back, Test!" ✅ |
| Index | `.indexes chat_messages` shows `idx_chat_messages_user` ✅ |
| Error paths (automated, with the AI call stubbed): timeout → 504 `CHAT_TIMEOUT`; model failure → 502 with no internals in the message; in-flight lock released after an error; duplicate → 409; 13th message in a minute → 429; unexpected error handler → 500 without the exception text; bad chat input handler → 400 "Please type a message…" | All pass ✅ |
| Automated tests: `cd backend && .venv/bin/python -m unittest discover tests` | **31 passed**, also with resource warnings turned into errors (confirms connections are closed) ✅ |
| Front end: `npm run build` (TypeScript check + build) | Passes ✅ |

**Bug found and fixed during testing:** the duplicate-send guard didn't work for a guest's very first message, because their chat id was only created inside that first request. Guests now get the id when the site loads, and the retest returned 409 for the duplicate.

---

## Running the automated tests

```bash
cd backend && .venv/bin/python -m unittest discover tests -v
```

```bash
cd frontend && npm run build
```

---

## Audit (follow-up)

Every claim above was re-checked against the running app. Items that had been implemented but not yet exercised were tested; anything verified only by automated tests says so.

**Issues found and fixed in the audit**

1. **Chat search on a filtered Products page didn't show its results** (broken Problem 7 behavior). Fixed in `Products.tsx`, `ChatWidget.tsx`, `Home.tsx`, `ProductDetail.tsx`; verified in the browser.
2. **Short technical server messages could have been shown to shoppers** (the filter only checked length). Fixed in `api.ts`; verified with three simulated technical errors.
3. **Overclaim in this document:** "4–5 columns on desktop" was only verified at 1280px (4 columns). Corrected.
4. **Error paths had no tests:** added 7 automated tests (429, 504, 502, 500, 400, 409, lock release). Suite: 24 → 31.
5. **A test left a database connection open** (the app code was fine). Fixed; 31 tests pass with zero resource warnings.

**Not a requirement gap, but worth knowing:** the per-minute cap and duplicate guard keep their counters in memory, so they reset if the backend restarts and wouldn't be shared across multiple server processes. That's fine for this single-server project.

## Final checklist

| Improvement | Requirement | Built | Verified how |
|---|---|---|---|
| **1. Product discovery** (front-end) | Prominent search bar | ✅ | Browser: Products search ("grey tee" → 17); Home search ("davenport" → 1) |
| | Category filters from real catalogue | ✅ | Automated (all 102 products categorized); browser (Hoodies 27, Quarter-zips 11) |
| | Sorting (price both ways, name) | ✅ | Browser: Hoodies price high → low $88…$45 |
| | Clear cards (image, name, price, short description) | ✅ | Browser screenshots; category label and Sold out tag |
| | Responsive grid (desktop, tablet, mobile) | ✅ | Browser: 4 / 3 / 2 columns at 1280 / 768 / 375px; no horizontal scroll |
| | Helpful no-match messages | ✅ | Browser: "No products match 'grey tee'" + Search all categories / Clear filters; load failure + Try again |
| | Clear listing ↔ detail navigation | ✅ | Browser: breadcrumbs, Back keeps filters, category crumb opens filtered list |
| **2. Chat interface** (front-end) | Branded, identifiable assistant | ✅ | Browser: "Ask Dan" button, Handsome Dan header |
| | Welcome explaining what it can do | ✅ | Browser: guest and logged-in versions |
| | Clickable suggested questions | ✅ | Browser: "Show me hoodies", "Anything under $40?", "Does this come in another color?" all sent and answered |
| | Loading / typing indicator | ✅ | Browser: 3 animated dots shown while waiting; Send disabled |
| | Customer vs AI messages clearly different | ✅ | Browser: navy right vs white left with avatar |
| | Auto-scroll to new messages | ✅ | Browser: list at bottom after reply |
| | Mobile-friendly | ✅ | Browser (375px): full screen, send/receive, See all on page |
| | Friendly errors with retry | ✅ | Browser: network failure + retry; simulated 400/409/500/502/504 |
| **3. Accurate recommendations** (agent/backend) | Search catalogue before recommending | ✅ | Prompt rule + fact-check; every live answer checked against DB |
| | Grounded in real names, prices, colors, sizes, stock | ✅ | 9 live chat answers, all prices and counts matched the database |
| | No invented products, prices, discounts, inventory | ✅ | Automated: invented price and promo code rejected, unknown ids dropped; live: "student discount?" answered correctly |
| | Natural-language requests ("affordable hoodies", "anything in blue?") | ✅ | Live chat + automated search tests |
| | Uses structured response for page cards | ✅ | Live: page results for hoodies, blue under $40, under $40 |
| | Helpful alternatives on no match | ✅ | Live: pink hoodie, baseball cap; automated: relaxed filters |
| | Product page awareness ("another color?") | ✅ | Browser (logged in) and live API |
| **4. Reliability** (agent/backend) | Validate messages and AI output | ✅ | Live 400s for empty/whitespace/too long/bad JSON/wrong types; automated validators |
| | Handle empty, invalid product results, API failures, unexpected errors | ✅ | Live 400s; automated 502/504/500 and dropped invalid ids; browser shows friendly text |
| | Prevent duplicate submissions | ✅ | Browser send lock; live 409 (guest and logged in) with only one exchange saved; automated 409 |
| | Customers only see their own history | ✅ | Live: Test User with `?user_id=3` got only their own 24 messages; automated isolation test |
| | Guest chat without login | ✅ | Browser and live (guest chat answered; history 401) |
| | Efficient lookups and queries | ✅ | Index present; connections closed (tests with resource warnings as errors); one SQL query per search |
| | Limit history sent to the AI | ✅ | Automated: ≤12 messages, ≤6,000 characters |
| | Customer memory still works | ✅ | Browser: logged in, 22 saved messages reloaded + "Welcome back, Test!" |
| | No technical errors shown to customers | ✅ | Live 400 messages; automated 500/502; browser filter of technical text |
| **Documentation** | `output/usability.md` with name, category, what, why, files, testing for all four | ✅ | This file (corrected in this audit) |
| **Testing** | Automated tests run and passing | ✅ | 31/31 backend; TypeScript build passes; lint has no errors |

---

## Status at final review

Re-checked at the end of the project (after Problems 10–12). Everything above still works in the running app; the counts above are as of Problem 9. The automated suite has since grown from 31 to **45 tests** (Problem 12 added audit-trail, execution-limit, and safety-enforcement tests), all passing, and the TypeScript build and lint are clean. Problem 10 restyled these features without changing their behavior; Problem 11's report (`output/app_check.html`) re-verified the category filter, sort, no-match feedback, mobile layout, and suggested questions in the browser.
