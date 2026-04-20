The Markdown-to-HTML Generator

Documentation Builder - Reads a Markdown file and converts it to styled HTML. Handles: headings (h1–h6), bold, italic, links, images, code blocks (with syntax highlighting class tags), ordered/unordered lists, blockquotes, horizontal rules. Wraps output in a clean HTML template with CSS. Supports batch mode (convert a folder of .md files into a static site).

Core features:
* Uses the markdown library with a defined set of enabled extensions (fenced code, tables, TOC) — don't hand-roll a parser in a day
* Single-file mode: mdhtml input.md --output output.html
* Batch mode: mdhtml ./notes/ --output ./site/ converts every .md file, preserving folder structure
* HTML template system — a template.html file with {{content}}, {{title}}, {{generated_at}} placeholders
* Two shipped themes (light and dark CSS files), selectable via --theme
* Frontmatter parsing (YAML block at top of file → title, author, date)
* Auto-generated index.html in batch mode with links to all converted files, sorted by date
* Syntax highlighting for code blocks via pygments CSS
* Table of contents generated from headings
* Relative image paths copied to output directory
* Clear error reporting: which file failed, which line
