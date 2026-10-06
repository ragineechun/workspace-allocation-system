# Workspace Allocation System

A web app for booking shared rooms and workspaces in a college or office. Users sign up, browse workspaces, and reserve a time slot; the app blocks double bookings and clashes with the class timetable.

Built with Flask, SQLite and plain HTML/CSS.

## Features

- **Accounts and roles** – sign up and log in as an Admin or a User; passwords are stored hashed.
- **Workspace booking** – reserve a workspace for a date and time slot. Bookings must fall between 8:00 AM and 5:00 PM and last 45 minutes to 4 hours.
- **Conflict checks** – a slot is rejected if it overlaps another booking or a scheduled class in that room.
- **Class routine** – enter a division's subjects for a day and the app assigns each period a free room with enough capacity.
- **Floor map** – rooms shown per floor; admins can add rooms and adjust their positions.
- **Notifications** – a log of bookings, cancellations and workspace changes, shown in Indian Standard Time.
- **My bookings, profile and settings** – view and cancel bookings, update your details, or delete your account.

## Tech stack

| Layer | Tools |
|---|---|
| Backend | Python, Flask, Flask-Login |
| Database | SQLite via Flask-SQLAlchemy |
| Frontend | HTML, CSS, Jinja2 templates, JavaScript |

## Run it locally

You need Python 3.10 or newer.

```bash
git clone https://github.com/<your-username>/workspace-allocation-system.git
cd workspace-allocation-system

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
python main.py
```

Open http://127.0.0.1:5000, sign up, and start booking. The database is created automatically on first run with three sample workspaces.

Helper scripts:

- `pop.py` – drops and recreates all tables.
- `reset.py` – deletes the database file.

## Project structure

```
main.py               entry point
requirements.txt
website/
  __init__.py         app setup, database, default workspaces
  auth.py             login, sign-up, logout
  models.py           User, Workspace, Booking, Notification, ClassRoutine
  views.py            booking, class routine, floor map, profile
  templates/          HTML pages
  static/styles/      CSS
```

## Team

This was a team project.

- **Raginee Chunkhare** – frontend pages (HTML/CSS templates), design and testing
- **Souvik** – teammate
- **Vedika**
