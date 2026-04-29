import os
import csv
import json
import io
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="FitAI Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS — Dark Cyber Theme
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Inter:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0a0e1a;
    color: #e0e6f0;
}

h1, h2, h3 { font-family: 'Rajdhani', sans-serif !important; letter-spacing: 1px; }

.stApp { background: linear-gradient(135deg, #0a0e1a 0%, #0d1426 50%, #0a1020 100%); }

/* Metric cards */
[data-testid="metric-container"] {
    background: linear-gradient(145deg, #111827, #1a2235);
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 4px 20px rgba(0,120,255,0.08);
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #38bdf8 !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 2rem !important;
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    color: #94a3b8 !important;
    font-size: 0.8rem !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1426 0%, #0a1020 100%);
    border-right: 1px solid #1e3a5f;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #1d4ed8, #0ea5e9);
    color: white;
    border: none;
    border-radius: 8px;
    font-family: 'Rajdhani', sans-serif;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 0.5rem 1.5rem;
    transition: all 0.2s ease;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(14,165,233,0.4);
}

/* Inputs */
.stTextInput input, .stNumberInput input, .stSelectbox select {
    background: #111827 !important;
    border: 1px solid #1e3a5f !important;
    color: #e0e6f0 !important;
    border-radius: 8px !important;
}

/* Info/warning boxes */
.stInfo { background: rgba(14,165,233,0.08); border-left: 3px solid #0ea5e9; border-radius: 4px; }
.stSuccess { background: rgba(16,185,129,0.08); border-left: 3px solid #10b981; }
.stWarning { background: rgba(245,158,11,0.08); border-left: 3px solid #f59e0b; }

/* Chat messages */
[data-testid="stChatMessage"] {
    background: #111827;
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    margin-bottom: 8px;
}

/* Section headers */
.section-header {
    background: linear-gradient(90deg, #1d4ed8 0%, transparent 100%);
    padding: 8px 16px;
    border-radius: 8px;
    margin-bottom: 16px;
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.2rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #ffffff;
}

/* Streak badge */
.streak-badge {
    background: linear-gradient(135deg, #f59e0b, #ef4444);
    color: white;
    padding: 6px 16px;
    border-radius: 20px;
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 1.1rem;
    display: inline-block;
}

/* Progress bar custom */
.goal-progress {
    background: #1a2235;
    border-radius: 8px;
    padding: 12px 16px;
    border: 1px solid #1e3a5f;
    margin-bottom: 8px;
}

/* Food log table */
.food-log-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid #1e3a5f;
    font-size: 0.9rem;
}

/* Divider */
hr { border-color: #1e3a5f !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
def initialize_session_state():
    defaults = {
        "profile": {
            "name": "",
            "age": 20,
            "weight": 70.0,
            "height": 170.0,
            "goal": "Maintain",
            "gender": "Male",
            "activity_level": "Moderately Active",
        },
        "daily_data": None,
        "daily_history": [],
        "weight_history": [],
        "bmi_history": [],
        "chat_history": [],
        "food_log": [],          # [{name, calories, protein, carbs, fat}]
        "streak": 0,
        "last_log_date": None,
        "workout_plan": "",
        "water_goal": 8,
        "calorie_goal": 2000,
        "last_food_search": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ─────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────
def estimate_calories(workout_type, duration, weight_kg=70):
    """More accurate MET-based calorie burn estimate."""
    met_values = {
        "Running": 9.8,
        "Gym / Weight Training": 5.0,
        "Yoga": 2.5,
        "Walking": 3.5,
        "Cycling": 7.5,
        "Swimming": 8.0,
        "HIIT": 12.0,
        "Jump Rope": 11.0,
        "Home Workout (Bodyweight)": 5.5,
        "Push-ups / Pull-ups": 5.0,
        "Stretching / Flexibility": 2.3,
        "Dance / Zumba (Home)": 7.0,
        "Stair Climbing": 8.0,
    }
    met = met_values.get(workout_type, 4.0)
    return round(met * weight_kg * (duration / 60))


def calculate_bmi(weight, height_cm):
    height_m = height_cm / 100
    if height_m <= 0:
        return 0
    return round(weight / (height_m ** 2), 1)


def get_bmi_category(bmi):
    if bmi < 18.5: return "Underweight", "#f59e0b"
    if bmi < 25:   return "Normal ✓",    "#10b981"
    if bmi < 30:   return "Overweight",  "#f59e0b"
    return "Obese",  "#ef4444"


def calculate_bmr(weight, height_cm, age, gender):
    """Mifflin-St Jeor Equation."""
    if gender == "Male":
        return round(10 * weight + 6.25 * height_cm - 5 * age + 5)
    return round(10 * weight + 6.25 * height_cm - 5 * age - 161)


def calculate_tdee(bmr, activity_level):
    multipliers = {
        "Sedentary": 1.2,
        "Lightly Active": 1.375,
        "Moderately Active": 1.55,
        "Very Active": 1.725,
        "Extremely Active": 1.9,
    }
    return round(bmr * multipliers.get(activity_level, 1.55))


def update_streak():
    today = str(date.today())
    yesterday = str(date.today() - timedelta(days=1))
    last = st.session_state.last_log_date

    if last == today:
        pass  # already logged today
    elif last == yesterday:
        st.session_state.streak += 1
        st.session_state.last_log_date = today
    else:
        st.session_state.streak = 1
        st.session_state.last_log_date = today


# ─────────────────────────────────────────────
# API FUNCTIONS
# ─────────────────────────────────────────────
def search_food_api(query):
    """Search Open Food Facts API — no API key needed."""
    try:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            "search_terms": query,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 5,
            "fields": "product_name,nutriments",
        }
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()
        results = []
        for product in data.get("products", []):
            name = product.get("product_name", "").strip()
            n = product.get("nutriments", {})
            cal = n.get("energy-kcal_100g", 0) or 0
            protein = n.get("proteins_100g", 0) or 0
            carbs = n.get("carbohydrates_100g", 0) or 0
            fat = n.get("fat_100g", 0) or 0
            if name and cal > 0:
                results.append({
                    "name": name[:50],
                    "calories_per_100g": round(cal),
                    "protein": round(protein, 1),
                    "carbs": round(carbs, 1),
                    "fat": round(fat, 1),
                })
        return results[:5]
    except Exception:
        return []


def get_ai_reply(user_input, system_prompt=None):
    """Call Groq API for AI fitness advice."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "⚠️ Add GROQ_API_KEY to your .env file to enable AI features."

    profile = st.session_state.profile
    context = (
        f"User: {profile['name'] or 'User'}, Age: {profile['age']}, "
        f"Weight: {profile['weight']}kg, Height: {profile['height']}cm, "
        f"Goal: {profile['goal']}, Gender: {profile['gender']}, "
        f"Activity: {profile['activity_level']}."
    )
    sys = system_prompt or (
        "You are FitAI Pro — a professional fitness coach and nutritionist. "
        "Give concise, personalized, evidence-based advice. Use bullet points when listing. "
        f"User profile: {context}"
    )

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": sys},
                    {"role": "user", "content": user_input},
                ],
                "max_tokens": 600,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ AI unavailable: {str(e)[:80]}"


def generate_workout_plan():
    """AI-generated personalized weekly workout plan."""
    profile = st.session_state.profile
    prompt = (
        f"Create a 7-day workout plan for someone aged {profile['age']}, "
        f"weight {profile['weight']}kg, goal: {profile['goal']}, "
        f"activity level: {profile['activity_level']}. "
        "For each day include: exercise name, sets/reps or duration, rest time. "
        "Format: Day 1: [Day Name] - [Focus Area] then bullet points."
    )
    return get_ai_reply(prompt, system_prompt="You are an elite personal trainer. Create structured, progressive workout plans.")


# ─────────────────────────────────────────────
# SIDEBAR — Profile + Stats
# ─────────────────────────────────────────────
def show_sidebar():
    with st.sidebar:
        st.markdown('<div class="section-header">⚡ FitAI Pro</div>', unsafe_allow_html=True)

        # Streak display
        streak = st.session_state.streak
        st.markdown(
            f'<div style="text-align:center; margin-bottom:16px;">'
            f'<span class="streak-badge">🔥 {streak} Day Streak</span></div>',
            unsafe_allow_html=True,
        )

        st.markdown("### 👤 Profile")
        p = st.session_state.profile
        p["name"] = st.text_input("Name", value=p["name"])
        p["gender"] = st.selectbox("Gender", ["Male", "Female"], index=0 if p["gender"] == "Male" else 1)

        col1, col2 = st.columns(2)
        with col1:
            p["age"] = st.number_input("Age", 10, 100, p["age"])
            p["weight"] = st.number_input("Weight (kg)", 20.0, 300.0, float(p["weight"]), step=0.5)
        with col2:
            p["height"] = st.number_input("Height (cm)", 50.0, 250.0, float(p["height"]), step=0.5)
            p["goal"] = st.selectbox("Goal", ["Weight Loss", "Muscle Gain", "Maintain"],
                                     index=["Weight Loss", "Muscle Gain", "Maintain"].index(p["goal"]))

        p["activity_level"] = st.selectbox("Activity Level", [
            "Sedentary", "Lightly Active", "Moderately Active", "Very Active", "Extremely Active"
        ], index=2)

        # Calculated stats
        bmi = calculate_bmi(p["weight"], p["height"])
        bmr = calculate_bmr(p["weight"], p["height"], p["age"], p["gender"])
        tdee = calculate_tdee(bmr, p["activity_level"])
        bmi_cat, bmi_color = get_bmi_category(bmi)

        st.markdown("---")
        st.markdown("### 📊 Your Stats")
        st.metric("BMI", bmi, help="Body Mass Index")
        st.markdown(f'<span style="color:{bmi_color}; font-weight:600;">● {bmi_cat}</span>', unsafe_allow_html=True)
        st.metric("BMR", f"{bmr} kcal", help="Basal Metabolic Rate")
        st.metric("TDEE", f"{tdee} kcal", help="Total Daily Energy Expenditure")

        # Daily calorie goal based on goal
        if p["goal"] == "Weight Loss":
            st.session_state.calorie_goal = tdee - 500
        elif p["goal"] == "Muscle Gain":
            st.session_state.calorie_goal = tdee + 300
        else:
            st.session_state.calorie_goal = tdee

        st.markdown("---")

        # Export button
        if st.button("📥 Export Data (CSV)"):
            export_data()


# ─────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────
def export_data():
    history = st.session_state.daily_history
    if not history:
        st.sidebar.warning("No data to export yet.")
        return

    df = pd.DataFrame(history)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    st.sidebar.download_button(
        label="⬇️ Download CSV",
        data=csv_buffer.getvalue(),
        file_name=f"fitai_export_{date.today()}.csv",
        mime="text/csv",
    )


# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
def show_daily_tracker_tab():
    st.markdown('<div class="section-header">📋 Daily Tracker</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🏋️ Workout")
        workout_type = st.selectbox("Workout Type", [
            # Home (No Equipment)
            "Home Workout (Bodyweight)",
            "Push-ups / Pull-ups",
            "Stretching / Flexibility",
            "Dance / Zumba (Home)",
            "Stair Climbing",
            "Jump Rope",
            "HIIT",
            "Yoga",
            # Outdoor
            "Running",
            "Walking",
            "Cycling",
            # Gym
            "Gym / Weight Training",
            "Swimming",
        ])
        home_workouts = {
            "Home Workout (Bodyweight)", "Push-ups / Pull-ups",
            "Stretching / Flexibility", "Dance / Zumba (Home)",
            "Stair Climbing", "Jump Rope", "HIIT", "Yoga"
        }
        if workout_type in home_workouts:
            st.success("🏠 No equipment needed!")
        duration = st.slider("Duration (minutes)", 0, 180, 30)
        weight_for_calc = st.session_state.profile["weight"]
        calories_burned = estimate_calories(workout_type, duration, weight_for_calc)
        st.info(f"🔥 Estimated burn: **{calories_burned} kcal** (MET-based)")

    with col2:
        st.markdown("#### 💤 Wellness")
        water = st.slider("💧 Water (glasses)", 0, 20, 8)
        sleep = st.slider("😴 Sleep (hours)", 0, 12, 7)
        mood = st.select_slider("😊 Mood", ["😞 Terrible", "😕 Bad", "😐 Okay", "🙂 Good", "😄 Great"], value="😐 Okay")
        steps = st.number_input("👟 Steps (optional)", min_value=0, max_value=100000, value=0, step=500)

    # Water goal progress
    water_goal = st.session_state.water_goal
    water_pct = min(water / water_goal * 100, 100)
    st.markdown(f"**💧 Water Goal Progress:** {water}/{water_goal} glasses")
    st.progress(int(water_pct))

    if st.button("💾 Save Today's Data", use_container_width=True):
        p = st.session_state.profile
        bmi = calculate_bmi(p["weight"], p["height"])
        total_food_cals = sum(f["calories"] for f in st.session_state.food_log)

        entry = {
            "date": str(date.today()),
            "workout_type": workout_type,
            "duration": duration,
            "calories_burned": calories_burned,
            "water": water,
            "sleep": sleep,
            "mood": mood,
            "steps": steps,
            "food_calories": total_food_cals,
            "net_calories": total_food_cals - calories_burned,
            "weight": p["weight"],
            "bmi": bmi,
        }

        st.session_state.daily_data = entry
        st.session_state.daily_history.append(entry)
        st.session_state.weight_history.append({"date": str(date.today()), "weight": p["weight"]})
        st.session_state.bmi_history.append({"date": str(date.today()), "bmi": bmi})
        update_streak()
        st.success(f"✅ Day logged! 🔥 Streak: {st.session_state.streak} days")
        st.balloons()



# ─────────────────────────────────────────────
# BUILT-IN FOOD DATABASE
# ─────────────────────────────────────────────
VEG_FOODS = {
    "🌾 Grains & Cereals": [
        {"name": "White Rice (cooked)", "cal": 130, "protein": 2.7, "carbs": 28.2, "fat": 0.3},
        {"name": "Brown Rice (cooked)", "cal": 111, "protein": 2.6, "carbs": 23.0, "fat": 0.9},
        {"name": "Roti / Chapati (1 piece)", "cal": 104, "protein": 3.1, "carbs": 18.0, "fat": 2.5},
        {"name": "Oats (cooked)", "cal": 71, "protein": 2.5, "carbs": 12.0, "fat": 1.5},
        {"name": "Poha (cooked)", "cal": 110, "protein": 2.0, "carbs": 23.0, "fat": 1.0},
        {"name": "Idli (1 piece)", "cal": 39, "protein": 1.8, "carbs": 8.0, "fat": 0.2},
        {"name": "Dosa (1 piece)", "cal": 133, "protein": 3.5, "carbs": 25.0, "fat": 2.5},
        {"name": "Bread (1 slice)", "cal": 79, "protein": 2.7, "carbs": 15.0, "fat": 1.0},
        {"name": "Upma (cooked)", "cal": 135, "protein": 3.0, "carbs": 22.0, "fat": 4.0},
    ],
    "🥦 Vegetables": [
        {"name": "Spinach (cooked)", "cal": 23, "protein": 2.5, "carbs": 3.6, "fat": 0.3},
        {"name": "Broccoli (cooked)", "cal": 35, "protein": 2.4, "carbs": 7.2, "fat": 0.4},
        {"name": "Potato (boiled)", "cal": 87, "protein": 1.9, "carbs": 20.0, "fat": 0.1},
        {"name": "Sweet Potato (boiled)", "cal": 90, "protein": 2.0, "carbs": 21.0, "fat": 0.1},
        {"name": "Carrot (raw)", "cal": 41, "protein": 0.9, "carbs": 10.0, "fat": 0.2},
        {"name": "Tomato (raw)", "cal": 18, "protein": 0.9, "carbs": 3.9, "fat": 0.2},
        {"name": "Onion (raw)", "cal": 40, "protein": 1.1, "carbs": 9.3, "fat": 0.1},
        {"name": "Cauliflower (cooked)", "cal": 25, "protein": 1.9, "carbs": 5.0, "fat": 0.3},
        {"name": "Peas (cooked)", "cal": 84, "protein": 5.4, "carbs": 15.6, "fat": 0.2},
        {"name": "Bhindi / Okra (cooked)", "cal": 33, "protein": 1.9, "carbs": 7.5, "fat": 0.2},
    ],
    "🫘 Dal & Legumes": [
        {"name": "Moong Dal (cooked)", "cal": 104, "protein": 7.0, "carbs": 18.0, "fat": 0.4},
        {"name": "Masoor Dal (cooked)", "cal": 116, "protein": 9.0, "carbs": 20.0, "fat": 0.4},
        {"name": "Chana Dal (cooked)", "cal": 164, "protein": 9.0, "carbs": 27.0, "fat": 2.7},
        {"name": "Rajma / Kidney Beans", "cal": 127, "protein": 8.7, "carbs": 22.8, "fat": 0.5},
        {"name": "Chole / Chickpeas", "cal": 164, "protein": 8.9, "carbs": 27.4, "fat": 2.6},
        {"name": "Black Chana (cooked)", "cal": 164, "protein": 8.9, "carbs": 27.0, "fat": 2.6},
        {"name": "Soybean (cooked)", "cal": 173, "protein": 16.6, "carbs": 9.9, "fat": 9.0},
        {"name": "Tofu (firm)", "cal": 76, "protein": 8.0, "carbs": 1.9, "fat": 4.2},
    ],
    "🍎 Fruits": [
        {"name": "Banana (1 medium)", "cal": 89, "protein": 1.1, "carbs": 23.0, "fat": 0.3},
        {"name": "Apple (1 medium)", "cal": 52, "protein": 0.3, "carbs": 14.0, "fat": 0.2},
        {"name": "Mango (100g)", "cal": 60, "protein": 0.8, "carbs": 15.0, "fat": 0.4},
        {"name": "Orange (1 medium)", "cal": 47, "protein": 0.9, "carbs": 12.0, "fat": 0.1},
        {"name": "Papaya (100g)", "cal": 43, "protein": 0.5, "carbs": 11.0, "fat": 0.3},
        {"name": "Guava (100g)", "cal": 68, "protein": 2.6, "carbs": 14.0, "fat": 1.0},
        {"name": "Grapes (100g)", "cal": 69, "protein": 0.7, "carbs": 18.0, "fat": 0.2},
        {"name": "Watermelon (100g)", "cal": 30, "protein": 0.6, "carbs": 8.0, "fat": 0.2},
    ],
    "🥛 Dairy": [
        {"name": "Whole Milk (200ml)", "cal": 122, "protein": 6.4, "carbs": 9.6, "fat": 6.6},
        {"name": "Curd / Dahi (100g)", "cal": 98, "protein": 3.5, "carbs": 3.4, "fat": 4.3},
        {"name": "Paneer (100g)", "cal": 265, "protein": 18.3, "carbs": 1.2, "fat": 20.8},
        {"name": "Greek Yogurt (100g)", "cal": 59, "protein": 10.0, "carbs": 3.6, "fat": 0.4},
        {"name": "Butter (1 tsp)", "cal": 36, "protein": 0.0, "carbs": 0.0, "fat": 4.1},
        {"name": "Ghee (1 tsp)", "cal": 45, "protein": 0.0, "carbs": 0.0, "fat": 5.0},
        {"name": "Cheese Slice (1 slice)", "cal": 79, "protein": 4.5, "carbs": 1.0, "fat": 6.3},
    ],
    "🥜 Nuts & Seeds": [
        {"name": "Almonds (10 pieces)", "cal": 70, "protein": 2.5, "carbs": 2.5, "fat": 6.0},
        {"name": "Walnuts (10g)", "cal": 65, "protein": 1.5, "carbs": 1.4, "fat": 6.5},
        {"name": "Peanuts (30g)", "cal": 170, "protein": 7.7, "carbs": 6.0, "fat": 14.0},
        {"name": "Cashews (10 pieces)", "cal": 90, "protein": 2.5, "carbs": 5.0, "fat": 7.0},
        {"name": "Chia Seeds (1 tbsp)", "cal": 58, "protein": 2.0, "carbs": 5.0, "fat": 3.7},
        {"name": "Flax Seeds (1 tbsp)", "cal": 55, "protein": 1.9, "carbs": 3.0, "fat": 4.3},
    ],
}

NON_VEG_FOODS = {
    "🍗 Chicken & Poultry": [
        {"name": "Chicken Breast (grilled, 100g)", "cal": 165, "protein": 31.0, "carbs": 0.0, "fat": 3.6},
        {"name": "Chicken Thigh (cooked, 100g)", "cal": 209, "protein": 26.0, "carbs": 0.0, "fat": 11.0},
        {"name": "Chicken Curry (100g)", "cal": 150, "protein": 14.0, "carbs": 5.0, "fat": 8.5},
        {"name": "Chicken Tikka (100g)", "cal": 172, "protein": 22.0, "carbs": 4.0, "fat": 7.0},
        {"name": "Boiled Chicken (100g)", "cal": 143, "protein": 27.0, "carbs": 0.0, "fat": 3.0},
        {"name": "Egg (1 whole, boiled)", "cal": 78, "protein": 6.3, "carbs": 0.6, "fat": 5.3},
        {"name": "Egg White (1 piece)", "cal": 17, "protein": 3.6, "carbs": 0.2, "fat": 0.1},
        {"name": "Egg Omelette (2 eggs)", "cal": 190, "protein": 13.0, "carbs": 1.5, "fat": 14.0},
    ],
    "🐟 Fish & Seafood": [
        {"name": "Salmon (cooked, 100g)", "cal": 208, "protein": 20.0, "carbs": 0.0, "fat": 13.0},
        {"name": "Tuna (canned, 100g)", "cal": 116, "protein": 26.0, "carbs": 0.0, "fat": 1.0},
        {"name": "Rohu Fish (cooked, 100g)", "cal": 97, "protein": 16.6, "carbs": 0.0, "fat": 2.7},
        {"name": "Pomfret (cooked, 100g)", "cal": 96, "protein": 17.0, "carbs": 0.0, "fat": 2.9},
        {"name": "Prawns / Shrimp (cooked, 100g)", "cal": 99, "protein": 24.0, "carbs": 0.2, "fat": 0.3},
        {"name": "Fish Curry (100g)", "cal": 130, "protein": 14.0, "carbs": 4.0, "fat": 6.5},
        {"name": "Sardines (100g)", "cal": 208, "protein": 24.6, "carbs": 0.0, "fat": 11.5},
    ],
    "🥩 Mutton & Red Meat": [
        {"name": "Mutton Curry (100g)", "cal": 195, "protein": 16.0, "carbs": 5.0, "fat": 12.5},
        {"name": "Mutton Keema (100g)", "cal": 260, "protein": 18.0, "carbs": 3.0, "fat": 19.0},
        {"name": "Lamb Chops (cooked, 100g)", "cal": 294, "protein": 25.0, "carbs": 0.0, "fat": 21.0},
        {"name": "Beef (lean, cooked, 100g)", "cal": 215, "protein": 26.0, "carbs": 0.0, "fat": 12.0},
        {"name": "Pork (lean, cooked, 100g)", "cal": 242, "protein": 27.0, "carbs": 0.0, "fat": 14.0},
    ],
    "🍳 Egg-Based Dishes": [
        {"name": "Egg Bhurji (2 eggs)", "cal": 200, "protein": 14.0, "carbs": 3.0, "fat": 15.0},
        {"name": "Scrambled Eggs (2 eggs)", "cal": 182, "protein": 12.0, "carbs": 1.5, "fat": 14.0},
        {"name": "Egg Curry (1 egg)", "cal": 145, "protein": 8.0, "carbs": 5.0, "fat": 10.0},
        {"name": "Egg Sandwich (1)", "cal": 235, "protein": 13.0, "carbs": 24.0, "fat": 9.0},
    ],
}


def show_nutrition_tab():
    st.markdown('<div class="section-header">🥗 Nutrition Tracker</div>', unsafe_allow_html=True)

    # Mode selector
    mode = st.radio(
        "How do you want to add food?",
        ["🟢 Veg Database", "🔴 Non-Veg Database", "✏️ Manual Entry"],
        horizontal=True,
    )

    left_col, right_col = st.columns([2, 1])

    with left_col:
        # ── VEG DATABASE ──────────────────────────────
        if mode == "🟢 Veg Database":
            st.markdown("### 🟢 Vegetarian Foods")
            category = st.selectbox("Select Category", list(VEG_FOODS.keys()), key="veg_cat")
            foods = VEG_FOODS[category]

            st.markdown(f"**{category}** — per 100g unless stated")
            st.markdown("---")

            for food in foods:
                c1, c2, c3, c4, c5, c6 = st.columns([3, 1, 1, 1, 1, 1])
                c1.markdown(f"**{food['name']}**")
                c2.markdown(f"🔥 **{food['cal']}**")
                c3.markdown(f"P: {food['protein']}g")
                c4.markdown(f"C: {food['carbs']}g")
                c5.markdown(f"F: {food['fat']}g")
                if c6.button("➕", key=f"veg_{food['name']}"):
                    st.session_state.food_log.append({
                        "name": food["name"],
                        "type": "🟢 Veg",
                        "portion_g": 100,
                        "calories": food["cal"],
                        "protein": food["protein"],
                        "carbs": food["carbs"],
                        "fat": food["fat"],
                    })
                    st.success(f"✅ Added: {food['name']}")
                    st.rerun()

        # ── NON-VEG DATABASE ──────────────────────────
        elif mode == "🔴 Non-Veg Database":
            st.markdown("### 🔴 Non-Vegetarian Foods")
            category = st.selectbox("Select Category", list(NON_VEG_FOODS.keys()), key="nonveg_cat")
            foods = NON_VEG_FOODS[category]

            st.markdown(f"**{category}** — per 100g unless stated")
            st.markdown("---")

            for food in foods:
                c1, c2, c3, c4, c5, c6 = st.columns([3, 1, 1, 1, 1, 1])
                c1.markdown(f"**{food['name']}**")
                c2.markdown(f"🔥 **{food['cal']}**")
                c3.markdown(f"P: {food['protein']}g")
                c4.markdown(f"C: {food['carbs']}g")
                c5.markdown(f"F: {food['fat']}g")
                if c6.button("➕", key=f"nonveg_{food['name']}"):
                    st.session_state.food_log.append({
                        "name": food["name"],
                        "type": "🔴 Non-Veg",
                        "portion_g": 100,
                        "calories": food["cal"],
                        "protein": food["protein"],
                        "carbs": food["carbs"],
                        "fat": food["fat"],
                    })
                    st.success(f"✅ Added: {food['name']}")
                    st.rerun()

        # ── MANUAL ENTRY ──────────────────────────────
        elif mode == "✏️ Manual Entry":
            st.markdown("### ✏️ Add Custom Food")
            food_type = st.radio("Food Type", ["🟢 Veg", "🔴 Non-Veg"], horizontal=True, key="manual_type")

            mc1, mc2 = st.columns(2)
            with mc1:
                manual_name = st.text_input("Food Name", placeholder="e.g. Dal Makhani", key="manual_name")
                manual_cal = st.number_input("Calories (kcal)", 0, 5000, 0, key="manual_cal")
                manual_portion = st.number_input("Portion (g)", 0, 2000, 100, step=10, key="manual_portion")
            with mc2:
                manual_protein = st.number_input("Protein (g)", 0.0, 500.0, 0.0, step=0.1, key="manual_protein")
                manual_carbs = st.number_input("Carbs (g)", 0.0, 500.0, 0.0, step=0.1, key="manual_carbs")
                manual_fat = st.number_input("Fat (g)", 0.0, 500.0, 0.0, step=0.1, key="manual_fat")

            if st.button("➕ Add to Food Log", use_container_width=True):
                if manual_name.strip():
                    st.session_state.food_log.append({
                        "name": manual_name.strip(),
                        "type": food_type,
                        "portion_g": manual_portion,
                        "calories": manual_cal,
                        "protein": manual_protein,
                        "carbs": manual_carbs,
                        "fat": manual_fat,
                    })
                    st.success(f"✅ Added: {manual_name}")
                    st.rerun()
                else:
                    st.warning("Please enter a food name.")

    # ── RIGHT PANEL: Today's Summary ─────────────────
    with right_col:
        st.markdown("#### 📊 Today's Intake")
        if st.session_state.food_log:
            total_cal = sum(f["calories"] for f in st.session_state.food_log)
            total_protein = sum(f["protein"] for f in st.session_state.food_log)
            total_carbs = sum(f["carbs"] for f in st.session_state.food_log)
            total_fat = sum(f["fat"] for f in st.session_state.food_log)
            calorie_goal = st.session_state.calorie_goal

            st.metric("Total Calories", f"{total_cal} kcal", f"{total_cal - calorie_goal:+d} vs goal")
            st.metric("Protein", f"{total_protein}g")
            st.metric("Carbs", f"{total_carbs}g")
            st.metric("Fat", f"{total_fat}g")

            # Veg vs Non-Veg split
            veg_cal = sum(f["calories"] for f in st.session_state.food_log if f.get("type", "") == "🟢 Veg")
            nonveg_cal = sum(f["calories"] for f in st.session_state.food_log if f.get("type", "") == "🔴 Non-Veg")
            manual_cal_total = sum(f["calories"] for f in st.session_state.food_log if f.get("type", "") not in ["🟢 Veg", "🔴 Non-Veg"])

            if total_cal > 0:
                fig_split = go.Figure(data=[go.Pie(
                    labels=["🟢 Veg", "🔴 Non-Veg", "✏️ Manual"],
                    values=[veg_cal, nonveg_cal, manual_cal_total],
                    hole=0.5,
                    marker_colors=["#10b981", "#ef4444", "#94a3b8"],
                )])
                fig_split.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#e0e6f0", margin=dict(l=0, r=0, t=20, b=0),
                    height=180, title="Veg vs Non-Veg",
                    title_font_color="#e0e6f0", showlegend=True,
                    legend=dict(font=dict(color="#e0e6f0", size=10)),
                )
                st.plotly_chart(fig_split, use_container_width=True)

            # Macro pie chart
            fig = go.Figure(data=[go.Pie(
                labels=["Protein", "Carbs", "Fat"],
                values=[max(total_protein * 4, 0.1), max(total_carbs * 4, 0.1), max(total_fat * 9, 0.1)],
                hole=0.5,
                marker_colors=["#38bdf8", "#10b981", "#f59e0b"],
            )])
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e0e6f0", margin=dict(l=0, r=0, t=20, b=0),
                height=180, title="Macros", title_font_color="#e0e6f0",
                showlegend=True, legend=dict(font=dict(color="#e0e6f0", size=10)),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Calorie goal progress
            pct = min(total_cal / max(calorie_goal, 1), 1.0)
            st.markdown(f"**Goal: {total_cal}/{calorie_goal} kcal**")
            st.progress(pct)

            if st.button("🗑️ Clear Food Log", use_container_width=True):
                st.session_state.food_log = []
                st.rerun()
        else:
            st.info("Add food from the database or manually to see your nutrition breakdown.")

    # ── Food Log Table ────────────────────────────────
    if st.session_state.food_log:
        st.markdown("---")
        st.markdown("#### 📋 Today's Food Log")
        log_df = pd.DataFrame(st.session_state.food_log)
        # Reorder columns nicely
        cols_order = ["name", "type", "portion_g", "calories", "protein", "carbs", "fat"]
        cols_present = [c for c in cols_order if c in log_df.columns]
        st.dataframe(log_df[cols_present], use_container_width=True, hide_index=True)


def show_analytics_tab():
    st.markdown('<div class="section-header">📈 Analytics & Progress</div>', unsafe_allow_html=True)

    history = st.session_state.daily_history
    if len(history) < 1:
        st.info("Save at least 1 day of data to see analytics.")
        return

    # ── Deduplicate: keep last entry per date ──
    df = pd.DataFrame(history)
    df["date"] = pd.to_datetime(df["date"]).dt.date  # strip time, keep only date
    df = df.drop_duplicates(subset="date", keep="last").reset_index(drop=True)
    df["day_label"] = df["date"].astype(str)  # clean string label for x-axis

    # ── Summary metrics ──
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("📅 Days Tracked", len(df))
    col2.metric("😴 Avg Sleep", f"{df['sleep'].mean():.1f}h" if 'sleep' in df.columns else "—")
    col3.metric("🔥 Avg Burned", f"{df['calories_burned'].mean():.0f} kcal" if 'calories_burned' in df.columns else "—")
    col4.metric("💧 Avg Water", f"{df['water'].mean():.1f}g" if 'water' in df.columns else "—")
    col5.metric("⚖️ Latest Weight", f"{df['weight'].iloc[-1]} kg" if 'weight' in df.columns else "—")

    if len(df) < 1:
        st.info("Keep logging daily to see your trends.")
        return

    st.markdown("---")

    # ── SINGLE MASTER DASHBOARD CHART ──
    st.markdown("#### 📊 Your Fitness Dashboard")

    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            "⚖️ Weight (kg)",
            "🧮 BMI Trend",
            "🔥 Calories Burned vs Food Intake",
            "💧 Water Intake (glasses)",
            "😴 Sleep Hours",
            "🏃 Workout Duration (min)",
        ),
        vertical_spacing=0.12,
        horizontal_spacing=0.08,
    )

    x = df["day_label"]

    # ── Row 1: Weight ──
    fig.add_trace(go.Scatter(
        x=x, y=df["weight"], mode="lines+markers+text",
        name="Weight", line=dict(color="#38bdf8", width=2.5),
        marker=dict(size=7, color="#38bdf8"),
        text=[f"{v}kg" for v in df["weight"]], textposition="top center",
        textfont=dict(size=9, color="#38bdf8"),
    ), row=1, col=1)

    # ── Row 1: BMI ──
    bmi_vals = df["bmi"] if "bmi" in df.columns else [0]*len(df)
    fig.add_trace(go.Scatter(
        x=x, y=bmi_vals, mode="lines+markers",
        name="BMI", line=dict(color="#10b981", width=2.5),
        marker=dict(size=7, color="#10b981"),
    ), row=1, col=2)
    # BMI reference bands
    fig.add_hline(y=18.5, line_dash="dot", line_color="#f59e0b", line_width=1,
                  annotation_text="Underweight 18.5", annotation_font_size=9,
                  annotation_font_color="#f59e0b", row=1, col=2)
    fig.add_hline(y=25.0, line_dash="dot", line_color="#ef4444", line_width=1,
                  annotation_text="Overweight 25", annotation_font_size=9,
                  annotation_font_color="#ef4444", row=1, col=2)
    fig.add_hrect(y0=18.5, y1=25.0, fillcolor="rgba(16,185,129,0.06)",
                  line_width=0, row=1, col=2)

    # ── Row 2: Calories Burned vs Food ──
    fig.add_trace(go.Bar(
        x=x, y=df.get("calories_burned", [0]*len(df)),
        name="Burned", marker_color="#38bdf8", opacity=0.85,
    ), row=2, col=1)
    if "food_calories" in df.columns:
        fig.add_trace(go.Bar(
            x=x, y=df["food_calories"],
            name="Food Intake", marker_color="#f59e0b", opacity=0.85,
        ), row=2, col=1)
    fig.update_layout(barmode="group")

    # ── Row 2: Water ──
    fig.add_trace(go.Bar(
        x=x, y=df["water"] if "water" in df.columns else [0]*len(df),
        name="Water", marker_color="#0ea5e9", opacity=0.85,
    ), row=2, col=2)
    fig.add_hline(y=8, line_dash="dot", line_color="#f59e0b", line_width=1,
                  annotation_text="Goal: 8", annotation_font_size=9,
                  annotation_font_color="#f59e0b", row=2, col=2)

    # ── Row 3: Sleep ──
    fig.add_trace(go.Scatter(
        x=x, y=df["sleep"] if "sleep" in df.columns else [0]*len(df),
        mode="lines+markers", fill="tozeroy",
        name="Sleep", line=dict(color="#818cf8", width=2),
        fillcolor="rgba(129,140,248,0.15)",
        marker=dict(size=6, color="#818cf8"),
    ), row=3, col=1)
    fig.add_hline(y=8, line_dash="dot", line_color="#10b981", line_width=1,
                  annotation_text="Ideal: 8h", annotation_font_size=9,
                  annotation_font_color="#10b981", row=3, col=1)

    # ── Row 3: Workout Duration ──
    fig.add_trace(go.Bar(
        x=x, y=df["duration"] if "duration" in df.columns else [0]*len(df),
        name="Duration", marker=dict(
            color=df["duration"] if "duration" in df.columns else [0]*len(df),
            colorscale=[[0, "#1d4ed8"], [0.5, "#0ea5e9"], [1, "#38bdf8"]],
            showscale=False,
        ),
        opacity=0.9,
    ), row=3, col=2)

    # ── Global layout ──
    fig.update_layout(
        height=750,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(17,24,39,0.0)",
        font=dict(color="#e0e6f0", size=11),
        title_font_color="#e0e6f0",
        showlegend=False,
        margin=dict(l=40, r=40, t=50, b=40),
    )

    # Style all subplots
    for i in range(1, 4):
        for j in range(1, 3):
            fig.update_xaxes(
                gridcolor="rgba(30,58,95,0.4)",
                linecolor="#1e3a5f",
                tickfont=dict(size=9, color="#64748b"),
                row=i, col=j,
            )
            fig.update_yaxes(
                gridcolor="rgba(30,58,95,0.4)",
                linecolor="#1e3a5f",
                tickfont=dict(size=9, color="#64748b"),
                row=i, col=j,
            )

    # Subplot title colors
    for ann in fig.layout.annotations:
        ann.font.color = "#94a3b8"
        ann.font.size = 12

    st.plotly_chart(fig, use_container_width=True)

    # ── Clean History Table ──
    st.markdown("---")
    st.markdown("#### 📋 Full History")
    display_df = df.copy()
    display_df["date"] = display_df["day_label"]

    # Rename columns nicely
    rename_map = {
        "date": "Date", "workout_type": "Workout", "duration": "Duration (min)",
        "calories_burned": "Burned (kcal)", "water": "Water (glasses)",
        "sleep": "Sleep (hrs)", "mood": "Mood", "steps": "Steps",
        "food_calories": "Food (kcal)", "net_calories": "Net Cal",
        "weight": "Weight (kg)", "bmi": "BMI",
    }
    display_df = display_df.rename(columns=rename_map)
    # Only show cols that exist
    show_cols = [v for v in rename_map.values() if v in display_df.columns]
    st.dataframe(display_df[show_cols], use_container_width=True, hide_index=True)



def show_workout_planner_tab():
    st.markdown('<div class="section-header">🗓️ AI Workout Planner</div>', unsafe_allow_html=True)

    p = st.session_state.profile
    col1, col2 = st.columns([1, 2])

    # Equipment options with strict no-equipment list
    NO_EQUIPMENT_TYPES = {
        "🏠 Home (No Equipment)": {
            "label": "Home Workout — No Equipment",
            "allowed": "bodyweight exercises only — push-ups, pull-ups (door frame), squats, lunges, planks, burpees, mountain climbers, jumping jacks, glute bridges, crunches, dips on chair",
            "banned": "STRICTLY NO dumbbells, barbells, cables, machines, resistance bands, gym equipment, or any equipment whatsoever.",
        },
        "🧘 Yoga / Stretching": {
            "label": "Yoga & Flexibility",
            "allowed": "yoga poses, stretches, breathing exercises, meditation",
            "banned": "NO gym equipment, NO weights.",
        },
        "💃 Dance / Zumba": {
            "label": "Dance & Cardio",
            "allowed": "dance routines, zumba, aerobics, jumping, cardio movements",
            "banned": "NO gym equipment, NO weights.",
        },
        "🪜 Stair / Outdoor Cardio": {
            "label": "Outdoor Cardio",
            "allowed": "stair climbing, running, brisk walking, jogging, spot jogging",
            "banned": "NO gym equipment, NO weights.",
        },
        "🏋️ Gym (Full Equipment)": {
            "label": "Full Gym Access",
            "allowed": "all equipment — dumbbells, barbells, cables, machines, benches",
            "banned": None,
        },
        "🏠+🏋️ Home + Dumbbells Only": {
            "label": "Home with Dumbbells",
            "allowed": "dumbbell exercises and bodyweight only — NO barbells, NO cables, NO machines",
            "banned": "NO barbells, NO cable machines, NO gym machines.",
        },
        "🚴 Cardio Only": {
            "label": "Cardio Focus",
            "allowed": "running, cycling, skipping, HIIT cardio, swimming",
            "banned": "NO weight training exercises.",
        },
    }

    with col1:
        st.markdown("#### ⚙️ Plan Parameters")

        st.info(
            f"**Goal:** {p['goal']}\n\n"
            f"**Activity Level:** {p['activity_level']}\n\n"
            f"**Age:** {p['age']} | **Weight:** {p['weight']}kg"
        )

        # Equipment selector
        equipment_choice = st.selectbox(
            "🏠 Equipment / Location",
            list(NO_EQUIPMENT_TYPES.keys()),
            index=0,
            help="This strictly controls what exercises AI will suggest"
        )
        eq = NO_EQUIPMENT_TYPES[equipment_choice]

        # Show badge
        if "No Equipment" in eq["label"] or "Home" in eq["label"] and "Dumbbell" not in eq["label"]:
            st.success("✅ No equipment needed — home friendly!")
        elif "Gym" in eq["label"]:
            st.warning("🏋️ Gym access required for this plan")
        else:
            st.info(f"ℹ️ {eq['label']}")

        # Workout days
        workout_days = st.slider("Workout Days Per Week", 3, 7, 5)

        # Session duration
        session_duration = st.selectbox("Session Duration", ["20-30 min", "30-45 min", "45-60 min", "60+ min"])

        # Injury / notes
        custom_notes = st.text_area(
            "Injuries or extra preferences? (optional)",
            placeholder="e.g. knee pain, back issue, prefer morning...",
            height=70,
        )

        if st.button("⚡ Generate My Plan", use_container_width=True):
            with st.spinner("FitAI is building your personalized plan..."):

                banned_str = f"\n\nSTRICT RULE — {eq['banned']}" if eq['banned'] else ""
                injury_str = f"\nInjuries/preferences: {custom_notes}" if custom_notes.strip() else ""

                plan_prompt = f"""
Create a {workout_days}-day per week workout plan with the following STRICT requirements:

PERSON: Age {p['age']}, Weight {p['weight']}kg, Gender {p.get('gender','Male')}, Goal: {p['goal']}, Activity: {p['activity_level']}
EQUIPMENT: {eq['allowed']}
SESSION DURATION: {session_duration}{banned_str}{injury_str}

IMPORTANT RULES:
1. Use ONLY the allowed equipment listed above. Do not suggest any exercise that needs other equipment.
2. For each day write: Day name, Focus area, then numbered exercises with sets/reps/duration and rest time.
3. Include warm-up (5 min) and cool-down (5 min) each day.
4. Day {workout_days + 1} onwards should be rest or active recovery.
5. Make it progressive and realistic for the person's activity level.
"""
                st.session_state.workout_plan = get_ai_reply(
                    plan_prompt,
                    system_prompt=(
                        "You are an elite certified personal trainer. "
                        "You STRICTLY follow equipment constraints. "
                        "If the plan says no equipment, you NEVER suggest dumbbells, barbells or machines. "
                        "You only suggest exercises that match the exact equipment specified."
                    )
                )

    with col2:
        if st.session_state.workout_plan:
            # Show equipment tag at top
            st.markdown(
                f'<div style="background:linear-gradient(90deg,#1d4ed8,transparent);'
                f'padding:8px 16px;border-radius:8px;margin-bottom:12px;'
                f'font-family:Rajdhani,sans-serif;font-weight:700;letter-spacing:1px;">'
                f'📋 {eq["label"]} Plan — {workout_days} days/week — {session_duration}</div>',
                unsafe_allow_html=True
            )
            st.markdown(st.session_state.workout_plan)

            if st.button("🔄 Regenerate Plan"):
                st.session_state.workout_plan = ""
                st.rerun()
        else:
            st.markdown("""
            <div style='background:#111827;border:1px solid #1e3a5f;border-radius:12px;padding:24px;text-align:center;'>
                <div style='font-size:3rem;margin-bottom:12px;'>🏋️</div>
                <div style='font-family:Rajdhani,sans-serif;font-size:1.3rem;color:#94a3b8;'>
                    Select your equipment type and click<br><strong style='color:#38bdf8;'>Generate My Plan</strong>
                </div>
                <div style='margin-top:12px;color:#64748b;font-size:0.85rem;'>
                    AI will create a plan using ONLY your selected equipment
                </div>
            </div>
            """, unsafe_allow_html=True)


def show_recommendations_tab():
    st.markdown('<div class="section-header">💡 Smart Insights</div>', unsafe_allow_html=True)

    daily = st.session_state.daily_data
    p = st.session_state.profile

    if not daily:
        st.info("Save today's tracker data to get personalized AI insights.")
        return

    # Auto recommendations
    issues = []
    positives = []

    if daily["water"] < 6:
        issues.append(f"💧 Low water intake ({daily['water']} glasses). Aim for 8+.")
    else:
        positives.append(f"💧 Great hydration! {daily['water']} glasses today.")

    if daily["sleep"] < 6:
        issues.append(f"😴 Low sleep ({daily['sleep']}h). Try for 7-9 hours.")
    elif daily["sleep"] >= 7:
        positives.append(f"😴 Good sleep quality at {daily['sleep']} hours.")

    if daily["duration"] < 20:
        issues.append("🏋️ Short workout. Try at least 30 minutes for best results.")
    elif daily["duration"] >= 45:
        positives.append(f"🏋️ Solid workout! {daily['duration']} minutes.")

    if daily.get("steps", 0) < 5000 and daily.get("steps", 0) > 0:
        issues.append(f"👟 Low step count ({daily['steps']}). Aim for 8,000-10,000.")

    total_food_cal = sum(f["calories"] for f in st.session_state.food_log)
    calorie_goal = st.session_state.calorie_goal
    if total_food_cal > 0:
        if total_food_cal > calorie_goal * 1.15:
            issues.append(f"🔥 Calorie intake ({total_food_cal} kcal) is above goal ({calorie_goal} kcal).")
        elif total_food_cal < calorie_goal * 0.7:
            issues.append(f"🥗 Calorie intake ({total_food_cal} kcal) is too low. Risk of muscle loss.")
        else:
            positives.append(f"🔥 Calorie intake ({total_food_cal} kcal) is on track!")

    col1, col2 = st.columns(2)
    with col1:
        if positives:
            st.markdown("#### ✅ What You're Doing Right")
            for p_item in positives:
                st.success(p_item)
    with col2:
        if issues:
            st.markdown("#### ⚠️ Areas to Improve")
            for issue in issues:
                st.warning(issue)

    # AI deep insight
    st.markdown("---")
    st.markdown("#### 🤖 AI Deep Analysis")
    if st.button("Get AI Personalized Advice", use_container_width=True):
        summary = (
            f"Today's data: workout={daily['workout_type']} for {daily['duration']}min, "
            f"calories burned={daily['calories_burned']}, water={daily['water']} glasses, "
            f"sleep={daily['sleep']}h, food calories={total_food_cal}, "
            f"goal={st.session_state.profile['goal']}."
        )
        with st.spinner("Analyzing your data..."):
            advice = get_ai_reply(
                f"Based on today's fitness data: {summary}. Give me 5 specific, actionable improvements.",
                "You are a data-driven fitness coach. Give numbered, specific, and practical advice."
            )
        st.markdown(advice)


def show_chatbot_tab():
    st.markdown('<div class="section-header">🤖 FitAI Chat</div>', unsafe_allow_html=True)
    st.caption("Ask anything — nutrition, workouts, recovery, form tips, supplements...")

    # Quick prompts
    st.markdown("**Quick Questions:**")
    qcols = st.columns(4)
    quick_prompts = [
        "💪 Best exercises for my goal",
        "🥗 What should I eat today?",
        "😴 How to improve sleep quality?",
        "🔥 How to boost metabolism?",
    ]
    for i, qp in enumerate(quick_prompts):
        if qcols[i].button(qp, use_container_width=True):
            st.session_state.chat_history.append({"role": "user", "content": qp})
            with st.spinner("Thinking..."):
                reply = get_ai_reply(qp)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            st.rerun()

    st.markdown("---")

    # Chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("Ask FitAI anything...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                reply = get_ai_reply(user_input)
            st.write(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
initialize_session_state()
show_sidebar()

# Header
st.markdown("""
<h1 style="font-family: 'Rajdhani', sans-serif; font-size: 2.5rem; font-weight: 700;
           background: linear-gradient(90deg, #38bdf8, #818cf8); -webkit-background-clip: text;
           -webkit-text-fill-color: transparent; margin-bottom: 0;">
    ⚡ FitAI Pro
</h1>
<p style="color: #94a3b8; font-size: 0.95rem; margin-top: 4px;">
    Your intelligent fitness companion — track, analyze, and optimize every day.
</p>
""", unsafe_allow_html=True)

# Today's summary strip (if data exists)
if st.session_state.daily_data:
    d = st.session_state.daily_data
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("💧 Water", f"{d['water']}g")
    m2.metric("😴 Sleep", f"{d['sleep']}h")
    m3.metric("🏃 Workout", f"{d['duration']}min")
    m4.metric("🔥 Burned", f"{d['calories_burned']} kcal")
    m5.metric("⚖️ Weight", f"{d['weight']}kg")
    m6.metric("🔥 Streak", f"{st.session_state.streak} days")

st.markdown("---")

# Main tabs
tabs = st.tabs(["📋 Daily Tracker", "🥗 Nutrition", "📈 Analytics", "🗓️ Workout Planner", "💡 Insights", "🤖 Chat"])

with tabs[0]:
    show_daily_tracker_tab()
with tabs[1]:
    show_nutrition_tab()
with tabs[2]:
    show_analytics_tab()
with tabs[3]:
    show_workout_planner_tab()
with tabs[4]:
    show_recommendations_tab()
with tabs[5]:
    show_chatbot_tab()