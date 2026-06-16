from datetime import datetime, timedelta

def get_date_context():
    """
    Returns a dict of all current date-related values used across the dashboard.
    Moved from app.py main() route.
    """
    now = datetime.now()

    today_label = now.strftime("%b %d, %Y")
    current_month_name = now.strftime("%B")

    start_of_week = now - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    week_range = f"{start_of_week.strftime('%b %d')} – {end_of_week.strftime('%b %d')}"

    month_range = now.strftime("%b 1") + " – " + now.strftime("%b %d")
    year_label = now.year

    return {
        "now": now,
        "today_label": today_label,
        "current_month_name": current_month_name,
        "start_of_week": start_of_week,
        "end_of_week": end_of_week,
        "week_range": week_range,
        "month_range": month_range,
        "year_label": year_label,
    }