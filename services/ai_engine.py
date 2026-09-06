import json
import base64
import requests
from kivy.utils import platform

class AIEngine:
    def __init__(self, mode="local", api_key=""):
        self.mode = mode
        self.api_key = api_key

    def test_key(self, key: str) -> bool:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
        try:
            res = requests.post(
                url,
                json={
                    "contents": [{"parts": [{"text": "ping"}]}],
                    "generationConfig": {"maxOutputTokens": 1}
                },
                timeout=5
            )
            return res.status_code == 200
        except Exception:
            return False

    def generate_clinical_audit(self, history_rows: list, report_type: str) -> str:
        # PII Scrubbing: Only dates, weights, and sugars are formatted[cite: 1]
        context_str = "\n".join([f"Date: {d} | Sugar: {s} | Weight: {w}" for d, w, s in history_rows[-14:]]) #[cite: 1]

        if self.mode == "google_free" and self.api_key:
            prompt = (
                f"Act as an endocrine sports scientist. Construct a detailed '{report_type}' based strictly on these vitals:\n\n"
                f"{context_str}\n\n"
                f"Provide actionable glycemic optimization guidance. Never provide clinical diagnoses."
            ) #[cite: 1]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
            try:
                res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
                if res.status_code == 200:
                    return res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception:
                pass

        # Offline Local Engine Fallback
        if not history_rows:
            return "Local Engine: No history logged yet."
        last_d, last_w, last_s = history_rows[-1]
        return (f"Local Audit ({report_type}): Current fasting glucose is {last_s} mg/dL, weight is {last_w} kg. "
                f"Ensure 15-minute Soleus contractions post-dinner to accelerate non-insulin-mediated glucose disposal.")

    def read_uri_to_base64(self, uri_str: str) -> str:
        """Streams directly from Google Photos / Android ContentProvider without storing files to disk."""
        if not uri_str:
            return ""

        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Uri = autoclass('android.net.Uri')
                ByteArrayOutputStream = autoclass('java.io.ByteArrayOutputStream')

                activity = PythonActivity.mActivity
                resolver = activity.getContentResolver()
                uri = Uri.parse(uri_str)

                input_stream = resolver.openInputStream(uri)
                if not input_stream:
                    return ""

                byte_array_output = ByteArrayOutputStream()
                buffer = bytearray(4096)
                while True:
                    bytes_read = input_stream.read(buffer)
                    if bytes_read == -1:
                        break
                    byte_array_output.write(buffer, 0, bytes_read)

                raw_bytes = bytes(byte_array_output.toByteArray())
                input_stream.close()
                return base64.b64encode(raw_bytes).decode('utf-8')
            except Exception:
                return ""
        else:
            # Desktop fallback for testing
            import os
            if os.path.exists(uri_str):
                with open(uri_str, "rb") as f:
                    return base64.b64encode(f.read()).decode('utf-8')
            return ""

    def analyze_food_image_uri(self, uri_str: str) -> str:
        if not (self.mode == "google_free" and self.api_key):
            return "Local Mode: Connect your free Google AI Key in Settings to enable multimodal food photo scans."

        img_b64 = self.read_uri_to_base64(uri_str)
        if not img_b64:
            return "Could not stream image directly from Google Photos."

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        prompt = (
            "You are an expert sports nutrition AI. Analyze this food photo. "
            "Provide a 2-sentence nutritional estimate of glycemic load, carbs, and protein."
        ) #[cite: 1]
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}}
                ]
            }]
        } #[cite: 1]
        try:
            res = requests.post(url, json=payload, timeout=20)
            if res.status_code == 200:
                return res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return f"Google AI error code {res.status_code}. Please verify your quota."
        except Exception as e:
            return f"Photo evaluation failed: {str(e)}"