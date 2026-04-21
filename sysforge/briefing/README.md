The Daily Briefing Generator

Morning Report Builder - Generates a personalized daily briefing text file containing: current date/time with time zone, local weather (from mock data JSON file), a random motivational quote (from a local quotes file), today's calendar items (from a mock calendar JSON), system uptime, and disk space summary. Outputs to a dated file:
briefing_2026-04-24.txt.

Core features:
* Reads four mock data files: weather.json, quotes.json, calendar.json, plus a briefing_config.json for preferences (name, timezone, data file paths)
* Timezone-aware time using zoneinfo (with a README note about pip install tzdata on Windows)
* Greeting that varies by time of day ("Good morning, Princeton" / afternoon / evening)
* Current date, time, and day of week formatted in the user's timezone
* Today's weather pulled from the mock JSON (temp, condition, high/low)
* Random quote selected from quotes.json
* Today's calendar items filtered from the calendar JSON by date
* System snapshot: OS name, Python version, uptime, free disk space
* Output file named briefing_YYYY-MM-DD.txt in a configured briefings/ directory
* Output format selectable: --format text|markdown (HTML stretch)
* Section toggles: --no-weather, --no-quote, --no-calendar

