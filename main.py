import os
from datetime import datetime, timezone, timedelta
from kivy.app import App
from kivy.lang import Builder
from kivy.utils import platform
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Ellipse

from services.database import DatabaseManager
from services.ai_engine import AIEngine
from services.plan_manager import PlanManager

# Safe fallback for Android (UTC+5:30)
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
    _ = datetime.now(IST)
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30))

LOCAL_TZ = IST


def get_current_date_str():
    return datetime.now(IST).strftime("%Y-%m-%d")


# Android UI thread helper to prevent CalledFromWrongThreadException
if platform == 'android':
    from jnius import autoclass # type: ignore
    from android.runnable import run_on_ui_thread # type: ignore

    @run_on_ui_thread
    def set_secure_window():
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        WindowManager = autoclass('android.view.WindowManager$LayoutParams')
        PythonActivity.mActivity.getWindow().addFlags(WindowManager.FLAG_SECURE)
else:
    def set_secure_window():
        pass


class TrendLineChart(Widget):
    """Canvas-rendered vector chart replacing heavy Plotly dependencies."""
    def draw_data(self, points, target_val=100.0):
        self.canvas.clear()
        if len(points) < 2:
            return

        with self.canvas:
            Color(0.2, 0.25, 0.3, 1)
            Line(rectangle=(self.x, self.y, self.width, self.height), width=1.2)

            min_y = min(min(points), target_val) - 10
            max_y = max(max(points), target_val) + 10
            range_y = max_y - min_y if max_y != min_y else 1.0

            # Green dashed baseline for 100 mg/dL optimal target
            target_norm = (target_val - min_y) / range_y
            Color(0.2, 0.8, 0.3, 0.6)
            Line(
                points=[self.x, self.y + target_norm * self.height,
                        self.x + self.width, self.y + target_norm * self.height],
                width=1.1, dash_offset=5, dash_length=5
            )

            # Draw trajectory
            pts = []
            Color(0.1, 0.7, 0.9, 1)
            step_x = self.width / (len(points) - 1)
            for i, val in enumerate(points):
                norm_y = (val - min_y) / range_y
                px = self.x + i * step_x
                py = self.y + norm_y * self.height
                pts.extend([px, py])
                Ellipse(pos=(px - 3, py - 3), size=(6, 6))
            Line(points=pts, width=1.8)


class VitalityRoot(BoxLayout):
    pass


class VitalityApp(App):
    status_text = StringProperty("Ready")
    selected_date = StringProperty(get_current_date_str())
    current_sugar_str = StringProperty("250.0")
    current_weight_str = StringProperty("78.5")

    # Daily checklist flags
    chk_ex_m = BooleanProperty(False)
    chk_ex_e = BooleanProperty(False)
    chk_sol_m = BooleanProperty(False)
    chk_sol_e = BooleanProperty(False)
    chk_pran = BooleanProperty(False)
    chk_pelv = BooleanProperty(False)

    image_uri_indicator = StringProperty("No Photo Linked")
    current_image_uri = ""

    plan_text = StringProperty("")
    ai_report_output = StringProperty("Tap below to compile your audit.")

    def build(self):
        if platform == 'android':
            from jnius import autoclass # type: ignore
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            # Hardware-level screen blanking scheduled safely on Android UI thread
            set_secure_window()
            base_dir = PythonActivity.mActivity.getFilesDir().getAbsolutePath()
        else:
            base_dir = os.path.expanduser("~/.vitality_tracker_mobile")
            os.makedirs(base_dir, exist_ok=True)

        self.db = DatabaseManager(base_dir)
        api_key = self.db.get_config("google_api_key", "")
        mode = "google_free" if api_key else "local"
        self.ai = AIEngine(mode=mode, api_key=api_key)
        self.plan_mgr = PlanManager(base_dir)

        self.root_widget = VitalityRoot()
        self.load_day(self.selected_date)
        return self.root_widget

    def load_day(self, date_str):
        self.selected_date = date_str
        log = self.db.get_day_log(date_str)
        if log:
            self.current_sugar_str = str(log["sugar"])
            self.current_weight_str = str(log["weight"])
            self.chk_ex_m = log["exermet_m"]
            self.chk_ex_e = log["exermet_e"]
            self.chk_sol_m = log["soleus_m"]
            self.chk_sol_e = log["soleus_e"]
            self.chk_pran = log["pranayama"]
            self.chk_pelv = log["pelvic_yoga"]
            self.current_image_uri = log["image_uri"]
            self.image_uri_indicator = "✓ Google Photo Linked" if self.current_image_uri else "No Photo Linked"
        else:
            self.chk_ex_m = self.chk_ex_e = self.chk_sol_m = self.chk_sol_e = False
            self.chk_pran = self.chk_pelv = False
            self.current_image_uri = ""
            self.image_uri_indicator = "No Photo Linked"

        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_plan = self.plan_mgr.get_plan_for_day(dt.strftime("%A"))
        self.plan_text = (
            f"Focus: {day_plan.get('Focus', '')}\n\n"
            f"Workout:\n{day_plan.get('Workout', '')}\n\n"
            f"Meals:\n- {day_plan.get('Breakfast', '')}\n- {day_plan.get('Dinner', '')}"
        )
        self.refresh_graph()

    def commit_entry(self, sugar_text, weight_text, notes_text):
        try:
            s_val = float(sugar_text) if sugar_text else 220.0
            w_val = float(weight_text) if weight_text else 78.5
        except ValueError:
            self.status_text = "Error: Input valid numerical values."
            return

        self.db.save_day_log(
            self.selected_date, w_val, s_val,
            self.chk_ex_m, self.chk_ex_e, self.chk_sol_m, self.chk_sol_e,
            self.chk_pran, self.chk_pelv, [], notes_text,
            self.current_image_uri
        )
        self.status_text = f"Saved {self.selected_date} to offline database."
        self.refresh_graph()

    def trigger_photo_picker(self):
        """Invokes Android Photo Picker for zero-permission gallery linking."""
        if platform != 'android':
            self.status_text = "Desktop mode: Use Android device/emulator for Google Photos picker."
            return

        try:
            from jnius import autoclass # type: ignore
            from android.activity import bind # type: ignore

            Intent = autoclass('android.content.Intent')
            MediaStore = autoclass('android.provider.MediaStore')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')

            intent = Intent(MediaStore.ACTION_PICK_IMAGES)
            intent.setType("image/*")

            def on_activity_result(request_code, result_code, intent_data):
                if request_code == 2001 and result_code == -1 and intent_data is not None:
                    selected_uri = intent_data.getData().toString()
                    self.current_image_uri = selected_uri
                    self.image_uri_indicator = "✓ Google Photo Linked"
                    self.status_text = "Google Photo linked via content URI."

            bind(on_activity_result=on_activity_result)
            PythonActivity.mActivity.startActivityForResult(intent, 2001)
        except Exception as e:
            self.status_text = f"Picker error: {str(e)}"

    def analyze_linked_photo(self):
        if not self.current_image_uri:
            self.status_text = "First select a photo via the button above."
            return
        self.status_text = "Analyzing image stream with Gemini..."
        result = self.ai.analyze_food_image_uri(self.current_image_uri)
        self.ai_report_output = f"📸 Meal Scan Analysis:\n{result}"
        self.status_text = "Food scan completed."

    def refresh_graph(self):
        records = self.db.get_all_logs()
        if len(records) >= 2 and hasattr(self.root_widget, 'ids') and 'chart' in self.root_widget.ids:
            points = [row[2] for row in records]
            self.root_widget.ids.chart.draw_data(points, target_val=100.0)

    def trigger_ai_report(self):
        records = self.db.get_all_logs()
        self.status_text = "Synthesizing clinical audit..."
        self.ai_report_output = self.ai.generate_clinical_audit(records, "Daily Action Audit")
        self.status_text = "Report generated."

    def save_api_key(self, key_str):
        k = key_str.strip()
        if not k.startswith("AIzaSy"):
            self.status_text = "Invalid format: Google AI keys begin with 'AIzaSy'."
            return
        if self.ai.test_key(k):
            self.db.set_config("google_api_key", k)
            self.ai.api_key = k
            self.ai.mode = "google_free"
            self.status_text = "Google AI Key validated and active!"
        else:
            self.status_text = "Verification failed: Check key or network connection."


if __name__ == '__main__':
    VitalityApp().run()