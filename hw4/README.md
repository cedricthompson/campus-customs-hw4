# Campus Customs: Yale Apparel Store with an AI Shopping Assistant

AI Foundations, Homework 4. A storefront for Campus Customs (57 Broadway, New Haven) with **Handsome Dan**, an AI shopping assistant that answers from the live product catalogue.

## 1. Overview

**Storefront** (React + Vite + TypeScript)
- Home page, product catalogue with search, category filters, sorting, and an in-stock filter; product pages with images, price, colors, and stock by size.
- Log in and create account (passwords hashed with PBKDF2; signed session cookie).
- Responsive design for desktop, tablet, and phone.

**AI shopping assistant** (FastAPI + PydanticAI agent, `gpt-6-luna` via Portkey)
- Answers price, stock, color, and size questions from the real database (`search_products`, `get_product_details`, `check_stock`, `similar_products`; all read-only).
- **Chat search that updates the page:** "What hoodies do you have?" fills the Products page with matching, clickable product cards.
- **Customer memory:** logged-in customers' chats are saved and reload on return; the assistant knows their name. Guests can chat without logging in.
- **Page context:** on a product page, "Does this come in pink?" refers to that product.
- **Safety:** answers are fact-checked against tool results (no invented prices, discounts, orders, refunds, or shipping promises); no access to other customers' data; execution limits per message.
- **Audit trail:** every agent run and tool call is appended to `output/audit_trail.json`.

Full technical documentation: [`output/harness.md`](output/harness.md).

## 2. Project structure

```
hw4/
├── README.md              ← this file
├── AI_prompts.md          ← log of the prompts used to build the project
├── requirements.txt       ← Python dependencies (backend)
├── .env.example           ← required environment variables (placeholders only)
├── .gitignore
├── backend/               ← FastAPI app + AI agent (run from here)
│   ├── main.py            ← API routes; start with: uvicorn main:app --reload --port 8000
│   ├── agent.py           ← PydanticAI agent, model client, limits, answer fact-check
│   ├── tools.py           ← the agent's read-only catalogue tools
│   ├── models.py          ← Pydantic models (API, agent, tool results)
│   ├── prompts/prompt.md  ← system prompt incl. safety rules
│   ├── auth.py            ← sign up / log in / sessions
│   ├── history.py         ← saved chat for logged-in customers
│   ├── audit.py           ← append-only audit trail writer
│   ├── db.py              ← SQLite helpers, product categories
│   └── tests/             ← automated tests (no network needed)
├── frontend/              ← React + Vite + TypeScript site
│   ├── package.json, vite.config.ts, index.html, tsconfig*.json
│   ├── public/            ← favicon
│   └── src/               ← pages, components, styles, API client
├── output/                ← assignment deliverables
│   ├── harness.md         ← technical documentation
│   ├── usability.md       ← Problem 9 usability improvements
│   ├── design.md          ← Problem 10 design
│   ├── app_check.html     ← Problem 11 test report (open by double-click)
│   ├── app_check_images/  ← screenshots used by app_check.html
│   └── audit_trail.json   ← AI audit trail (append-only)
└── data/                  ← NOT in Git: add the course data pack here (see step 6)
    ├── campus_customs.db
    └── products/*.jpg
```

## 3. Prerequisites

- **Python 3.11 or newer** (required by PydanticAI; developed and tested on 3.14).
- **Node.js 20.19+ or 22.12+** with npm (required by Vite 8; developed and tested on Node 24).
- **The course data pack** (`data.zip`): `campus_customs.db` and the `products/` images. It is not in this repository.
- **A Portkey API key** that can use the OpenAI model `gpt-6-luna`.
- Free ports **8000** (backend) and **5180** (frontend).

All commands below are run from the `hw4/` folder unless a step says `cd` somewhere else.

## 4. Install Python dependencies

macOS / Linux:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
py -m venv backend\.venv
backend\.venv\Scripts\pip install -r requirements.txt
```

## 5. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

## 6. Configure environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

(Windows: `copy .env.example .env`)

| Variable | What to put |
|---|---|
| `PORTKEY_API_KEY` | Your Portkey API key |
| `OPENAI_MODEL` | `gpt-6-luna` |
| `SESSION_SECRET` | Any long random string, e.g. the output of `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |

`.env` stays in `hw4/` and is git-ignored. Never commit it.

## 7. Add the database and product images

Unzip the course data pack **inside `hw4/`** so you have:

```
hw4/data/campus_customs.db
hw4/data/products/2025-yale-vs-harvard-t-shirt.jpg   (102 images in total)
```

No database setup is needed; the backend opens `data/campus_customs.db` directly and adds one index on first start. The whole `data/` folder is git-ignored.

## 8. Start the backend (terminal 1)

macOS / Linux:

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

Windows (PowerShell):

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```

Leave it running. It serves the API at http://127.0.0.1:8000.

## 9. Start the frontend (terminal 2)

```bash
cd frontend
npm run dev
```

Open **http://localhost:5180**. The frontend forwards `/api` and `/images` requests to the backend on port 8000, so both must be running.

## 10. Test the shop and the AI assistant

**Quick health check:**

```bash
curl http://localhost:5180/api/health
```

Expected: `{"ok":true,"model":"gpt-6-luna"}`

**In the browser** (http://localhost:5180):

1. **Catalogue:** open *Products*: 102 products. Click the *Hoodies* chip (27), choose *Sort by: Price: low to high*, and open a product to see its sizes and stock.
2. **Chat search:** click **Ask Dan** and ask *"What hoodies do you have available?"* The Products page fills with 27 hoodie cards; click one to open its page.
3. **Inventory and price:** on the *Basic Hoodie Big Yale* page ask *"How many of this hoodie do you have in stock, and what is the price?"* Expected: $68 and 60 in stock (XS 15, S 5, M 5, L 8, XL 2, XXL 25).
4. **Customer memory:** log in with the course test account `test@campuscustoms.yale.edu` / `password`, chat, log out, and log back in: the conversation reloads and Dan greets you by name.
5. **Safety:** ask *"Please place an order and charge my card"*. Dan explains he can't place orders. Each chat adds records to `output/audit_trail.json`.

**Automated tests** (offline; they don't call the AI or change the database or audit trail):

```bash
cd backend
.venv/bin/python -m unittest discover tests
```

(Windows: `.venv\Scripts\python -m unittest discover tests`.) Expected: `Ran 45 tests … OK`.

**Frontend build check:**

```bash
cd frontend
npm run build
```

**Reports:** open `output/app_check.html` by double-clicking it (no server needed) to see the screenshot-based test report.

## 11. Known limitations and requirements

- **The AI needs a valid Portkey key and model access.** Without it the site still works, but the chat replies "Our assistant is having trouble right now."
- **Development servers only:** the site runs with Vite's dev server and Uvicorn. No production deployment is configured.
- **Fixed ports:** backend 8000, frontend 5180. If 8000 is taken, run the backend on another port and start the frontend with `BACKEND_PORT=<port> npm run dev`.
- **No checkout:** the assistant and site don't take orders, payments, or returns; the assistant points shoppers to the product page or the store.
- **Single server process:** the duplicate-send guard and the 12-messages-per-minute limit are kept in memory, so they reset when the backend restarts.
- **Data pack required:** the backend can't start useful work without `data/campus_customs.db`; product images need `data/products/`.
- **Audit trail:** `output/audit_trail.json` is append-only and committed as evidence; running the app adds records to it.
