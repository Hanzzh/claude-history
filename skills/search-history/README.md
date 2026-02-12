# Search History Skill

Enable Claude Code to proactively search your conversation history.

## What It Does

When you ask about something discussed before, Claude Code will:
- Detect time range from your query (yesterday, a few days ago, etc.)
- Search `.claude/history/` for relevant conversations
- Summarize previous discussions and relate them to your current question

## Installation

Copy this entire directory to `.claude/skills/search-history/`:

```bash
cp -r skills/search-history ~/.claude/skills/
```

## Usage Examples

```
You: What did we work on yesterday?
You: How did we handle that state management decision?
You: Have we talked about XXX before?
```
