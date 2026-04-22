The System Health Monitor

System Vitals Logger - Checks system health metrics: disk usage per partition, memory usage (using psutil or parsing /proc on Linux), CPU load average, running process count, and uptime. Logs readings to a timestamped file. Sets configurable thresholds and flags warnings (disk > 80%, memory > 90%). When run in --watch mode, it takes readings every N seconds and appends them to the log.

Core features:
* psutil for cross-platform metric reading (don't parse /proc by hand)
* Metrics collected: CPU percent, memory percent + available bytes, disk usage per partition, process count, boot time / uptime, load average on Unix
* Single-shot mode (default) prints a snapshot and exits
* --watch --interval 30 takes readings every N seconds until Ctrl+C
* Thresholds loaded from a config file (reuse Day 26's config manager — this is where integration starts)
* Alert levels: INFO (normal), WARNING (e.g. disk > 80%), CRITICAL (e.g. disk > 95%)
* Alerts only fire on transition (WARNING → CRITICAL), not every cycle — no spam
* Log file in JSON Lines format (one JSON object per line, easy to parse later)
* Log rotation by size (e.g. rotate at 10MB, keep last 5 files)
* Pretty console output via rich (colored table, updated in place in watch mode)
* Graceful shutdown on Ctrl+C: writes a final log line, closes files cleanly
* Top 5 processes by memory and CPU in the single-shot view


