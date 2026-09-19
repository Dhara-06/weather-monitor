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
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "dharani2006dgl@gmail.com")

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
    """Build a colorful, interactive Bootstrap-styled HTML email and plain-text fallback."""
    code = weather.get("weather_code", 0)
    condition, emoji, grad_start, grad_end = get_weather_meta(code)
    temp = weather.get("temperature_2m", 0)
    apparent_temp = weather.get("apparent_temperature", 0)
    humidity = weather.get("relative_humidity_2m", 0)
    precipitation = weather.get("precipitation", 0.0)
    wind_speed = weather.get("wind_speed_10m", 0)
    timestamp = datetime.now().strftime("%B %d, %Y • %I:%M %p")

    # Thermal variance
    temp_delta = round(apparent_temp - temp, 1)
    delta_str = f"{temp_delta:+.1f}°C" if temp_delta != 0 else "0.0°C"

    # Contextual insight
    if precipitation > 0:
        insight = f"Precipitation of {precipitation} mm recorded. Don't forget an umbrella if heading out!"
        insight_bg = "#fff3cd"
        insight_border = "#ffecb5"
        insight_text = "#664d03"
    elif temp >= 22:
        insight = "Pleasantly warm weather today — great conditions for outdoor activities."
        insight_bg = "#d1e7dd"
        insight_border = "#badbcc"
        insight_text = "#0f5132"
    elif temp <= 7:
        insight = "Cold temperatures reported. Remember to bundle up with a warm jacket."
        insight_bg = "#cff4fc"
        insight_border = "#9eeaf9"
        insight_text = "#055160"
    else:
        insight = f"Stable {condition.lower()} conditions in {LOCATION_NAME}. Moderate atmospheric comfort."
        insight_bg = "#cfe2ff"
        insight_border = "#b6d4fe"
        insight_text = "#084298"

    # Clean plain-text fallback
    plain_body = f"""\
{LOCATION_NAME} Weather Update
{temp}°C — {condition} (Feels like {apparent_temp}°C)

* Humidity:      {humidity}%
* Wind Speed:    {wind_speed} km/h
* Precipitation: {precipitation} mm
* Real Feel:     {apparent_temp}°C ({delta_str})

Insight: {insight}

Updated: {timestamp} • Open-Meteo
"""

    # Colorful, Interactive Bootstrap 5 Email UI
    html_body = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{LOCATION_NAME} Weather</title>
  <!-- Bootstrap 5 CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body style="margin: 0; padding: 0; background-color: #f0f2f5; font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; color: #212529;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #f0f2f5; padding: 36px 12px;">
    <tr>
      <td align="center">
        
        <!-- Bootstrap Card Container -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 520px; background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(13, 110, 253, 0.08);">
          
          <!-- Card Header (Bootstrap Primary with Gradient) -->
          <tr>
            <td style="background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%); padding: 20px 26px; color: #ffffff;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td align="left">
                    <div style="font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: rgba(255, 255, 255, 0.85); margin-bottom: 4px;">
                      Weather Monitor
                    </div>
                    <div style="font-size: 20px; font-weight: 700; color: #ffffff;">
                      📍 {LOCATION_NAME}
                    </div>
                  </td>
                  <td align="right" valign="middle">
                    <span style="background-color: rgba(255, 255, 255, 0.25); color: #ffffff; padding: 5px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; display: inline-block;">
                      Live Sync
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Card Body -->
          <tr>
            <td style="padding: 26px 26px 20px; background-color: #ffffff;">
              
              <!-- Hero Section: Temperature & Icon -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td align="left" valign="middle">
                    <div style="font-size: 56px; font-weight: 800; color: #0d6efd; line-height: 1; letter-spacing: -2px;">
                      {round(temp)}<span style="font-size: 32px; font-weight: 500; color: #6c757d; vertical-align: top;">°C</span>
                    </div>
                    <div style="margin-top: 10px;">
                      <!-- Bootstrap Badges -->
                      <span style="background-color: #0dcaf0; color: #000000; font-size: 12px; font-weight: 700; padding: 5px 12px; border-radius: 20px; display: inline-block; text-transform: uppercase; letter-spacing: 0.3px;">
                        {condition}
                      </span>
                      <span style="background-color: #f8f9fa; color: #495057; font-size: 12px; font-weight: 600; padding: 5px 10px; border-radius: 20px; border: 1px solid #dee2e6; display: inline-block; margin-left: 6px;">
                        Feels like {round(apparent_temp)}°C
                      </span>
                    </div>
                  </td>
                  <td align="right" valign="middle" width="90">
                    <div style="font-size: 54px; line-height: 1;">
                      {emoji}
                    </div>
                  </td>
                </tr>
              </table>

              <!-- Bootstrap Alert Banner -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-top: 22px;">
                <tr>
                  <td style="background-color: {insight_bg}; border: 1px solid {insight_border}; border-radius: 8px; padding: 12px 16px; color: {insight_text}; font-size: 13px; line-height: 1.5;">
                    💡 <strong>Observation:</strong> {insight}
                  </td>
                </tr>
              </table>

              <!-- Bootstrap Metric Cards Grid (2x2) -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-top: 20px;">
                <tr>
                  <!-- Metric 1: Humidity (Bootstrap Info Tint) -->
                  <td width="48%" style="background-color: #f0f9ff; border: 1px solid #b6d4fe; border-radius: 10px; padding: 14px 16px; text-align: left; vertical-align: top;">
                    <div style="color: #055160; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                      💧 Humidity
                    </div>
                    <div style="color: #084298; font-size: 24px; font-weight: 800; margin: 4px 0 6px;">
                      {humidity}<span style="font-size: 14px; font-weight: 600; color: #6c757d;">%</span>
                    </div>
                    <!-- Bootstrap Progress Bar -->
                    <div style="background-color: #e2e8f0; height: 6px; border-radius: 3px; overflow: hidden;">
                      <div style="background-color: #0dcaf0; width: {humidity}%; height: 6px; border-radius: 3px;"></div>
                    </div>
                  </td>

                  <!-- Spacer -->
                  <td width="4%"></td>

                  <!-- Metric 2: Wind Speed (Bootstrap Success Tint) -->
                  <td width="48%" style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 14px 16px; text-align: left; vertical-align: top;">
                    <div style="color: #14532d; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                      💨 Wind Speed
                    </div>
                    <div style="color: #198754; font-size: 24px; font-weight: 800; margin: 4px 0 6px;">
                      {wind_speed} <span style="font-size: 12px; font-weight: 600; color: #6c757d;">km/h</span>
                    </div>
                    <!-- Bootstrap Progress Bar -->
                    <div style="background-color: #e2e8f0; height: 6px; border-radius: 3px; overflow: hidden;">
                      <div style="background-color: #198754; width: {min(100, int(wind_speed * 2.5))}%; height: 6px; border-radius: 3px;"></div>
                    </div>
                  </td>
                </tr>

                <tr><td height="12" colspan="3"></td></tr>

                <tr>
                  <!-- Metric 3: Precipitation (Bootstrap Primary Tint) -->
                  <td width="48%" style="background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; padding: 14px 16px; text-align: left; vertical-align: top;">
                    <div style="color: #1e40af; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                      🌧️ Precipitation
                    </div>
                    <div style="color: #0d6efd; font-size: 24px; font-weight: 800; margin: 4px 0 6px;">
                      {precipitation} <span style="font-size: 12px; font-weight: 600; color: #6c757d;">mm</span>
                    </div>
                    <span style="background-color: #dbeafe; color: #1e40af; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px; display: inline-block;">
                      {"Dry / Clear" if precipitation == 0 else "Active Rain"}
                    </span>
                  </td>

                  <!-- Spacer -->
                  <td width="4%"></td>

                  <!-- Metric 4: Real Feel (Bootstrap Warning Tint) -->
                  <td width="48%" style="background-color: #fffbeb; border: 1px solid #fde68a; border-radius: 10px; padding: 14px 16px; text-align: left; vertical-align: top;">
                    <div style="color: #92400e; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                      🌡️ Real Feel
                    </div>
                    <div style="color: #b45309; font-size: 24px; font-weight: 800; margin: 4px 0 6px;">
                      {apparent_temp}<span style="font-size: 14px; font-weight: 600; color: #6c757d;">°C</span>
                    </div>
                    <span style="background-color: #fef3c7; color: #92400e; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px; display: inline-block;">
                      Delta {delta_str}
                    </span>
                  </td>
                </tr>
              </table>

              <!-- Interactive Bootstrap Buttons Section -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-top: 24px;">
                <tr>
                  <td align="center">
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                      <tr>
                        <td style="padding: 0 4px;">
                          <a href="https://open-meteo.com/en/docs#latitude=50.8503&longitude=4.3517" target="_blank" style="display: inline-block; background-color: #0d6efd; border: 1px solid #0d6efd; color: #ffffff; text-decoration: none; padding: 9px 18px; font-weight: 600; font-size: 13px; border-radius: 6px;">
                            📊 Live Radar
                          </a>
                        </td>
                        <td style="padding: 0 4px;">
                          <a href="https://www.google.com/search?q=weather+brussels" target="_blank" style="display: inline-block; background-color: #ffffff; border: 1px solid #0d6efd; color: #0d6efd; text-decoration: none; padding: 9px 18px; font-weight: 600; font-size: 13px; border-radius: 6px;">
                            🌐 7-Day Forecast &rarr;
                          </a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- Card Footer (Bootstrap Light) -->
          <tr>
            <td style="background-color: #f8f9fa; border-top: 1px solid #dee2e6; padding: 16px 26px; text-align: center;">
              <div style="font-size: 11px; color: #6c757d;">
                Generated on {timestamp} &bull; Powered by Open-Meteo &amp; Bootstrap
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

    # Step 3: Build email content (both Bootstrap HTML and plain text)
    plain_body, html_body, condition = build_email_body(weather)
    subject = f"🌤️ {LOCATION_NAME} Weather: {round(weather['temperature_2m'])}°C {condition}"

    # Step 4: Send email
    try:
        send_email(subject, plain_body, html_body)
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        return

    # Step 5: Success message
    print("Bootstrap-styled weather email sent successfully!")


if __name__ == "__main__":
    main()