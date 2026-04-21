The Time Tracker

CLI Billable Hours Logger - A CLI stopwatch and time logger. Commands: start "Client project" begins a timer; stop ends it and logs the entry; log shows today's entries; report --week generates a weekly summary; export --csv dumps all entries to CSV. Entries are persisted to a JSON file between sessions. Tracks: task name, start time, end time, duration, billable rate (configurable).

Core features:
* File-based state (no daemon) — a single timesheet.json holding entries plus an active_timer field
* start "Task name" --project ClientX --tag billable begins a timer (rejects if one is already running)
* stop ends the active timer and appends a completed entry
* status prints the active timer with elapsed time
* log shows today's entries with durations
* report --week or --month with totals by project and by tag
* export --csv timesheet.csv dumps all entries
* Atomic writes: write to timesheet.json.tmp, then os.replace — this is the detail that shows file I/O maturity
* Manual entry: add "Task" --start "2026-04-19 09:00" --end "2026-04-19 10:30" for forgotten sessions
* Delete by entry ID with confirmation prompt
* Configurable hourly rate per project, shown in reports as billable total
* Warns if a timer has been running > 8 hours ("did you forget to stop?")
* Duration formatted as Hh MMm, entries display in local time
