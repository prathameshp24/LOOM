import sqlite3
import os
import logging
from datetime import date, timedelta, datetime

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "loom_db", "habits.sqlite"))


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _init_db():
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS habits (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                name                TEXT NOT NULL UNIQUE,
                description         TEXT DEFAULT '',
                color               TEXT DEFAULT '#00d4ff',
                frequency_per_week  INTEGER DEFAULT 7,
                goal_days           INTEGER DEFAULT NULL,
                created_at          TEXT DEFAULT (date('now'))
            );

            CREATE TABLE IF NOT EXISTS checkins (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id    INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
                checked_on  TEXT NOT NULL,
                note        TEXT DEFAULT '',
                UNIQUE(habit_id, checked_on)
            );
        """)


_init_db()


# ── Streak helpers ────────────────────────────────────────────────────────────

def _week_start(d: date) -> date:
    """Monday of the week containing d."""
    return d - timedelta(days=d.weekday())


def _calculate_streak(checkin_dates: list[str], freq: int) -> int:
    """
    Daily (freq=7): consecutive days ending today (or yesterday).
    Sub-daily (freq<7): consecutive calendar weeks where check-in count >= freq.
    """
    if not checkin_dates:
        return 0

    dates = sorted({date.fromisoformat(d) for d in checkin_dates}, reverse=True)

    if freq == 7:
        # Consecutive day streak
        today = date.today()
        streak = 0
        expected = today if dates[0] == today else today - timedelta(days=1)
        for d in dates:
            if d == expected:
                streak += 1
                expected -= timedelta(days=1)
            elif d < expected:
                break
        return streak

    else:
        # Weekly streak: consecutive weeks meeting target
        from collections import defaultdict
        week_counts: dict[date, int] = defaultdict(int)
        for d in dates:
            week_counts[_week_start(d)] += 1

        today = date.today()
        current_week = _week_start(today)
        streak = 0
        week = current_week

        # Current week counts only if already met target
        while True:
            count = week_counts.get(week, 0)
            if week == current_week:
                # Partial week — only counts toward streak if already met
                if count >= freq:
                    streak += 1
                # Either way, continue checking past weeks
                week -= timedelta(weeks=1)
            else:
                if count >= freq:
                    streak += 1
                    week -= timedelta(weeks=1)
                else:
                    break

        return streak


def _this_week_count(habit_id: int) -> int:
    today = date.today()
    week_start = _week_start(today).isoformat()
    week_end = today.isoformat()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM checkins WHERE habit_id=? AND checked_on BETWEEN ? AND ?",
            (habit_id, week_start, week_end)
        ).fetchone()
    return row[0] if row else 0


# ── CRUD ──────────────────────────────────────────────────────────────────────

def createHabit(name: str, description: str = "", color: str = "#00d4ff",
                frequency_per_week: int = 7, goal_days: int = None) -> dict:
    try:
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO habits (name, description, color, frequency_per_week, goal_days) VALUES (?,?,?,?,?)",
                (name.strip(), description.strip(), color, max(1, min(7, frequency_per_week)),
                 goal_days if goal_days and goal_days > 0 else None)
            )
        logging.info(f"Habit created: {name}")
        return getAllHabits()[-1]
    except sqlite3.IntegrityError:
        raise ValueError(f"A habit named '{name}' already exists.")


def getAllHabits() -> list[dict]:
    with _get_conn() as conn:
        habits = conn.execute("SELECT * FROM habits ORDER BY id").fetchall()
        result = []
        for h in habits:
            h = dict(h)
            checkin_rows = conn.execute(
                "SELECT checked_on FROM checkins WHERE habit_id=? ORDER BY checked_on DESC",
                (h["id"],)
            ).fetchall()
            checkin_dates = [r["checked_on"] for r in checkin_rows]

            h["total_checkins"] = len(checkin_dates)
            h["checked_today"] = date.today().isoformat() in checkin_dates
            h["streak"] = _calculate_streak(checkin_dates, h["frequency_per_week"])
            h["this_week_count"] = _this_week_count(h["id"])
            result.append(h)
    return result


def getHabitLogs(habit_id: int, limit: int = 14) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT checked_on, note FROM checkins WHERE habit_id=? ORDER BY checked_on DESC LIMIT ?",
            (habit_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


def logHabit(habit_name: str, note: str = "") -> str:
    with _get_conn() as conn:
        habits = conn.execute("SELECT id, name, frequency_per_week FROM habits").fetchall()

    if not habits:
        return "No habits are being tracked yet. Add one first."

    # Fuzzy match: find best (longest-name) substring match
    query = habit_name.lower().strip()
    matches = [h for h in habits if query in h["name"].lower() or h["name"].lower() in query]
    if not matches:
        known = ", ".join(h["name"] for h in habits)
        return f"No habit matching '{habit_name}' found. Known habits: {known}."

    # Pick the best match (longest name = most specific)
    best = max(matches, key=lambda h: len(h["name"]))

    with _get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO checkins (habit_id, checked_on, note) VALUES (?, date('now'), ?)",
            (best["id"], note)
        )
        already_logged = conn.total_changes == 0

    if already_logged:
        return f"Already logged '{best['name']}' for today."

    # Recalculate streak after logging
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT checked_on FROM checkins WHERE habit_id=? ORDER BY checked_on DESC",
            (best["id"],)
        ).fetchall()
    checkin_dates = [r["checked_on"] for r in rows]
    streak = _calculate_streak(checkin_dates, best["frequency_per_week"])
    freq = best["frequency_per_week"]

    if freq == 7:
        return f"Logged '{best['name']}' for today. Streak: {streak} day{'s' if streak != 1 else ''}."
    else:
        week_count = _this_week_count(best["id"])
        streak_unit = f"{streak} week{'s' if streak != 1 else ''}"
        return (f"Logged '{best['name']}'. {week_count}/{freq} this week. "
                f"Streak: {streak_unit}.")


def logHabitById(habit_id: int, note: str = "") -> str:
    with _get_conn() as conn:
        habit = conn.execute("SELECT * FROM habits WHERE id=?", (habit_id,)).fetchone()
        if not habit:
            return f"Habit id {habit_id} not found."
        conn.execute(
            "INSERT OR IGNORE INTO checkins (habit_id, checked_on, note) VALUES (?, date('now'), ?)",
            (habit_id, note)
        )
        already_logged = conn.total_changes == 0

    habit = dict(habit)
    if already_logged:
        return f"Already logged '{habit['name']}' for today."

    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT checked_on FROM checkins WHERE habit_id=? ORDER BY checked_on DESC",
            (habit_id,)
        ).fetchall()
    checkin_dates = [r["checked_on"] for r in rows]
    streak = _calculate_streak(checkin_dates, habit["frequency_per_week"])
    freq = habit["frequency_per_week"]

    if freq == 7:
        return f"Logged '{habit['name']}' for today. Streak: {streak} day{'s' if streak != 1 else ''}."
    else:
        week_count = _this_week_count(habit_id)
        return f"Logged '{habit['name']}'. {week_count}/{freq} this week. Streak: {streak} week{'s' if streak != 1 else ''}."


def deleteHabitById(habit_id: int):
    with _get_conn() as conn:
        conn.execute("DELETE FROM habits WHERE id=?", (habit_id,))


# ── Orchestrator context ──────────────────────────────────────────────────────

def getHabitContextForOrchestrator() -> str:
    habits = getAllHabits()
    if not habits:
        return ""

    today = date.today()
    day_str = today.strftime("%A %B %-d")
    lines = [f"[SYSTEM HABIT CONTEXT: Today is {day_str}."]

    for h in habits:
        freq = h["frequency_per_week"]
        streak = h["streak"]
        name = h["name"]
        goal = h["goal_days"]
        total = h["total_checkins"]

        if freq == 7:
            status = "checked today ✓" if h["checked_today"] else "NOT done today"
            streak_str = f"streak {streak} day{'s' if streak != 1 else ''}"
            line = f"- {name}: {status} | {streak_str} | daily"
        else:
            wc = h["this_week_count"]
            status = f"{wc}/{freq} this week"
            streak_str = f"streak {streak} week{'s' if streak != 1 else ''}"
            line = f"- {name}: {status} | {streak_str} | {freq}x/week"
            if goal:
                line += f" | goal: {goal} sessions ({total} done)"

        lines.append(line)

    lines[-1] = lines[-1] + "]"
    return "\n".join(lines)
