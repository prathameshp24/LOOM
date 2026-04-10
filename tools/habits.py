from core.habit_manager import (
    logHabit, getAllHabits, createHabit, getHabitLogs
)


def logHabitTool(habit_name: str, note: str = "") -> str:
    """Logs a habit check-in for today. Use when the user says they completed a habit:
    'I meditated', 'just worked out', 'finished my run', 'did yoga', 'did DSA today'.
    habit_name should match one of the user's tracked habits.
    note is optional context like '30 minutes' or 'felt great'."""
    return logHabit(habit_name, note)


def getHabitStatus(habit_name: str = "") -> str:
    """Returns today's status and streak for a habit. If habit_name is empty,
    returns a summary of ALL habits. Use when user asks 'did I work out today?',
    'how is my DSA streak?', 'show my habits', 'am I on track this week?'."""
    habits = getAllHabits()
    if not habits:
        return "No habits are being tracked yet."

    if habit_name:
        query = habit_name.lower().strip()
        matches = [h for h in habits if query in h["name"].lower() or h["name"].lower() in query]
        if not matches:
            known = ", ".join(h["name"] for h in habits)
            return f"No habit matching '{habit_name}' found. Known habits: {known}."
        habits = matches

    lines = []
    for h in habits:
        freq = h["frequency_per_week"]
        streak = h["streak"]
        goal = h["goal_days"]
        total = h["total_checkins"]

        if freq == 7:
            status = "✓ Done today" if h["checked_today"] else "✗ Not done today"
            streak_str = f"{streak} day streak"
            lines.append(f"{h['name']}: {status} | {streak_str}")
        else:
            wc = h["this_week_count"]
            status = f"{wc}/{freq} this week"
            streak_str = f"{streak} week streak"
            line = f"{h['name']}: {status} | {streak_str}"
            if goal:
                line += f" | {total}/{goal} total sessions"
            lines.append(line)

    return "\n".join(lines)


def createHabitTool(name: str, description: str = "", frequency_per_week: int = 7, goal_days: int = 0) -> str:
    """Creates a new habit to track. frequency_per_week is how many times per week
    (1-7, default 7 = daily). goal_days is an optional total session target (0 = no goal).
    Use when user says 'track DSA 3 times a week', 'add habit Y', 'I want to do Z daily for 30 days'."""
    try:
        createHabit(
            name=name,
            description=description,
            frequency_per_week=frequency_per_week,
            goal_days=goal_days if goal_days > 0 else None
        )
        freq_str = "daily" if frequency_per_week == 7 else f"{frequency_per_week}x/week"
        goal_str = f" Goal: {goal_days} sessions." if goal_days and goal_days > 0 else ""
        return f"Created habit '{name}' ({freq_str}).{goal_str} You can now log it anytime."
    except ValueError as e:
        return str(e)
