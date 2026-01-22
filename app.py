import streamlit as st
import json
import os
import datetime

# --- 1. DATA CONFIGURATION ---
DB_FILE = "smartstock_db.json"

# How long items last (in days)
ITEM_LIFESPAN = {
    "Milk": 3, "Bread": 4, "Eggs": 7, "Bananas": 5, "Curd": 4
}

# Event Bundles
EVENT_BUNDLES = {
    "Diwali": ["Oil", "Cotton Wicks", "Besan", "Sugar", "Gifts"],
    "Birthday Party": ["Cake Mix", "Candles", "Chips", "Cold Drink", "Disposable Plates"],
    "Movie Night": ["Popcorn", "Nachos", "Soda"],
    "Summer Stock": ["Glucon-D", "Mangoes", "Ice Cream"]
}

# --- 2. DATABASE FUNCTIONS ---
def load_data():
    if not os.path.exists(DB_FILE):
        return {"shopping_list": [], "pantry": {}}
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"shopping_list": [], "pantry": {}}

def save_data(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

data = load_data()

# --- 3. INTELLIGENCE ENGINES ---
def get_restock_suggestions(pantry_data):
    """Engine 1: Checks for expiring items"""
    suggestions = []
    today = datetime.date.today()
    
    for item, details in pantry_data.items():
        if details.get("status") == "In Stock":
            bought_date = datetime.datetime.strptime(details["bought_date"], "%Y-%m-%d").date()
            lifespan = ITEM_LIFESPAN.get(item, 7) # Default to 7 days if unknown
            
            # If 80% of lifespan has passed, suggest it
            days_passed = (today - bought_date).days
            if days_passed >= (lifespan * 0.8):
                suggestions.append(item)
    return suggestions

def get_event_suggestions(selected_event):
    """Engine 2: Checks for upcoming events"""
    if selected_event and selected_event in EVENT_BUNDLES:
        return EVENT_BUNDLES[selected_event]
    return []

# --- 4. APP UI ---
st.set_page_config(page_title="SmartStock Pro", page_icon="🛍️")
st.title("🛍️ SmartStock Pro")

# === SIDEBAR: THE SIMULATOR & TIME MACHINE ===
st.sidebar.header("🔧 Developer Tools")

# Tool 1: Event Simulator
st.sidebar.subheader("1. Event Simulator")
simulated_event = st.sidebar.selectbox(
    "Trigger an Event:",
    ["None", "Diwali", "Birthday Party", "Movie Night"]
)

# Tool 2: Time Machine (THE FIX)
st.sidebar.divider()
st.sidebar.subheader("2. Time Machine ⏰")
st.sidebar.caption("Make all pantry items 7 days old to test alerts.")
if st.sidebar.button("Age Inventory by 1 Week"):
    if data["pantry"]:
        past_date = str(datetime.date.today() - datetime.timedelta(days=7))
        for item in data["pantry"]:
            data["pantry"][item]["bought_date"] = past_date
        save_data(data)
        st.sidebar.success("🕒 Time Travel Successful! Check 'Plan' tab.")
        st.rerun()
    else:
        st.sidebar.warning("Pantry is empty! Buy something first.")

tab1, tab2, tab3 = st.tabs(["📝 Plan", "🏪 Shop", "🏠 Pantry"])

# --- TAB 1: PLAN (The Intelligence Hub) ---
with tab1:
    st.header("Smart Planner")
    
    # 🧠 SECTION 1: RESTOCK ALERTS
    restock_items = get_restock_suggestions(data["pantry"])
    
    if restock_items:
        st.error(f"⚠️ **Expired/Low Stock:** {', '.join(restock_items)}")
        st.caption("These items are past their usage date.")
        
        if st.button("Add Restock Items ➕", key="btn_restock"):
            for item in restock_items:
                if item not in data["shopping_list"]:
                    data["shopping_list"].append(item)
                    # Mark status as Low so it doesn't spam
                    data["pantry"][item]["status"] = "Low"
            save_data(data)
            st.success("Added to shopping list!")
            st.rerun()
    else:
        st.info("✅ No low-stock items detected.")

    # 🎉 SECTION 2: EVENT ALERTS
    if simulated_event != "None":
        event_items = get_event_suggestions(simulated_event)
        needed_items = [item for item in event_items if item not in data["shopping_list"]]
        
        st.divider()
        if needed_items:
            st.info(f"🎉 **{simulated_event}** detected!")
            st.write(f"Suggested: {', '.join(needed_items)}")
            
            if st.button(f"Add Bundle 🛒", key="btn_event"):
                data["shopping_list"].extend(needed_items)
                save_data(data)
                st.rerun()

    st.divider()

    # SECTION 3: MANUAL INPUT
    col1, col2 = st.columns([3, 1])
    with col1:
        new_item = st.text_input("Manual Add", placeholder="e.g. Toothpaste")
    with col2:
        if st.button("Add"):
            if new_item and new_item not in data["shopping_list"]:
                data["shopping_list"].append(new_item)
                save_data(data)
                st.rerun()

    # SECTION 4: THE LIST
    st.subheader("Your Shopping List")
    if data["shopping_list"]:
        for i, item in enumerate(data["shopping_list"]):
            st.text(f"{i+1}. {item}")
        
        if st.button("Clear List 🗑️"):
            data["shopping_list"] = []
            save_data(data)
            st.rerun()
    else:
        st.caption("List is empty.")

# --- TAB 2: SHOP ---
with tab2:
    st.header("In The Market")
    if not data["shopping_list"]:
        st.success("Relax! Nothing to buy.")
    else:
        for item in data["shopping_list"][:]:
            if st.checkbox(f"Buy {item}", key=f"shop_{item}"):
                data["shopping_list"].remove(item)
                data["pantry"][item] = {"status": "In Stock", "bought_date": str(datetime.date.today())}
                save_data(data)
                st.toast(f"Got {item}!")
                st.rerun()

# --- TAB 3: PANTRY ---
with tab3:
    st.header("Inventory")
    if data["pantry"]:
        display_data = []
        for name, info in data["pantry"].items():
            display_data.append({"Item": name, "Bought": info["bought_date"]})
        st.dataframe(display_data)
        
        if st.button("Reset All Data"):
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
            st.rerun()
    else:
        st.info("Pantry is empty.")
