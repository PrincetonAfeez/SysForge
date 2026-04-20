The Folder Organizer

Automated File Sorter - Scans a target directory (e.g., Downloads) and sorts files into organized subdirectories based on configurable rules: by extension (/Images, /Docs, /Code, /Archives, /Media), by date modified (year/month folders), or by size(small/medium/large). Handles duplicates (rename with suffix, skip, or overwrite — user's choice). Generates a move log.


Core features:
* Three sort modes selectable via flag: --by extension, --by date, --by size
* Rule config loaded from a JSON file (extension → category mapping, size buckets, date format) with a shipped default
* Dry-run mode (--dry-run) that prints the full plan without touching the filesystem
* Duplicate handling strategy (--on-conflict rename|skip|overwrite), with rename appending _1, _2, etc.
* Move log written to a JSON file (timestamp, source path, destination path, strategy used)
* --undo command that reads the most recent log and reverses the moves
* Hidden files skipped by default, --include-hidden to override
* Symlinks skipped (documented behavior, not silent)
* Summary report at the end: moved, skipped, errors, total size processed
* Single-directory scan by default; --recursive is opt-in