# Library Management System

A local admin tool for a self-study library serving ~40 students at subsidized rates.
Built with **Python**, **Flask**, **SQLite**, **Bootstrap 5**, and **Matplotlib**.
No internet connection required after install — runs fully offline.

---

## Screenshots

| Dashboard | Students | Student Profile |
|-----------|----------|-----------------|
| KPI cards with live overdue scan | Avatar initials + tier badges | Two-column card with borrow history |

---

## Project Structure

```
library-management-system/
├── app.py                  # Entry point — registers blueprints, starts server
├── requirements.txt        # Flask 3.1 + Matplotlib 3.11
├── library.db              # SQLite database (auto-created on first run)
│
├── models/
│   ├── database.py         # Connection factory, schema DDL, init_db()
│   ├── book.py             # Book CRUD + availability helpers
│   ├── student.py          # Student CRUD
│   └── transaction.py      # Issue / return / overdue / fine logic
│
├── routes/
│   ├── dashboard.py        # GET  /
│   ├── books.py            # GET  /books/  +  POST /books/add
│   ├── students.py         # GET  /students/  +  profile  +  add
│   ├── transactions.py     # POST /transactions/issue  +  /return
│   └── analytics.py        # GET  /analytics/
│
├── templates/
│   ├── base.html           # Shared layout — dark sidebar + sticky topbar
│   ├── dashboard.html      # KPI cards + quick actions
│   ├── books.html          # Book catalogue with search/filter
│   ├── add_book.html       # Add book form
│   ├── students.html       # Student list with avatar initials
│   ├── add_student.html    # Register student form
│   ├── issue_return.html   # Issue / return with tab switcher
│   ├── student_profile.html # Two-column profile + borrow history
│   ├── analytics.html      # Charts side-by-side + raw data table
│   └── 404.html            # Custom error page
│
└── static/
    └── style.css           # Bootstrap 5 override layer + sidebar layout
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Flask 3.1 |
| Database | SQLite 3 (stdlib — no install needed) |
| UI framework | Bootstrap 5.3 + Bootstrap Icons 1.11 |
| Charts | Matplotlib 3.11 (Agg backend, embedded as base64 PNG) |
| Templating | Jinja2 (comes with Flask) |

---

## Setup & Run

### 1. Clone the repo
```bash
git clone https://github.com/Dev252001/Library-Management-System.git
cd Library-Management-System
```

### 2. Create a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

Only two packages install — Flask and Matplotlib. Everything else is Python stdlib.

### 4. Run
```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

On first run `library.db` is created automatically with all three tables.
Press `Ctrl+C` to stop the server.

---

## Features

| Page | URL | What it does |
|------|-----|-------------|
| Dashboard | `/` | 5 live KPI cards — total copies, available, issued, overdue, fines |
| Book Catalogue | `/books/` | Search by title/author, filter by category, availability badges |
| Add Book | `/books/add` | Add a new title with copy count |
| Students | `/students/` | Member list with avatar initials and tier badges |
| Register Student | `/students/add` | Register a new member with fee tier |
| Student Profile | `/students/<id>` | Full borrow history + outstanding fine summary |
| Issue Book | `/transactions/issue` | Issue a copy — unavailable books shown but disabled |
| Return Book | `/transactions/return` | Enter Transaction ID — fine calculated and displayed |
| Analytics | `/analytics/` | Top 5 books bar chart + monthly volume line chart |

---

## Business Rules

### Loan period
Every book is issued for **14 days** from the issue date.
Due date is calculated automatically — the librarian never sets it manually.

### Overdue detection
On every page load, the system scans all `issued` transactions whose
`due_date` is before today and marks them `overdue`. No cron job needed.

### Fine calculation

> When a book is returned, the system counts the number of calendar days
> between the due date and the actual return date; if that number is greater
> than zero, a fine of **₹2 per overdue day** is charged.
> The fine is hard-capped at **₹50** regardless of how many days late,
> because the library serves subsidized students and the fine should be a
> deterrent, not a debt.
> For books not yet returned, today's date is used as a stand-in so the
> dashboard always shows a live running total of outstanding fines.

Fine constants are defined in one place — [`models/transaction.py`](models/transaction.py):

```python
LOAN_DAYS    = 14    # days before a book is overdue
FINE_PER_DAY = 2.0   # rupees per overdue day
FINE_CAP     = 50.0  # maximum fine (rupees)
```

---

## Edge Cases Handled

| Scenario | Behaviour |
|----------|-----------|
| Issue a book with 0 copies | Error: "no copies available" |
| Issue same book twice to one student | Error: "already has an unreturned copy" |
| Return an already-returned book | Error: "already marked as returned" |
| Invalid Transaction ID or Student ID | HTTP 404 or inline error message |
| `fee_tier` tampered via POST | SQLite CHECK constraint blocks it |
| Non-integer or < 1 total copies | Validated in route before hitting DB |

---

## UI Overview

- **Dark sidebar** with Bootstrap Icons for navigation
- **Sticky topbar** with page title and quick-action buttons
- **KPI cards** with colour-coded icon badges (blue / green / amber / red / purple)
- **Avatar initials** circle generated from student name — no images needed
- **Bootstrap 5 tables** with hover, responsive wrapper, and status badges
- **Nav-pill tabs** for Issue / Return on a single page
- **Dismissible alerts** with icons for all flash messages
- **Side-by-side chart cards** on the analytics page with a medal rank table

---

## Reset Data

```bash
# Windows
del library.db

# macOS / Linux
rm library.db
```

The database recreates itself empty on the next `python app.py`.

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 3.1.* | Web framework, routing, Jinja2 templates, flash messages |
| Matplotlib | 3.11.* | Server-side PNG chart generation (Agg — no display needed) |
| sqlite3 | stdlib | Relational database |
| datetime | stdlib | Due-date and overdue calculations |
| base64 / io | stdlib | Encoding charts as inline data URIs |
