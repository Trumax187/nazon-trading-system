import os
from google import genai

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not set.")

client = genai.Client(api_key=API_KEY)

def analyze_chart(chart_data):
    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=f"You are NAZON, a forex trading assistant. Analyze this chart data and give a concise BUY, SELL, or WAIT recommendation with a brief reason.\n\n{chart_data}"
        )
        return response.text
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    test_data = "XAUUSDm H4: Price 3996.06, Trend DOWN, RSI 22.84, ADX 43.2 (Trending)"
    print("Sending test data to Gemini...")
    result = analyze_chart(test_data)
    print("\n--- Gemini Analysis ---")
    print(result)
