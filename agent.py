"""
Brussels Weather -> Gmail Automation
--------------------------------------------
Replicates a Zapier "weather -> email" workflow entirely in Python.
Fetches current weather from Open-Meteo and emails it via Gmail SMTP.
"""

import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# =========================================================
# CREDENTIALS
# Reads from environment variables (for GitHub Secrets / CI)
# and falls back to default values for local execution.
# =========================================================
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "dharani2006dgl@gmail.com")
APP_PASSWORD = os.getenv("APP_PASSWORD", "tbea grzy zlon fnzf")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "mega95377@gmail.com")

# =========================================================
# WEATHER CONFIG
# =========================================================
LATITUDE = 50.8503
LONGITUDE = 4.3517
LOCATION_NAME = "Brussels, Belgium"
TIMEZONE = "Europe/Brussels"

WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


WEATHER_META = {
    0: ("Clear Sky", "☀️", "#f59e0b", "#d97706"),
    1: ("Mainly Clear", "🌤️", "#0ea5e9", "#0284c7"),
    2: ("Partly Cloudy", "⛅", "#3b82f6", "#2563eb"),
    3: ("Overcast", "☁️", "#64748b", "#475569"),
    45: ("Foggy", "🌫️", "#64748b", "#475569"),
    48: ("Rime Fog", "🌫️", "#64748b", "#475569"),
    51: ("Light Drizzle", "🌦️", "#0284c7", "#0369a1"),
    53: ("Moderate Drizzle", "🌦️", "#0284c7", "#0369a1"),
    55: ("Dense Drizzle", "🌧️", "#0369a1", "#075985"),
    56: ("Freezing Drizzle", "🌨️", "#0ea5e9", "#0284c7"),
    57: ("Dense Freezing Drizzle", "🌨️", "#0284c7", "#0369a1"),
    61: ("Slight Rain", "🌧️", "#2563eb", "#1d4ed8"),
    63: ("Moderate Rain", "🌧️", "#1d4ed8", "#1e40af"),
    65: ("Heavy Rain", "🌧️", "#1e40af", "#172554"),
    66: ("Freezing Rain", "🌨️", "#0284c7", "#0369a1"),
    67: ("Heavy Freezing Rain", "🌨️", "#0369a1", "#075985"),
    71: ("Slight Snow", "❄️", "#38bdf8", "#0ea5e9"),
    73: ("Moderate Snow", "❄️", "#0ea5e9", "#0284c7"),
    75: ("Heavy Snow", "❄️", "#0284c7", "#0369a1"),
    77: ("Snow Grains", "❄️", "#38bdf8", "#0ea5e9"),
    80: ("Light Rain Showers", "🌦️", "#2563eb", "#1d4ed8"),
    81: ("Moderate Showers", "🌧️", "#1d4ed8", "#1e40af"),
    82: ("Violent Showers", "⛈️", "#1e3a8a", "#0f172a"),
    85: ("Snow Showers", "🌨️", "#0ea5e9", "#0284c7"),
    86: ("Heavy Snow Showers", "❄️", "#0284c7", "#0369a1"),
    95: ("Thunderstorm", "⛈️", "#7c3aed", "#5b21b6"),
    96: ("Thunderstorm w/ Hail", "⛈️", "#7c3aed", "#5b21b6"),
    99: ("Severe Thunderstorm", "⛈️", "#6d28d9", "#4c1d95"),
}


def get_weather_meta(code):
    """Return (description, emoji, grad_start, grad_end) for a weather code."""
    return WEATHER_META.get(code, ("Unknown", "🌡️", "#2563eb", "#1d4ed8"))


def weather_code_to_description(code):
    """Convert Open-Meteo weather_code into a human-readable description."""
    desc, _, _, _ = get_weather_meta(code)
    return desc


def get_weather_data():
    """Call the Open-Meteo API and return current weather data for Brussels."""
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
        ],
        "timezone": TIMEZONE,
    }

    try:
        response = requests.get(WEATHER_API_URL, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Weather API request failed: {e}")

    try:
        data = response.json()
        current = data["current"]
    except (ValueError, KeyError) as e:
        raise RuntimeError(f"Invalid API response format: {e}")

    required_keys = [
        "temperature_2m",
        "relative_humidity_2m",
        "apparent_temperature",
        "precipitation",
        "weather_code",
        "wind_speed_10m",
    ]
    for key in required_keys:
        if key not in current:
            raise RuntimeError(f"Missing expected field in API response: {key}")

    return current


def build_email_body(weather):
    """Build a clean, minimalist HTML email and plain-text fallback."""
    code = weather.get("weather_code", 0)
    condition = weather_code_to_description(code)
    temp = weather.get("temperature_2m", 0)
    apparent_temp = weather.get("apparent_temperature", 0)
    humidity = weather.get("relative_humidity_2m", 0)
    precipitation = weather.get("precipitation", 0.0)
    wind_speed = weather.get("wind_speed_10m", 0)
    timestamp = datetime.now().strftime("%B %d, %Y • %I:%M %p")

    # Clean plain-text fallback
    plain_body = f"""\
{LOCATION_NAME}
{temp}°C — {condition}
Feels like {apparent_temp}°C

Humidity:       {humidity}%
Wind Speed:     {wind_speed} km/h
Precipitation:  {precipitation} mm

Updated: {timestamp}
"""

    # Minimalist, elegant HTML email UI
    html_body = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{LOCATION_NAME} Weather</title>
</head>
<body style="margin: 0; padding: 0; background-color: #fafafa; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; color: #18181b;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #fafafa; padding: 48px 16px;">
    <tr>
      <td align="center">
        <!-- Minimal Card Container -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 440px; background-color: #ffffff; border: 1px solid #eaeaea; border-radius: 12px; padding: 36px 32px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);">
          
          <!-- Location & Date -->
          <tr>
            <td style="padding-bottom: 24px; text-align: left;">
              <div style="font-size: 13px; font-weight: 500; color: #71717a; letter-spacing: 0.3px;">
                {LOCATION_NAME}
              </div>
            </td>
          </tr>

          <!-- Large Minimal Temperature -->
          <tr>
            <td style="padding-bottom: 8px; text-align: left;">
              <div style="font-size: 72px; font-weight: 300; line-height: 1; letter-spacing: -3px; color: #18181b;">
                {round(temp)}<span style="font-size: 40px; font-weight: 200; vertical-align: top; margin-left: 2px;">°</span>
              </div>
            </td>
          </tr>

          <!-- Condition & Feels Like -->
          <tr>
            <td style="padding-bottom: 28px; text-align: left;">
              <div style="font-size: 15px; font-weight: 400; color: #52525b;">
                {condition} &bull; Feels like {round(apparent_temp)}°
              </div>
            </td>
          </tr>

          <!-- Hairline Divider -->
          <tr>
            <td style="border-top: 1px solid #f4f4f5; padding-bottom: 24px;"></td>
          </tr>

          <!-- Metrics Strip -->
          <tr>
            <td>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <!-- Humidity -->
                  <td width="33%" style="text-align: left; vertical-align: top;">
                    <div style="font-size: 10px; font-weight: 600; color: #a1a1aa; letter-spacing: 0.8px; text-transform: uppercase;">
                      Humidity
                    </div>
                    <div style="font-size: 16px; font-weight: 600; color: #18181b; margin-top: 4px;">
                      {humidity}%
                    </div>
                  </td>

                  <!-- Wind -->
                  <td width="34%" style="text-align: left; vertical-align: top;">
                    <div style="font-size: 10px; font-weight: 600; color: #a1a1aa; letter-spacing: 0.8px; text-transform: uppercase;">
                      Wind
                    </div>
                    <div style="font-size: 16px; font-weight: 600; color: #18181b; margin-top: 4px;">
                      {wind_speed} <span style="font-size: 12px; font-weight: 400; color: #71717a;">km/h</span>
                    </div>
                  </td>

                  <!-- Precipitation -->
                  <td width="33%" style="text-align: left; vertical-align: top;">
                    <div style="font-size: 10px; font-weight: 600; color: #a1a1aa; letter-spacing: 0.8px; text-transform: uppercase;">
                      Precipitation
                    </div>
                    <div style="font-size: 16px; font-weight: 600; color: #18181b; margin-top: 4px;">
                      {precipitation} <span style="font-size: 12px; font-weight: 400; color: #71717a;">mm</span>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Hairline Divider -->
          <tr>
            <td style="border-top: 1px solid #f4f4f5; padding-top: 24px; padding-bottom: 0;"></td>
          </tr>

          <!-- Minimal Footer -->
          <tr>
            <td style="text-align: left; padding-top: 12px;">
              <div style="font-size: 11px; color: #a1a1aa; font-weight: 400;">
                {timestamp} &bull; Open-Meteo
              </div>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    return plain_body, html_body, condition


def send_email(subject, plain_body, html_body):
    """Send multipart (HTML + plain text fallback) weather email using Gmail SMTP."""
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject

    # Attach plain text version first (fallback for simple clients)
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    # Attach HTML version second (email clients will display this by default)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
    except smtplib.SMTPAuthenticationError:
        raise RuntimeError("SMTP authentication failed. Check your email/app password.")
    except smtplib.SMTPException as e:
        raise RuntimeError(f"Failed to send email: {e}")


def main():
    # Step 1: Get weather data
    try:
        weather = get_weather_data()
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        return

    # Step 2: Print weather details to console
    condition = weather_code_to_description(weather["weather_code"])
    print("Weather data retrieved successfully:")
    print(f"  Location:      {LOCATION_NAME}")
    print(f"  Condition:     {condition}")
    print(f"  Temperature:   {weather['temperature_2m']} °C")
    print(f"  Feels Like:    {weather['apparent_temperature']} °C")
    print(f"  Humidity:      {weather['relative_humidity_2m']} %")
    print(f"  Precipitation: {weather['precipitation']} mm")
    print(f"  Wind Speed:    {weather['wind_speed_10m']} km/h")
    print()

    # Step 3: Build email content (both minimal HTML and plain text)
    plain_body, html_body, condition = build_email_body(weather)
    subject = f"{LOCATION_NAME} — {round(weather['temperature_2m'])}° {condition}"

    # Step 4: Send email
    try:
        send_email(subject, plain_body, html_body)
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        return

    # Step 5: Success message
    print("Minimalist weather email sent successfully!")


if __name__ == "__main__":
    main()