The Configuration Manager

JSON/TOML Config Handler - A tool that reads, validates, updates, and manages application configuration files. Commands: config get <key>, config set <key><value>, config validate, config diff file1.json file2.json, config init --templateapp (generate a default config from a template). Supports nested keys with dot notation: config. get ('database.host'). Validates values against a schema (type, range, required/optional).

Core features:
* JSON only for v1 (TOML as stretch — tomllib is stdlib but writing TOML needs tomli_w)
* config get database.host — dot notation for nested keys
* config set database.port 5432 --file app.json — sets value, preserves surrounding structure
* config list --file app.json — flattened view of all keys with their dot paths
* config validate app.json --schema app.schema.json — validates against a minimal schema (type, required, default, min/max, enum)
* config diff a.json b.json — shows added, removed, and changed keys with old→new values
* config init --template web-app — copies a named template from a local templates/ folder
* Atomic writes via temp file + rename
* Automatic .bak backup before every write
* Environment variable overrides (APP_DATABASE_HOST beats database.host when reading)
* Clear error messages with the key path that failed validation
* Exit codes that matter: 0 = ok, 1 = validation error, 2 = file error