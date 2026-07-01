import json
from datetime import datetime, timedelta
import utils
import db
import recommendation

def get_week_start():
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return today - timedelta(days=today.weekday())

def generate_schedule(user_id):
    pref = db.execute_query("SELECT * FROM preferences WHERE user_id = %s", (user_id,))
    if not pref:
        return None, "Preferences not set. Please set preferences first."
    pref = pref[0]
    
    classes = db.execute_query("SELECT * FROM classes WHERE user_id = %s", (user_id,))
    clubs = db.execute_query("SELECT * FROM clubs WHERE user_id = %s", (user_id,))
    assignments = db.execute_query("SELECT * FROM assignments WHERE user_id = %s AND completed = FALSE", (user_id,))
    
    grid = [[{"activity": "Free Time", "details": "Relax & Unwind"} for _ in range(24)] for _ in range(7)]
    
    for c in classes:
        slots = utils.get_slots(c['day_of_week'], c['start_time'], c['end_time'])
        for slot in slots:
            grid[slot // 24][slot % 24] = {"activity": "Class", "details": c['subject_name']}
            
    for cl in clubs:
        slots = utils.get_slots(cl['day_of_week'], cl['start_time'], cl['end_time'])
        for slot in slots:
            grid[slot // 24][slot % 24] = {"activity": "Club", "details": cl['club_name']}
            
    sleep_hours_limit = int(pref['sleep_hours'])
    for d in range(7):
        sleep_count = 0
        for h in [23, 0, 1, 2, 3, 4, 5, 6, 22, 7, 8]:
            if grid[d][h]['activity'] == 'Free Time' and sleep_count < sleep_hours_limit:
                grid[d][h] = {"activity": "Sleep", "details": "Rest & Recharge"}
                sleep_count += 1

    gym_hours_limit = int(pref['gym_hours'])
    if gym_hours_limit > 0:
        for d in [0, 2, 4, 5, 6]:
            gym_count = 0
            for h in [7, 8, 17, 18]:
                if gym_count < gym_hours_limit and grid[d][h]['activity'] == 'Free Time':
                    grid[d][h] = {"activity": "Gym", "details": "Workout Session"}
                    gym_count += 1

    week_start_date = get_week_start()
    warnings = []
    
    sorted_assignments = sorted(assignments, key=lambda x: x['deadline'])
    for a in sorted_assignments:
        rem_hours = a['estimated_hours']
        if a['deadline']:
            diff = a['deadline'] - week_start_date
            deadline_slot = max(0, min(167, int(diff.total_seconds() // 3600)))
        else:
            deadline_slot = 167
            
        for slot in range(deadline_slot):
            if rem_hours <= 0:
                break
            d, h = utils.slot_to_dh(slot)
            if grid[d][h]['activity'] == 'Free Time' and h < 23:
                consec_study = sum(1 for offset in [1, 2] if h >= offset and grid[d][h - offset]['activity'] == 'Study')
                if consec_study < 2:
                    grid[d][h] = {"activity": "Study", "details": f"Study: {a['title']}"}
                    rem_hours -= 1
        if rem_hours > 0:
            warnings.append(f"Could not fully schedule study for '{a['title']}' (missing {rem_hours} hours).")

    study_hours_limit = int(pref['study_hours_per_day'])
    for d in range(7):
        current_study_hours = sum(1 for h in range(24) if grid[d][h]['activity'] == 'Study')
        for h in range(24):
            if current_study_hours >= study_hours_limit:
                break
            if grid[d][h]['activity'] == 'Free Time' and h < 23:
                consec_study = sum(1 for offset in [1, 2] if h >= offset and grid[d][h - offset]['activity'] == 'Study')
                if consec_study < 2:
                    grid[d][h] = {"activity": "Study", "details": "General Study"}
                    current_study_hours += 1

    activity_counts = {act: sum(1 for d in range(7) for h in range(24) if grid[d][h]['activity'] == act) for act in ["Sleep", "Study", "Gym", "Free Time"]}
    
    score, recommendations_list = recommendation.predict_productivity(
        activity_counts["Sleep"] / 7.0,
        activity_counts["Study"] / 7.0,
        activity_counts["Gym"] / 7.0,
        len(assignments),
        len(classes),
        activity_counts["Free Time"] / 7.0
    )
    
    learner_profile = recommendation.get_learning_profile(user_id)
    
    db.execute_query(
        "INSERT INTO generated_schedules (user_id, schedule_json, productivity_score) VALUES (%s, %s, %s)",
        (user_id, json.dumps(grid), score),
        commit=True
    )
    
    suggestions = list(recommendations_list)
    if len(classes) + len(clubs) > 20:
        suggestions.append("Improve balance between academics and extracurriculars.")
    if warnings:
        suggestions.append("Reduce workload or request assignment deadline extensions.")
        
    return {
        "grid": grid,
        "score": score,
        "profile": learner_profile,
        "suggestions": suggestions,
        "warnings": warnings
    }, "Success"
