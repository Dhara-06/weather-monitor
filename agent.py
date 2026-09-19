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
    """Build an executive-grade, professional HTML email briefing and plain-text fallback."""
    code = weather.get("weather_code", 0)
    condition, emoji, _, _ = get_weather_meta(code)
    temp = weather.get("temperature_2m", 0)
    apparent_temp = weather.get("apparent_temperature", 0)
    humidity = weather.get("relative_humidity_2m", 0)
    precipitation = weather.get("precipitation", 0.0)
    wind_speed = weather.get("wind_speed_10m", 0)
    now = datetime.now()
    timestamp = now.strftime("%B %d, %Y • %I:%M %p")
    report_id = f"WXR-BRU-{now.strftime('%Y%m%d%H%M')}"

    # Atmospheric moisture classification
    if humidity < 30:
        hum_badge, hum_bg, hum_fg = "Low", "#fef3c7", "#b45309"
        hum_desc = "Low atmospheric humidity levels."
    elif humidity <= 65:
        hum_badge, hum_bg, hum_fg = "Optimal", "#dcfce7", "#15803d"
        hum_desc = "Optimal atmospheric comfort range."
    elif humidity <= 80:
        hum_badge, hum_bg, hum_fg = "Elevated", "#e0f2fe", "#0369a1"
        hum_desc = "Moderate ambient moisture index."
    else:
        hum_badge, hum_bg, hum_fg = "Saturated", "#fee2e2", "#b91c1c"
        hum_desc = "Near moisture saturation."

    # Wind velocity classification
    if wind_speed < 12:
        wind_badge, wind_bg, wind_fg = "Calm", "#dcfce7", "#15803d"
        wind_desc = "Negligible wind displacement."
    elif wind_speed <= 28:
        wind_badge, wind_bg, wind_fg = "Moderate Breeze", "#e0f2fe", "#0369a1"
        wind_desc = "Surface breeze active (Beaufort 4)."
    elif wind_speed <= 45:
        wind_badge, wind_bg, wind_fg = "Fresh Breeze", "#fef3c7", "#b45309"
        wind_desc = "Gusty conditions; outdoor caution advised."
    else:
        wind_badge, wind_bg, wind_fg = "High Wind", "#fee2e2", "#b91c1c"
        wind_desc = "Elevated wind forces present."

    # Precipitation status
    if precipitation == 0:
        precip_badge, precip_bg, precip_fg = "Zero Rain", "#f1f5f9", "#475569"
        precip_desc = "Dry conditions; zero precipitation recorded."
        precip_summary = "Precipitation probability remains negligible."
        op_status = "standard and uninhibited"
    elif precipitation <= 2.0:
        precip_badge, precip_bg, precip_fg = "Light Precip", "#e0f2fe", "#0369a1"
        precip_desc = f"{precipitation} mm precipitation volume detected."
        precip_summary = "Light precipitation recorded in the vicinity."
        op_status = "stable with localized wet surfaces"
    else:
        precip_badge, precip_bg, precip_fg = "Active Rainfall", "#fee2e2", "#b91c1c"
        precip_desc = f"{precipitation} mm heavy precipitation volume."
        precip_summary = "Active rainfall observed across the sector."
        op_status = "subject to standard weather delays"

    # Thermal variance calculation
    temp_delta = round(apparent_temp - temp, 1)
    delta_str = f"{temp_delta:+.1f}°C" if temp_delta != 0 else "0.0°C"

    # Executive Briefing text
    exec_summary = (
        f"Surface telemetry for {LOCATION_NAME} indicates an ambient temperature of {temp}°C "
        f"with a wind-chill displacement to {apparent_temp}°C under {condition.lower()} skies. "
        f"Relative moisture is sustained at {humidity}%, accompanied by surface winds at {wind_speed} km/h. "
        f"{precip_summary} Overall transit and field operations remain {op_status}."
    )

    # Plain-text Fallback
    plain_body = f"""\
===================================================================
METEOROLOGICAL INTELLIGENCE BRIEFING | EXECUTIVE DISPATCH
===================================================================
Location:         {LOCATION_NAME}
Coordinates:      {LATITUDE}° N, {LONGITUDE}° E
Timezone:         {TIMEZONE}
Dispatch Time:    {timestamp}
Report Reference: {report_id}
-------------------------------------------------------------------
CURRENT METRICS:
* Ambient Temperature:  {temp} °C
* Apparent Temperature: {apparent_temp} °C (Variance: {delta_str})
* Sky Condition:        {condition}
* Relative Humidity:    {humidity} % ({hum_badge})
* Surface Wind Speed:   {wind_speed} km/h ({wind_badge})
* Precipitation Volume: {precipitation} mm ({precip_badge})
-------------------------------------------------------------------
EXECUTIVE SUMMARY & OPERATIONAL IMPACT:
{exec_summary}
-------------------------------------------------------------------
Automated Meteorological Transmission • Synoptic Observation Feed
===================================================================
"""

    # Executive-grade HTML Email UI
    html_body = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Meteorological Intelligence Report - {LOCATION_NAME}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; color: #0f172a;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #f1f5f9; padding: 32px 14px;">
    <tr>
      <td align="center">
        <!-- Main Container Card -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 620px; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(15, 23, 42, 0.08); border: 1px solid #e2e8f0;">
          
          <!-- Top Accent Band -->
          <tr>
            <td height="4" style="background: linear-gradient(90deg, #1e3a8a 0%, #2563eb 50%, #0284c7 100%);"></td>
          </tr>

          <!-- Executive Header Bar -->
          <tr>
            <td style="background-color: #0f172a; padding: 24px 30px 22px; color: #ffffff;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td align="left">
                    <div style="color: #94a3b8; font-size: 11px; font-weight: 700; letter-spacing: 1.4px; text-transform: uppercase; margin-bottom: 6px;">
                      METEOROLOGICAL INTELLIGENCE DISPATCH
                    </div>
                    <div style="color: #ffffff; font-size: 22px; font-weight: 700; letter-spacing: -0.4px;">
                      {LOCATION_NAME}
                    </div>
                    <div style="color: #64748b; font-size: 12px; margin-top: 2px;">
                      Coord: {LATITUDE}° N, {LONGITUDE}° E &bull; {TIMEZONE}
                    </div>
                  </td>
                  <td align="right" valign="top">
                    <!-- Status Indicator Badge -->
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                      <tr>
                        <td style="background-color: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 5px 10px;">
                          <span style="display: inline-block; width: 7px; height: 7px; background-color: #22c55e; border-radius: 50%; margin-right: 5px; vertical-align: middle;"></span>
                          <span style="color: #22c55e; font-size: 11px; font-weight: 700; letter-spacing: 0.8px; vertical-align: middle;">LIVE SYNC</span>
                        </td>
                      </tr>
                      <tr>
                        <td align="right" style="color: #64748b; font-size: 10px; padding-top: 6px; font-family: 'SFMono-Regular', Consolas, Menlo, monospace;">
                          {report_id}
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Primary Metric & Real-Feel Hero Section -->
          <tr>
            <td style="padding: 28px 30px 20px; background-color: #ffffff; border-bottom: 1px solid #f1f5f9;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <!-- Left: Temperature & Conditions -->
                  <td align="left" valign="middle" width="55%">
                    <div style="color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 4px;">
                      CURRENT OBSERVATION
                    </div>
                    <div style="font-size: 54px; font-weight: 800; color: #0f172a; line-height: 1; letter-spacing: -2px;">
                      {temp}<span style="font-size: 28px; font-weight: 500; color: #64748b; vertical-align: super;">°C</span>
                    </div>
                    <div style="margin-top: 10px;">
                      <span style="display: inline-block; background-color: #f1f5f9; color: #1e293b; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 4px; border: 1px solid #cbd5e1; text-transform: uppercase; letter-spacing: 0.5px;">
                        {condition}
                      </span>
                      <span style="display: inline-block; color: #64748b; font-size: 13px; font-weight: 500; margin-left: 8px;">
                        Feels like <strong style="color: #0f172a;">{apparent_temp}°C</strong>
                      </span>
                    </div>
                  </td>

                  <!-- Right: Snapshot Overview -->
                  <td align="right" valign="middle" width="45%">
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; text-align: left; width: 100%;">
                      <tr>
                        <td style="color: #64748b; font-size: 11px; padding-bottom: 5px;">Sky Status:</td>
                        <td align="right" style="color: #0f172a; font-size: 12px; font-weight: 600; padding-bottom: 5px;">{condition}</td>
                      </tr>
                      <tr>
                        <td style="color: #64748b; font-size: 11px; padding-bottom: 5px;">Thermal Variance:</td>
                        <td align="right" style="color: #0f172a; font-size: 12px; font-weight: 600; padding-bottom: 5px;">{delta_str}</td>
                      </tr>
                      <tr>
                        <td style="color: #64748b; font-size: 11px;">Precip Risk:</td>
                        <td align="right" style="color: #15803d; font-size: 12px; font-weight: 600;">{precip_badge}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Executive Summary Callout Box -->
          <tr>
            <td style="padding: 16px 30px 10px;">
              <div style="background-color: #f8fafc; border-left: 4px solid #2563eb; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; border-radius: 0 8px 8px 0; padding: 14px 18px;">
                <div style="color: #2563eb; font-size: 11px; font-weight: 800; letter-spacing: 0.9px; text-transform: uppercase; margin-bottom: 6px;">
                  EXECUTIVE SYNOPSIS & OPERATIONAL IMPACT
                </div>
                <div style="color: #334155; font-size: 13px; line-height: 1.55;">
                  {exec_summary}
                </div>
              </div>
            </td>
          </tr>

          <!-- Detailed Telemetry Matrix (4 Clean KPI Cards) -->
          <tr>
            <td style="padding: 14px 30px 24px;">
              <div style="color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 10px;">
                KEY METEOROLOGICAL INDICATORS
              </div>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <!-- Card 1: Humidity -->
                  <td width="48%" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; vertical-align: top;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                      <tr>
                        <td style="color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                          Relative Humidity
                        </td>
                        <td align="right">
                          <span style="background-color: {hum_bg}; color: {hum_fg}; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px;">
                            {hum_badge}
                          </span>
                        </td>
                      </tr>
                    </table>
                    <div style="color: #0f172a; font-size: 26px; font-weight: 800; margin: 8px 0 3px;">
                      {humidity}<span style="font-size: 15px; font-weight: 600; color: #64748b; margin-left: 2px;">%</span>
                    </div>
                    <div style="color: #64748b; font-size: 11px; line-height: 1.4;">
                      {hum_desc}
                    </div>
                  </td>

                  <!-- Spacer -->
                  <td width="4%"></td>

                  <!-- Card 2: Wind Velocity -->
                  <td width="48%" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; vertical-align: top;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                      <tr>
                        <td style="color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                          Wind Velocity
                        </td>
                        <td align="right">
                          <span style="background-color: {wind_bg}; color: {wind_fg}; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px;">
                            {wind_badge}
                          </span>
                        </td>
                      </tr>
                    </table>
                    <div style="color: #0f172a; font-size: 26px; font-weight: 800; margin: 8px 0 3px;">
                      {wind_speed}<span style="font-size: 13px; font-weight: 600; color: #64748b; margin-left: 3px;">km/h</span>
                    </div>
                    <div style="color: #64748b; font-size: 11px; line-height: 1.4;">
                      {wind_desc}
                    </div>
                  </td>
                </tr>

                <tr><td height="12" colspan="3"></td></tr>

                <tr>
                  <!-- Card 3: Precipitation -->
                  <td width="48%" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; vertical-align: top;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                      <tr>
                        <td style="color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                          Precipitation
                        </td>
                        <td align="right">
                          <span style="background-color: {precip_bg}; color: {precip_fg}; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px;">
                            {precip_badge}
                          </span>
                        </td>
                      </tr>
                    </table>
                    <div style="color: #0f172a; font-size: 26px; font-weight: 800; margin: 8px 0 3px;">
                      {precipitation}<span style="font-size: 13px; font-weight: 600; color: #64748b; margin-left: 3px;">mm</span>
                    </div>
                    <div style="color: #64748b; font-size: 11px; line-height: 1.4;">
                      {precip_desc}
                    </div>
                  </td>

                  <!-- Spacer -->
                  <td width="4%"></td>

                  <!-- Card 4: Apparent Temperature -->
                  <td width="48%" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; vertical-align: top;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                      <tr>
                        <td style="color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                          Real Feel Index
                        </td>
                        <td align="right">
                          <span style="background-color: #f1f5f9; color: #475569; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px;">
                            Delta {delta_str}
                          </span>
                        </td>
                      </tr>
                    </table>
                    <div style="color: #0f172a; font-size: 26px; font-weight: 800; margin: 8px 0 3px;">
                      {apparent_temp}<span style="font-size: 15px; font-weight: 600; color: #64748b; margin-left: 2px;">°C</span>
                    </div>
                    <div style="color: #64748b; font-size: 11px; line-height: 1.4;">
                      Thermal displacement relative to ambient air.
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Synoptic Metadata Table -->
          <tr>
            <td style="padding: 0 30px 24px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; font-size: 12px;">
                <tr style="background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                  <td style="padding: 9px 14px; font-weight: 600; color: #475569; width: 40%; border-bottom: 1px solid #e2e8f0;">Station Identification</td>
                  <td style="padding: 9px 14px; color: #0f172a; border-bottom: 1px solid #e2e8f0;">Open-Meteo Synoptic Grid ({LOCATION_NAME})</td>
                </tr>
                <tr style="background-color: #ffffff;">
                  <td style="padding: 9px 14px; font-weight: 600; color: #475569; border-bottom: 1px solid #e2e8f0;">Geographic Coordinate</td>
                  <td style="padding: 9px 14px; color: #0f172a; border-bottom: 1px solid #e2e8f0;">Lat {LATITUDE} &bull; Lon {LONGITUDE}</td>
                </tr>
                <tr style="background-color: #f8fafc;">
                  <td style="padding: 9px 14px; font-weight: 600; color: #475569;">Telemetry Timestamp</td>
                  <td style="padding: 9px 14px; color: #0f172a;">{timestamp} ({TIMEZONE})</td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Corporate Footer -->
          <tr>
            <td style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 22px 30px; text-align: center;">
              <div style="color: #475569; font-size: 12px; font-weight: 600; margin-bottom: 4px;">
                Automated Meteorological Intelligence System
              </div>
              <div style="color: #94a3b8; font-size: 11px; line-height: 1.5;">
                This transmission is an automated executive weather briefing for {LOCATION_NAME}.<br>
                Official synoptic data &bull; Generated via Python &bull; Ref: {report_id}
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
    return plain_body, html_body, condition, emoji, report_id


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

    # Step 3: Build email content (both rich HTML and plain text)
    plain_body, html_body, condition, emoji, report_id = build_email_body(weather)
    subject = f"[BRIEFING] {LOCATION_NAME} Weather: {condition} ({weather['temperature_2m']}°C)"

    # Step 4: Send email
    try:
        send_email(subject, plain_body, html_body)
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        return

    # Step 5: Success message
    print(f"Executive weather briefing ({report_id}) sent successfully!")


if __name__ == "__main__":
    main()