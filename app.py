import streamlit as st

# ── MUST be the very first Streamlit call ──────────────────────────────────────
st.set_page_config(page_title="FlowState", layout="wide")

from datetime import datetime, time
import pandas as pd
import json
import db, scheduler, analytics, utils, recommendation

# ── Database initialisation ────────────────────────────────────────────────────
try:
    db.init_db()
    db.seed_db()
except Exception as e:
    st.error(
        f"⚠️ **Could not connect to the database.**\n\n"
        f"Error: `{e}`\n\n"
        "If you are running on **Streamlit Cloud**, make sure you have added your "
        "database credentials under **App Settings → Secrets**."
    )
    st.stop()

st.title("⏱️ FlowState - Intelligent Academic Scheduling & Productivity Platform")

users = db.execute_query("SELECT id, name FROM users")
u_names = {u['name']: u['id'] for u in users}
sel_user = st.sidebar.selectbox("Student Profile", list(u_names.keys()) if u_names else ["Alice Smith"])
user_id = u_names[sel_user] if u_names else 1

page = st.sidebar.radio("Navigation", ["Dashboard", "Assignments", "Preferences", "Generate Timetable", "Analytics"])

def render_list(items, desc_fn, table):
    for item in items:
        if st.button(f"🗑️ Delete: {desc_fn(item)}", key=f"del_{table}_{item['id']}"):
            db.execute_query(f"DELETE FROM {table} WHERE id = %s", (item['id'],), commit=True)
            st.rerun()

if page == "Dashboard":
    st.header("📋 Schedule Inputs")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📚 Subjects")
        with st.form("subject_form", clear_on_submit=True):
            sub = st.text_input("Subject Name")
            if st.form_submit_button("Add Subject") and sub.strip():
                db.execute_query("INSERT INTO subjects (user_id, subject_name) VALUES (%s, %s)", (user_id, sub.strip()), commit=True)
                st.rerun()
        render_list(db.execute_query("SELECT * FROM subjects WHERE user_id = %s", (user_id,)), lambda x: x['subject_name'], "subjects")

    with col2:
        st.subheader("🏋️ Clubs")
        with st.form("club_form", clear_on_submit=True):
            name = st.text_input("Club Name")
            day = st.selectbox("Club Day", utils.DAYS)
            start = st.time_input("Club Start", time(16, 0))
            end = st.time_input("Club End", time(17, 30))
            if st.form_submit_button("Add Club") and name.strip():
                db.execute_query("INSERT INTO clubs (user_id, club_name, day_of_week, start_time, end_time) VALUES (%s, %s, %s, %s, %s)", (user_id, name.strip(), utils.DAYS.index(day), str(start), str(end)), commit=True)
                st.rerun()
        render_list(db.execute_query("SELECT * FROM clubs WHERE user_id = %s", (user_id,)), lambda x: f"{x['club_name']} ({utils.DAYS[x['day_of_week']]} {str(x['start_time'])[:5]}-{str(x['end_time'])[:5]})", "clubs")

    st.markdown("---")
    st.subheader("🏫 College Classes")
    subs = db.execute_query("SELECT * FROM subjects WHERE user_id = %s", (user_id,))
    c1, c2 = st.columns(2)
    with c1:
        if subs:
            with st.form("class_form", clear_on_submit=True):
                cl_sub = st.selectbox("Select Subject", [s['subject_name'] for s in subs])
                cl_day = st.selectbox("Class Day", utils.DAYS)
                cl_start = st.time_input("Class Start", time(9, 0))
                cl_end = st.time_input("Class End", time(10, 30))
                if st.form_submit_button("Add Class"):
                    db.execute_query("INSERT INTO classes (user_id, subject_name, day_of_week, start_time, end_time) VALUES (%s, %s, %s, %s, %s)", (user_id, cl_sub, utils.DAYS.index(cl_day), str(cl_start), str(cl_end)), commit=True)
                    st.rerun()
        else: st.info("Add a subject first.")
    with c2:
        render_list(db.execute_query("SELECT * FROM classes WHERE user_id = %s", (user_id,)), lambda x: f"{x['subject_name']} ({utils.DAYS[x['day_of_week']]} {str(x['start_time'])[:5]}-{str(x['end_time'])[:5]})", "classes")

elif page == "Assignments":
    st.header("📝 Assignments")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Add Assignment")
        with st.form("assignment_form", clear_on_submit=True):
            t = st.text_input("Title")
            dd = st.date_input("Deadline Date", datetime.now().date())
            dt = st.time_input("Deadline Time", time(23, 59))
            est = st.number_input("Est. Hours", 1, 40, 3)
            pri = st.slider("Priority (1-5)", 1, 5, 3)
            if st.form_submit_button("Save Assignment") and t.strip():
                db.execute_query("INSERT INTO assignments (user_id, title, deadline, estimated_hours, priority) VALUES (%s, %s, %s, %s, %s)", (user_id, t.strip(), datetime.combine(dd, dt).strftime("%Y-%m-%d %H:%M:%S"), int(est), int(pri)), commit=True)
                st.rerun()
    with c2:
        st.subheader("Active & Completed")
        for a in db.execute_query("SELECT * FROM assignments WHERE user_id = %s ORDER BY completed ASC, deadline ASC", (user_id,)):
            st.markdown(f"**{'✅' if a['completed'] else '⏳'} {a['title']}** (Priority {a['priority']})")
            st.write(f"Due: {a['deadline']} | Est: {a['estimated_hours']} hrs")
            if not a['completed']:
                if st.button("Complete ✅", key=f"c_{a['id']}"):
                    db.execute_query("UPDATE assignments SET completed = TRUE WHERE id = %s", (a['id'],), commit=True)
                    st.rerun()
                if st.button("Delete 🗑️", key=f"d_{a['id']}"):
                    db.execute_query("DELETE FROM assignments WHERE id = %s", (a['id'],), commit=True)
                    st.rerun()
            st.markdown("---")

elif page == "Preferences":
    st.header("⚙️ Preferences")
    p = db.execute_query("SELECT * FROM preferences WHERE user_id = %s", (user_id,))
    p = p[0] if p else {"sleep_hours": 8.0, "gym_hours": 1.0, "study_hours_per_day": 4.0, "preferred_study_time": "Night"}
    c1, c2 = st.columns(2)
    with c1:
        with st.form("preferences_form"):
            sl = st.slider("Sleep Goal (Hours)", 4.0, 10.0, float(p['sleep_hours']), 0.5)
            gy = st.slider("Gym Target (Hours)", 0.0, 3.0, float(p['gym_hours']), 0.5)
            st_h = st.slider("Study Target (Hours)", 1.0, 10.0, float(p['study_hours_per_day']), 0.5)
            pref = st.selectbox("Preferred Study Time", ["Morning", "Afternoon", "Night"], index=["Morning", "Afternoon", "Night"].index(p['preferred_study_time']))
            if st.form_submit_button("Save Preferences"):
                db.execute_query("INSERT INTO preferences (user_id, sleep_hours, gym_hours, study_hours_per_day, preferred_study_time) VALUES (%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE sleep_hours=VALUES(sleep_hours), gym_hours=VALUES(gym_hours), study_hours_per_day=VALUES(study_hours_per_day), preferred_study_time=VALUES(preferred_study_time)", (user_id, sl, gy, st_h, pref), commit=True)
                st.rerun()
    with c2:
        st.subheader("🤖 AI Learner Profile")
        try: st.info(f"Your learning profile: {recommendation.get_learning_profile(user_id)}")
        except Exception: st.warning("Seed profiles are initializing.")

elif page == "Generate Timetable":
    st.header("📅 Schedule Generation")
    if st.button("Generate Weekly Schedule"):
        res, msg = scheduler.generate_schedule(user_id)
        if res: st.success("Schedule generated!"); st.session_state["grid"] = res
        else: st.error(msg)
    if "grid" in st.session_state:
        res = st.session_state["grid"]
        df = pd.DataFrame(index=[utils.format_hour(h) for h in range(24)], columns=utils.DAYS)
        for d in range(7):
            for h in range(24):
                item = res["grid"][d][h]
                df.iloc[h, d] = f"{item['activity']}\n({item['details']})"
        st.dataframe(df, height=500, use_container_width=True)
        st.subheader("💡 Schedule AI Analysis")
        c1, c2 = st.columns(2)
        c1.metric("Learning Profile", res["profile"])
        c2.metric("Productivity Score", f"{res['score']}/100")
        if res["warnings"]:
            st.warning("⚠️ Constraints:")
            for w in res["warnings"]: st.write(f"- {w}")
        st.subheader("📈 Suggestions:")
        for idx, sug in enumerate(res["suggestions"]): st.write(f"{idx+1}. {sug}")

elif page == "Analytics":
    st.header("📊 Insights")
    latest = db.execute_query("SELECT schedule_json FROM generated_schedules WHERE user_id = %s ORDER BY created_at DESC LIMIT 1", (user_id,))
    if latest:
        stats = analytics.generate_analytics_data(user_id, json.loads(latest[0]['schedule_json']))
        c1, c2, c3 = st.columns(3)
        c1.metric("Weekly Study", f"{stats['weekly_study']} hrs")
        c2.metric("Weekly Free Time", f"{stats['free_time']} hrs")
        c3.metric("Completed Assignments", stats["completed_assignments"])
        ch1, ch2 = st.columns(2)
        ch1.plotly_chart(stats["fig_pie"], use_container_width=True)
        ch2.plotly_chart(stats["fig_bar"], use_container_width=True)
        ch3, ch4 = st.columns(2)
        ch3.plotly_chart(stats["fig_gauge"], use_container_width=True)
        ch4.plotly_chart(stats["fig_subj"], use_container_width=True)
    else: st.info("Please generate a timetable first.")
