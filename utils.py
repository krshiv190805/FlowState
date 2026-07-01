from datetime import datetime, timedelta

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def parse_time(t_str):
    if isinstance(t_str, timedelta):
        return t_str.total_seconds() / 3600.0
    parts = str(t_str).split(":")
    return int(parts[0]) + (int(parts[1]) / 60.0 if len(parts) > 1 else 0.0)

def get_slots(day, start_str, end_str):
    sh = int(parse_time(start_str))
    eh = int(parse_time(end_str) + 0.99)
    return [day * 24 + h for h in range(sh, eh) if 0 <= h < 24]

def slot_to_dh(slot):
    return slot // 24, slot % 24

def format_hour(h):
    if h == 0:
        return "12 AM"
    elif h == 12:
        return "12 PM"
    elif h < 12:
        return f"{h} AM"
    else:
        return f"{h-12} PM"
