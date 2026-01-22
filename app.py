import streamlit as st
import json
import os
import datetime
import re
import difflib
from statistics import mean

# --- 1. CONFIGURATION & DATA ---
DB_FILE = "smartstock_db.json"

# A. Hardcoded "Teacher" Knowledge (Fallback)
DEFAULT_LIFESPAN = {
    "Milk": 3, "Bread": 4, "Eggs": 7, "Bananas": 5, "Curd": 4, 
    "Toothpaste": 30, "Rice": 30, "Oil": 30
}

# B. Known valid items for Spell Check
VALID_ITEMS = list(DEFAULT_LIFESPAN.keys())

# --- 2. THE AI BRAIN (NLP & ML) ---

def parse_smart_input(raw_text):
    """
    NLP Engine: Extracts Item Name and Quantity from messy text.
    Input: "2kg Rice" or "Rice 2kg" or "Rcie"
    Output: ("Rice", "2kg")
    """
    # 1. Extract Quantity (Digits + Optional Unit)
    # Looks for things like "2kg", "1 L", "500g", "2"
    quantity_match = re.search(r'(\d+\s*[a-zA-Z]+|\d+)', raw_text)
    quantity = quantity_match.group(0) if quantity_match else "1"
    
    # 2. Extract Item Name (Remove the quantity from text)
    item_name = raw_text.replace(quantity, "").strip()
    
    # 3. Spell Checker (Fuzzy Logic)
    # Finds the closest match in our known list (cutoff=0.6 means 60% similarity)
    closest_matches = difflib.get_close_matches(item_name.title(), VALID_ITEMS, n=1, cutoff=0.6)
    
    if closest_matches:
        final_name = closest_matches[0] # Auto-correct to "Rice"
    else:
        final_name = item_name.title() # Keep as new item if no match found
        
    return final_name, quantity

def calculate_dynamic_lifespan(item_name, purchase_history):
    """
    ML Engine: Learns from your history.
    Calculates average days between purchases.
    """
    # Filter history for this specific item
    dates = [
        datetime.datetime.strptime(entry["date"], "%Y-%m-%d") 
        for entry in purchase_history 
        if entry["item"] == item_name
    ]
    dates.sort()
    
    # We need at least 2 purchases to calculate a gap
    if len(dates) < 2:
        return DEFAULT_LIFESPAN.get(item_name, 7) # Fallback to Hardcoded
    
    # Calculate gaps between purchases
    gaps = []
    for i in range(1, len(dates)):
        delta = (dates[i] - dates[i-1]).days
        gaps.append(delta)
        
    # Return the average (ML Prediction)
    if gaps:
        return int(mean(gaps))
    else:
        return DEFAULT_LIFESPAN.get(item_name, 7)

# --- 3. DATABASE FUNCTIONS ---
def load_data():
    if not os.path.exists(DB_FILE):
        # Added "history" to track past purchases for ML
        return {"shopping_list": [], "pantry": {}, "history": []}
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"shopping_list": [], "pantry": {}, "history": []}

def save_data(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- 4. APP INTERFACE ---
def main():
    st.set_page_config(page_title="SmartStock AI", page_icon="🧠")
    
    # Login Check (Simplified for demo)
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        st.title("🔐 Login")
        if st.button("Login as Rahul"): # Quick login for demo
            st.session_state["logged_in"] = True
            st.rerun()
        return

    data = load_data()
    st.title("🧠 SmartStock AI")

    tab1, tab2, tab3 = st.tabs(["📝 Plan", "🏪 Shop", "🏠 Pantry"])

    # --- TAB 1: PLAN (The AI Hub) ---
    with tab1:
        st.header("Smart Planner")
        
        # === A. PREDICTION ENGINE ===
        suggestions = []
        today = datetime.date.today()
        
        for item, details in data["pantry"].items():
            if details["status"] == "In Stock":
                last_bought = datetime.datetime.strptime(details["bought_date"], "%Y-%m-%d").date()
                
                # HYBRID LOGIC: Ask ML first, fallback to Hardcode
                lifespan = calculate_dynamic_lifespan(item, data["history"])
                
                days_passed = (today - last_bought).days
                if days_passed >= (lifespan * 0.8):
                    suggestions.append(f"{item} (Expires in ~{lifespan} days)")

        if suggestions:
            st.warning(f"📉 **AI Prediction:** You are low on: {', '.join(suggestions)}")
        
        st.divider()

        # === B. NLP INPUT ===
        st.subheader("Add Item (Natural Language)")
        with st.form("nlp_form", clear_on_submit=True):
            raw_input = st.text_input("Type naturally (e.g., '2L milk', 'rice 5kg', 'banna')")
            submitted = st.form_submit_button("Add to List")
            
            if submitted and raw_input:
                # RUN NLP & SPELL CHECK
                item, qty = parse_smart_input(raw_input)
                
                # Check if we spell-corrected it
                if item.lower() not in raw_input.lower() and item in VALID_ITEMS:
                    st.success(f"✨ Corrected spelling: **'{item}'**")
                
                full_entry = f"{item} ({qty})"
                if full_entry not in data["shopping_list"]:
                    data["shopping_list"].append(full_entry)
                    save_data(data)
                    st.toast(f"Added {full_entry}")
                    st.rerun()

        # === C. LIST ===
        if data["shopping_list"]:
            st.write("### Current List:")
            for item in data["shopping_list"]:
                st.text(f"• {item}")
            if st.button("Clear List"):
                data["shopping_list"] = []
                save_data(data)
                st.rerun()

    # --- TAB 2: SHOP ---
    with tab2:
        st.header("Shopping Mode")
        if not data["shopping_list"]:
            st.info("List is empty.")
        else:
            for entry in data["shopping_list"][:]:
                if st.checkbox(f"Buy {entry}", key=f"shop_{entry}"):
                    # Clean item name for history (remove quantity bracket)
                    # e.g., "Milk (2L)" -> "Milk"
                    item_name = entry.split(" (")[0]
                    
                    data["shopping_list"].remove(entry)
                    
                    # 1. Update Pantry
                    data["pantry"][item_name] = {
                        "status": "In Stock", 
                        "bought_date": str(datetime.date.today())
                    }
                    
                    # 2. Update ML History (The Learning Part)
                    data["history"].append({
                        "item": item_name,
                        "date": str(datetime.date.today())
                    })
                    
                    save_data(data)
                    st.toast(f"Bought {item_name}! AI is learning...")
                    st.rerun()

    # --- TAB 3: PANTRY & BRAIN ---
    with tab3:
        st.header("Inventory & AI Stats")
        
        if data["pantry"]:
            st.subheader("📦 Current Stock")
            clean_data = [{"Item": k, "Bought": v["bought_date"]} for k,v in data["pantry"].items()]
            st.dataframe(clean_data)
        
        st.divider()
        st.subheader("🧠 What the AI has learned")
        if data["history"]:
            # Show calculated lifespans
            stats = []
            unique_items = set([x["item"] for x in data["history"]])
            for item in unique_items:
                ml_lifespan = calculate_dynamic_lifespan(item, data["history"])
                source = "AI (History)" if len([x for x in data["history"] if x["item"]==item]) >= 2 else "Hardcoded (Default)"
                stats.append({"Item": item, "Estimated Lifespan": f"{ml_lifespan} Days", "Source": source})
            st.dataframe(stats)
        else:
            st.info("Buy items more than once to start training the AI.")

if __name__ == "__main__":
    main()
