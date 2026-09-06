import os
from datetime import datetime, timezone, timedelta
from kivy.app import App
from kivy.lang import Builder
from kivy.utils import platform
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.graphics import (
    Color, Line, Ellipse, Rectangle,
    StencilPush, StencilUse, StencilUnUse, StencilPop
)

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
    from jnius import autoclass, PythonJavaClass, java_method  # type: ignore
    from android.runnable import run_on_ui_thread  # type: ignore
    from android.activity import bind  # type: ignore

    @run_on_ui_thread
    def set_secure_window():
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        WindowManager = autoclass('android.view.WindowManager$LayoutParams')
        PythonActivity.mActivity.getWindow().addFlags(WindowManager.FLAG_SECURE)
else:
    def set_secure_window():
        pass


class TrendLineChart(Widget):
    """Canvas-rendered vector chart with strict bounding box clipping."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw)
        self.cached_points = []
        self.cached_target = 100.0

    def draw_data(self, points, target_val=100.0):
        self.cached_points = points
        self.cached_target = target_val
        self._redraw()

    def _redraw(self, *args):
        self.canvas.clear()
        if len(self.cached_points) < 2 or self.width <= 10 or self.height <= 10:
            return

        pad_x = 24
        pad_y = 18
        plot_w = max(self.width - (pad_x * 2), 10)
        plot_h = max(self.height - (pad_y * 2), 10)

        min_y = min(min(self.cached_points), self.cached_target) - 10
        max_y = max(max(self.cached_points), self.cached_target) + 10
        range_y = max_y - min_y if max_y != min_y else 1.0

        with self.canvas:
            StencilPush()
            Rectangle(pos=self.pos, size=self.size)
            StencilUse()

            # Soft card border
            Color(0.85, 0.89, 0.93, 1)
            Line(rectangle=(self.x + 1, self.y + 1, self.width - 2, self.height - 2), width=1.0)

            # Target Baseline (100 mg/dL optimal) - Vivid Emerald Green
            target_norm = (self.cached_target - min_y) / range_y
            target_y = self.y + pad_y + (target_norm * plot_h)
            Color(0.08, 0.68, 0.42, 0.85)
            Line(
                points=[self.x + pad_x, target_y, self.x + self.width - pad_x, target_y],
                width=1.4,
                dash_length=6,
                dash_offset=6
            )

            # Glucose Trajectory Line & Points - Deep Medical Cerulean
            pts = []
            Color(0.12, 0.48, 0.78, 1)
            step_x = plot_w / (len(self.cached_points) - 1)
            for i, val in enumerate(self.cached_points):
                norm_y = (val - min_y) / range_y
                px = self.x + pad_x + (i * step_x)
                py = self.y + pad_y + (norm_y * plot_h)
                pts.extend([px, py])
                Ellipse(pos=(px - 4, py - 4), size=(8, 8))

            Line(points=pts, width=2.2)

            StencilUnUse()
            Rectangle(pos=self.pos, size=self.size)
            StencilPop()


class VitalityRoot(BoxLayout):
    pass


class VitalityApp(App):
    status_text = StringProperty("Ready")
    selected_date = StringProperty(get_current_date_str())
    current_sugar_str = StringProperty("250.0")
    current_weight_str = StringProperty("78.5")
    notes_text = StringProperty("")
    stored_api_key = StringProperty("")

    # Daily checklist state
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
    history_text = StringProperty("No history loaded. Tap Refresh.")

    def build(self):
        if platform == 'android':
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            set_secure_window()
            base_dir = PythonActivity.mActivity.getFilesDir().getAbsolutePath()
        else:
            base_dir = os.path.expanduser("~/.vitality_tracker_mobile")
            os.makedirs(base_dir, exist_ok=True)

        self.db = DatabaseManager(base_dir)
        api_key = self.db.get_config("google_api_key", "")
        self.stored_api_key = api_key
        mode = "google_free" if api_key else "local"
        self.ai = AIEngine(mode=mode, api_key=api_key)
        self.plan_mgr = PlanManager(base_dir)

        self.root_widget = VitalityRoot()
        self.load_day(self.selected_date)
        self.refresh_history_table()
        return self.root_widget

    def show_calendar_picker(self):
        """Spawns native Android DatePickerDialog with dynamic screen-fitting."""
        try:
            cur_dt = datetime.strptime(self.selected_date, "%Y-%m-%d")
        except Exception:
            cur_dt = datetime.now(IST)

        if platform == 'android':
            class DateSetListener(PythonJavaClass):
                __javainterfaces__ = ['android/app/DatePickerDialog$OnDateSetListener']
                __javacontext__ = 'app'

                def __init__(self, callback):
                    super().__init__()
                    self.callback = callback

                @java_method('(Landroid/widget/DatePicker;III)V')
                def onDateSet(self, view, year, monthOfYear, dayOfMonth):
                    selected = f"{year:04d}-{monthOfYear + 1:02d}-{dayOfMonth:02d}"
                    self.callback(selected)

            @run_on_ui_thread
            def launch_native_picker():
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                DatePickerDialog = autoclass('android.app.DatePickerDialog')
                listener = DateSetListener(self.load_day)
                dialog = DatePickerDialog(
                    PythonActivity.mActivity,
                    listener,
                    cur_dt.year,
                    cur_dt.month - 1,
                    cur_dt.day
                )
                dialog.show()

            launch_native_picker()
        else:
            # Fallback popup for desktop testing
            box = BoxLayout(orientation='vertical', spacing=10, padding=10)
            txt_in = TextInput(text=self.selected_date, multiline=False, size_hint_y=0.4)
            btn = Button(text="Select", size_hint_y=0.4)
            box.add_widget(Label(text="Enter Date (YYYY-MM-DD):", size_hint_y=0.2))
            box.add_widget(txt_in)
            box.add_widget(btn)

            popup = Popup(title="Select Date", content=box, size_hint=(0.8, 0.35))

            def apply_selection(*args):
                self.load_day(txt_in.text.strip())
                popup.dismiss()

            btn.bind(on_release=apply_selection)
            popup.open()

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
            self.notes_text = log["notes"]
            self.current_image_uri = log["image_uri"]
            self.image_uri_indicator = "✓ Google Photo Linked" if self.current_image_uri else "No Photo Linked"
        else:
            self.chk_ex_m = self.chk_ex_e = self.chk_sol_m = self.chk_sol_e = False
            self.chk_pran = self.chk_pelv = False
            self.notes_text = ""
            self.current_image_uri = ""
            self.image_uri_indicator = "No Photo Linked"

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            day_plan = self.plan_mgr.get_plan_for_day(dt.strftime("%A"))
            self.plan_text = (
                f"Focus: {day_plan.get('Focus', '')}\n\n"
                f"Workout:\n{day_plan.get('Workout', '')}\n\n"
                f"Meals:\n- {day_plan.get('Breakfast', '')}\n- {day_plan.get('Dinner', '')}"
            )
        except Exception:
            self.plan_text = "Clinical plan unavailable."

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
        self.status_text = f"Saved {self.selected_date} to local database."
        self.refresh_graph()
        self.refresh_history_table()

    def refresh_history_table(self):
        records = self.db.get_all_logs()
        if not records:
            self.history_text = "No records found in database."
            return

        lines = ["Date         | Sugar | Weight | Habits"]
        lines.append("-" * 46)
        for r in records:
            # Record fields: id(0), date(1), weight(2), sugar(3), ex_m(4)...
            habits_done = sum([bool(r[i]) for i in range(4, 10)])
            lines.append(f"{r[1]} | {r[3]:>5.1f} | {r[2]:>6.1f} | {habits_done}/6 done")
        self.history_text = "\n".join(lines)

    def trigger_photo_picker(self):
        """Invokes Android Photo Picker for scoped, zero-permission gallery selection."""
        if platform != 'android':
            self.status_text = "Desktop mode: Use Android device for Photo Picker."
            return

        try:
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
                    self.status_text = "Meal photo linked via Content URI."

            bind(on_activity_result=on_activity_result)
            PythonActivity.mActivity.startActivityForResult(intent, 2001)
        except Exception as e:
            self.status_text = f"Picker error: {str(e)}"

    def analyze_linked_photo(self):
        if not self.current_image_uri:
            self.status_text = "First select a photo via 'Link Meal Photo'."
            return
        self.status_text = "Analyzing image stream with Gemini..."
        result = self.ai.analyze_food_image_uri(self.current_image_uri)
        self.ai_report_output = f"📸 Meal Scan Analysis:\n{result}"
        self.status_text = "Food scan completed."

    def refresh_graph(self):
        records = self.db.get_all_logs()
        if len(records) >= 2 and hasattr(self.root_widget, 'ids') and 'chart' in self.root_widget.ids:
            points = [row[3] for row in records]
            self.root_widget.ids.chart.draw_data(points, target_val=100.0)

    def trigger_ai_report(self):
        records = self.db.get_all_logs()
        self.status_text = "Synthesizing clinical audit..."
        self.ai_report_output = self.ai.generate_clinical_audit(records, "Daily Action Audit")
        self.status_text = "Report generated."

    def save_api_key(self, key_str):
        k = key_str.strip()
        if not k:
            self.status_text = "Error: Key cannot be empty."
            return
        
        valid, msg = self.ai.test_key(k)
        self.status_text = msg
        if valid:
            self.db.set_config("google_api_key", k)
            self.stored_api_key = k
            self.ai.api_key = k
            self.ai.mode = "google_free"


if __name__ == '__main__':
    VitalityApp().run()