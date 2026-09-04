# Library Management System

A local admin tool for a self-study library serving ~40 students at subsidized rates.
Built with Python, Flask, SQLite, and Matplotlib. No internet connection required.

---

## Project Structure

```
library-management-system/
├── app.py                  # Entry point — wires Blueprints, starts server
├── requirements.txt        # Flask + Matplotlib (all else is stdlib)
├── library.db              # SQLite database (auto-created on first run)
│
├── models/
│   ├── database.py         # Connection factory + schema DDL + init_db()
│   ├── book.py             # Book CRUD + availability helpers
│   ├── student.py          # Student CRUD
│   └── transaction.py      # Issue / return / overdue / fine logic
│
├── routes/
│   ├── dashboard.py        # GET  /
│   ├── books.py            # GET  /books/  + POST /books/add
│   ├── students.py         # GET  /students/  + profile + add
│   ├── transactions.py     # POST /transactions/issue + /return
│   └── analytics.py        # GET  /analytics/
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Shared layout (nav, flash messages)
│   ├── dashboard.html
│   ├── books.html / add_book.html
│   ├── students.html / add_student.html
│   ├── issue_return.html
│   ├── student_profile.html
│   ├── analytics.html
│   └── 404.html
│
└── static/
    └── style.css           # All styling — no external framework
```

---

## Prerequisites

- Python 3.10 or newer
- `pip` (comes with Python)

Verify your Python version:

```bash
python --version
```

---

## Setup & Run (3 steps)

### 1. Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

> A virtual environment isolates this project's dependencies from your
> system Python. Always activate it before running the app.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

This installs Flask and Matplotlib. Everything else (`sqlite3`, `datetime`,
`io`, `base64`) is part of Python's standard library.

### 3. Start the server

```bash
python app.py
```

On first run, `init_db()` creates `library.db` with all three tables.
Open your browser at:

```
http://127.0.0.1:5000
```

Press `Ctrl+C` to stop the server.

---

## Seeding Sample Data (optional)

To demo the system with pre-loaded books, students, and transactions, run
the seed script below **after** the server has been started at least once
(so `library.db` exists):

```bash
python seed.py
```

> If you haven't created `seed.py`, skip this step and add data through
> the web UI — register students, add books, then issue them.

---

## Feature Walkthrough

| Page | URL | What it does |
|---|---|---|
| Dashboard | `/` | KPI cards: total copies, available, issued, overdue, fines |
| Book Catalogue | `/books/` | Search by title/author, filter by category |
| Add Book | `/books/add` | Add a new title to the catalogue |
| Students | `/students/` | List all members |
| Register Student | `/students/add` | Register a new member |
| Student Profile | `/students/<id>` | Full borrow history + outstanding fines |
| Issue Book | `/transactions/issue` | Issue a copy to a student |
| Return Book | `/transactions/return` | Process a return; fine shown immediately |
| Analytics | `/analytics/` | Top 5 books + monthly volume charts |

---

## Business Rules

### Loan period
Every book is issued for **14 days** from the issue date.
The due date is calculated automatically — the librarian does not set it manually.

### Overdue detection
When any page loads, the system scans all `issued` transactions whose
`due_date` is before today and flips their status to `overdue`.
No scheduled job or daemon is needed.

### Fine calculation

> **Professor-ready summary (3 sentences):**
>
> When a book is returned, the system counts the number of calendar days
> between the due date and the actual return date; if that number is greater
> than zero, a fine of ₹2 per overdue day is charged.
> The fine is hard-capped at ₹50 regardless of how many days late the return
> is, because the library serves subsidized students and the fine is meant as
> a deterrent, not a debt.
> For books that have not yet been returned, the same formula is applied using
> today's date as a stand-in for the return date, so the dashboard always
> shows a live running total of outstanding fines rather than a stale figure.

The constants that govern this logic are defined in one place —
[`models/transaction.py`](models/transaction.py) lines 33–35:

```python
LOAN_DAYS    = 14     # borrow period in days
FINE_PER_DAY = 2.0    # ₹ per overdue day
FINE_CAP     = 50.0   # maximum fine (₹)
```

Changing any of these values takes effect immediately on the next server restart.

---

## Edge Cases Handled

| Scenario | Response |
|---|---|
| Issue a book with 0 copies available | Error: "no copies available" — book not issued |
| Issue the same book twice to one student | Error: "already has an unreturned copy" |
| Return an already-returned book | Error: "already marked as returned" |
| Return / profile with invalid transaction/student ID | HTTP 404 or inline error message |
| Book ID or student ID not found on issue | Error with the specific ID that wasn't found |
| `fee_tier` tampered to an invalid value via POST | SQLite CHECK constraint raises `IntegrityError` → friendly error flash |
| `total_copies` submitted as text or < 1 | Validated in the route before hitting the DB |

---

## Design Decisions (for your defence)

**Why SQLite and not PostgreSQL?**
This is a single-user local admin tool for 40 students. SQLite is a single
file, requires zero server setup, and its entire state can be backed up with
`cp library.db library.db.bak`. PostgreSQL would be the right choice if
multiple librarians needed concurrent write access from different machines.

**Why no ORM (SQLAlchemy)?**
Every query in this project is plain SQL that can be read aloud. An ORM
would hide the fine-calculation query behind method chains, making it harder
to explain to a reviewer without knowing the ORM's API.

**Why Blueprints?**
Each Blueprint is a self-contained group of routes for one concern (books,
students, transactions). When a bug is reported in "returning a book", you
open `routes/transactions.py` — not a 500-line `app.py`.

**Why are `decrement_available` / `increment_available` in `book.py` but
called from `transaction.py`?**
Both functions accept an external connection so that the book-copy change
and the transaction-row change share one database transaction. If either
write fails, SQLite rolls back both — you can never have a transaction row
without a matching copy decrement, or vice versa.

---

## Stopping & Restarting

```bash
# Stop
Ctrl+C

# Restart (data is preserved in library.db)
python app.py
```

To reset all data (start fresh):

```bash
# Windows
del library.db

# macOS / Linux
rm library.db
```

The database will be recreated empty on the next `python app.py`.

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| Flask | 3.1.* | Web framework, routing, Jinja2 templating, flash messages |
| Matplotlib | 3.11.* | Server-side PNG chart generation (Agg backend, no display needed) |
| sqlite3 | stdlib | Relational database, built into Python |
| datetime | stdlib | Due-date calculation, overdue detection |
| base64 / io | stdlib | Encoding charts as inline data URIs |
