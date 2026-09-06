import json
import requests

class AIEngine:
    def __init__(self, mode: str = "local", api_key: str = ""):
        self.mode = mode
        self.api_key = api_key
        self.endpoint_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

    def test_key(self, key_str: str) -> bool:
        """Validates key format and tests live connectivity against Google AI Studio."""
        if not key_str or not key_str.startswith("AIzaSy"):
            return False

        test_url = f"{self.endpoint_url}?key={key_str}"
        payload = {
            "contents": [{"parts": [{"text": "ping"}]}]
        }
        try:
            resp = requests.post(test_url, json=payload, timeout=8)
            return resp.status_code == 200
        except Exception:
            return False

    def generate_clinical_audit(self, records: list, audit_type: str = "Daily Action Audit") -> str:
        """Compiles an endocrine audit from variable-length SQLite row tuples."""
        if not records:
            return "No historical records logged yet. Commit daily entries first."

        formatted_history = []
        for row in records:
            if len(row) >= 11:
                # Schema: id(0), log_date(1), weight(2), sugar(3), ex_m(4), ex_e(5), sol_m(6), sol_e(7), pran(8), pelv(9), notes(10)
                log_date = row[1]
                weight = row[2]
                sugar = row[3]
                habits_done = sum([bool(row[i]) for i in range(4, 10)])
                notes = row[10] or ""
                formatted_history.append(
                    f"• {log_date}: Fasting Sugar={sugar} mg/dL, Weight={weight} kg, Habits={habits_done}/6. Notes: {notes}"
                )
            elif len(row) >= 4:
                formatted_history.append(f"• {row[1]}: Sugar={row[3]} mg/dL, Weight={row[2]} kg")
            elif len(row) == 3:
                d, w, s = row
                formatted_history.append(f"• {d}: Sugar={s} mg/dL, Weight={w} kg")

        history_summary = "\n".join(formatted_history[-7:])

        prompt = (
            f"You are an expert Clinical Endocrinologist and Metabolic Health Specialist.\n"
            f"Review this patient's recent glycemic tracking data:\n\n"
            f"{history_summary}\n\n"
            f"Clinical Target: Fasting Blood Glucose of 100 mg/dL.\n"
            f"Provide a concise, 3-bullet clinical assessment covering:\n"
            f"1. Glycemic velocity and trajectory relative to 100 mg/dL.\n"
            f"2. Adherence to physical interventions (Soleus contractions, Exermet timing, Pranayama).\n"
            f"3. High-leverage tactical advice for tomorrow."
        )

        if self.mode == "google_free" and self.api_key:
            return self._call_gemini_api(prompt)
        else:
            last_entry = records[-1]
            latest_sugar = last_entry[3] if len(last_entry) >= 4 else (last_entry[2] if len(last_entry) == 3 else 200.0)
            latest_weight = last_entry[2] if len(last_entry) >= 4 else (last_entry[1] if len(last_entry) == 3 else 75.0)

            return (
                f"Local Clinical Audit ({audit_type}):\n"
                f"• Current fasting glucose is {latest_sugar:.1f} mg/dL (Target: 100 mg/dL).\n"
                f"• Recorded weight is {latest_weight:.1f} kg.\n"
                f"• Maintain post-meal 15-minute Soleus pushups and ensure steady hydration to optimize insulin-independent glucose clearance."
            )

    def analyze_food_image_uri(self, image_uri: str) -> str:
        if not self.api_key:
            return "Gemini API key not configured. Save a valid AIzaSy key in Settings to analyze photos."
        return "Meal photo linked. Nutritional decomposition requires active Gemini vision stream."

    def _call_gemini_api(self, prompt: str) -> str:
        target_url = f"{self.endpoint_url}?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 600
            }
        }
        try:
            resp = requests.post(target_url, json=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            elif resp.status_code == 400:
                return "API Error 400: Malformed request or invalid API key. Update key in Settings."
            elif resp.status_code == 429:
                return "API Error 429: Rate limit reached. Free-tier quota will refresh shortly."
            else:
                return f"Google AI Studio returned HTTP {resp.status_code}."
        except requests.exceptions.Timeout:
            return "Network timeout contacting Google AI Studio. Check connection."
        except Exception as e:
            return f"Inference error: {str(e)}"