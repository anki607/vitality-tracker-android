import json
import os

DEFAULT_PLAN = {
    "Monday": {
        "Workout": "UPPER BODY STRENGTH:\n- Incline Push-ups: 3x10\n- Dumbbell Rows: 3x12/arm\n- Lateral Raises: 3x12",
        "Breakfast": "Plain or Methi/Palak Parantha + Dahi",
        "MidDay": "1 bowl of Watermelon cubes",
        "Evening": "30g Chana, 15g Walnuts, 15g Almonds, 10g Pumpkin Seeds, 2 Dates",
        "Dinner": "Roti + Dal + Dahi + Steamed Broccoli/Cauliflower",
        "Focus": "Bypasses insulin via upper body contractions to sink baseline glucose."
    },
    "Tuesday": {
        "Workout": "CORE & DEEP PELVIC FLOW:\n- Glute Bridges: 3x15 (3s hold)\n- Bird-Dogs: 3x10/side",
        "Breakfast": "Poha loaded with veggies + 2 Boiled Eggs",
        "MidDay": "1 bowl of Papaya + Lemon juice",
        "Evening": "30g Chana, 15g Walnuts, 15g Almonds, 10g Pumpkin Seeds, 2 Dates",
        "Dinner": "Rice + Dal + Dahi + Beetroot salad",
        "Focus": "Morning pelvic work awakens lower-abdomen circulation to stimulate vitality."
    },
    "Wednesday": {
        "Workout": "ARM HYPERTROPHY:\n- Dumbbell Hammer Curls: 3x12\n- Tricep Extensions: 3x12",
        "Breakfast": "Idli + Sambar + Sprouted Moong",
        "MidDay": "Sliced Carrot sticks + Dahi dip",
        "Evening": "30g Chana, 15g Walnuts, 15g Almonds, 10g Pumpkin Seeds, 2 Dates",
        "Dinner": "Roti + Paneer Bhurji + Sabji",
        "Focus": "Direct arm loading expands upper arm glycogen storage capacity."
    },
    "Thursday": {
        "Workout": "FLEXIBILITY & LIVER RECOVERY:\nDeep breathing and pelvic tracking.",
        "Breakfast": "Your choice of Parantha + Dahi",
        "MidDay": "1 cup of Watermelon or Papaya cubes",
        "Evening": "30g Chana, 15g Walnuts, 15g Almonds, 10g Pumpkin Seeds, 2 Dates",
        "Dinner": "Your choice of Roti/Sabji or Rice/Dal (Optional Swim 6-7 PM)",
        "Focus": "Deep pranayama reduces cortisol to prevent testosterone crashes."
    },
    "Friday": {
        "Workout": "REST WINDOW:\nNo heavy weights morning. Conserve energy.",
        "Breakfast": "Veggie Poha or Omelet with Carrots",
        "MidDay": "Raw Carrot and Beetroot salad",
        "Evening": "Transition directly to Friday layout at 8:00 PM",
        "Dinner": "MODIFIED FRIDAY PLAN (8:00 PM onwards):\n- 4x50ml Alcohol + 30g Roasted Peanuts\n- 2 Eggs or 80g Paneer\n- Salad: 50g Radish + 50g Cucumber + Lemon",
        "Focus": "High-protein fiber shield to protect blood vessels during drinks."
    },
    "Saturday": {
        "Workout": "WEEKEND SPORTS WINDOW:\nMain Cardio: Swimming or Table Tennis (10-11:30 AM or 6-7 PM)",
        "Breakfast": "High-Protein Breakfast (Eggs or Paneer/Sprouts)",
        "MidDay": "Mango slices or 1 small Banana",
        "Evening": "30g Chana, 15g Walnuts, 15g Almonds, 10g Pumpkin Seeds, 2 Dates",
        "Dinner": "Rice + Dal + Dahi + Veggies",
        "Focus": "Zero-impact swimming torches leftover glucose parameters."
    },
    "Sunday": {
        "Workout": "WEEKEND SPORTS WINDOW:\nCardio Session 2: Swimming or Table Tennis (10-11:30 AM or 6-7 PM)",
        "Breakfast": "Parantha + Dahi",
        "MidDay": "Mixed Watermelon and Papaya cubes",
        "Evening": "30g Chana, 15g Walnuts, 15g Almonds, 10g Pumpkin Seeds, 2 Dates",
        "Dinner": "Light Roti + Sabji + Dahi",
        "Focus": "Consecutive sports surge Nitric Oxide, expanding arterial walls."
    }
} #[cite: 1]

class PlanManager:
    def __init__(self, base_dir: str):
        self.file_path = os.path.join(base_dir, "ai_plan_overrides.json") #[cite: 1]
        self.overrides = self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_overrides(self, overrides: dict):
        self.overrides = overrides
        try:
            with open(self.file_path, "w") as f:
                json.dump(overrides, f, indent=4)
        except Exception:
            pass

    def get_plan_for_day(self, day_name: str) -> dict:
        base = DEFAULT_PLAN.get(day_name, DEFAULT_PLAN["Monday"]).copy()
        if day_name in self.overrides:
            base.update(self.overrides[day_name])
        return base