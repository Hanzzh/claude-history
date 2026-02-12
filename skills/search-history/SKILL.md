---
description: Search conversation history for relevant context
---

## History Directory Structure

```
.claude/history/
├── index.md                          # Global conversation index (metadata only)
└── YYYY/                             # Organized by year
    └── MM-DD/                        # Organized by month-day
        ├── {session-id-a}.md         # Individual conversation files
        ├── {session-id-b}.md
        └── ...
```

Each conversation file contains:
- YAML frontmatter (title, date, tags, session_id, project)
- Complete conversation content (User, Claude, Tool Use)

## Search Strategy

When the user asks about something that might have been discussed before:

1. **Detect time range** from user query:
   - "yesterday" / "last day" → search in specific date folder like `.claude/history/*/{MM-DD}/`
   - "N days ago" / "a few days ago" → search in recent date folders
   - No time mentioned → search all history

2. **Use Glob** to find relevant files in `.claude/history/**/*.md` (or narrowed by date pattern)

3. **Use Grep** to search for keywords in those files

4. **Use Read** to read the most relevant conversations

5. **Summarize** what was discussed before and how it relates to the current question

## Example Queries

- "How did we handle that state management decision?"
- "What did we discuss about..."
- "Have we talked about XXX before"
- "What did we work on yesterday?"
- "What did we discuss a few days ago?"
