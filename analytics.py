import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import db

def generate_analytics_data(user_id, schedule_grid):
    counts = {"Sleep": 0, "Gym": 0, "Study": 0, "Class": 0, "Club": 0, "Free Time": 0}
    daily_stats = []
    
    subjects = db.execute_query("SELECT subject_name FROM subjects WHERE user_id = %s", (user_id,))
    subj_list = [s['subject_name'] for s in subjects]
    subj_study = {s: 0 for s in subj_list}
    subj_study["General/Other"] = 0

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for d_idx, day_name in enumerate(days):
        day_counts = {k: 0 for k in counts.keys()}
        for h in range(24):
            act = schedule_grid[d_idx][h]["activity"]
            details = schedule_grid[d_idx][h].get("details", "")
            if act in counts:
                counts[act] += 1
                day_counts[act] += 1
            if act == "Study":
                matched = next((s for s in subj_list if s.lower() in details.lower()), None)
                if matched:
                    subj_study[matched] += 1
                else:
                    subj_study["General/Other"] += 1
                    
        for act, hrs in day_counts.items():
            daily_stats.append({"Day": day_name, "Activity": act, "Hours": hrs})
            
    fig_pie = px.pie(
        names=list(counts.keys()), values=list(counts.values()),
        title="Weekly Time Distribution", hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    
    fig_bar = px.bar(
        pd.DataFrame(daily_stats), x="Day", y="Hours", color="Activity",
        title="Daily Time Allocation Breakdown",
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    
    latest = db.execute_query(
        "SELECT productivity_score FROM generated_schedules WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
        (user_id,)
    )
    score = latest[0]['productivity_score'] if latest else 0.0
    
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        title={'text': "Predicted Productivity Score"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "#2ECC71"},
            'steps': [
                {'range': [0, 50], 'color': "#FF7675"},
                {'range': [50, 80], 'color': "#FFEAA7"},
                {'range': [80, 100], 'color': "#55EFC4"}
            ]
        }
    ))
    fig_gauge.update_layout(height=280)
    
    fig_subj = px.bar(
        pd.DataFrame(list(subj_study.items()), columns=["Subject", "Study Hours"]),
        x="Subject", y="Study Hours", title="Study Time per Subject",
        color="Study Hours", color_continuous_scale="Purples"
    )
    
    comp = db.execute_query("SELECT COUNT(*) as c FROM assignments WHERE user_id = %s AND completed = TRUE", (user_id,))
    
    return {
        "weekly_study": counts["Study"],
        "free_time": counts["Free Time"],
        "completed_assignments": comp[0]['c'] if comp else 0,
        "fig_pie": fig_pie,
        "fig_bar": fig_bar,
        "fig_gauge": fig_gauge,
        "fig_subj": fig_subj
    }
