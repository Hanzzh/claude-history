# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code conversation auto-export system that automatically exports conversation transcripts to Markdown files when exiting Claude Code. The system uses Claude Code's SessionEnd hook mechanism to trigger the export process.

## Architecture

### Hook-Based Auto-Export System

The system consists of three main components:

1. **Hook Configuration** (`.claude/settings.local.json`): Defines the SessionEnd hook that triggers on exit
2. **Shell Wrapper** (`.claude/scripts/export-conversation.sh`): Wrapper script that delegates to Python
3. **Python Export Engine** (`.claude/scripts/export-conversation.py`): Core logic for parsing and exporting transcripts

### Data Flow

```
User exits Claude Code (Ctrl+D / exit / logout)
    ↓
SessionEnd hook triggered (configured in settings.local.json)
    ↓
export-conversation.sh executed (with timeout 10s, async)
    ↓
export-conversation.py parses JSONL transcript from ~/.claude/projects/
    ↓
Messages converted to Markdown with YAML frontmatter
    ↓
Saved to .claude/history/YYYY/MM-DD/{session-id}.md
    ↓
index.md updated with new entry
```

### Transcript Format

The script parses Claude Code's JSONL (JSON Lines) format where each line contains:
- `type`: "user", "assistant", "tool_use", or "tool_result"
- `message`: Actual message content with `role` and `content` fields
- `content`: Array of content blocks (text, images, tool results)

### Export Structure

```
.claude/history/
├── index.md                          # Global conversation index
└── YYYY/MM-DD/{session-id}.md       # Individual conversations
```

Each exported Markdown file contains:
- YAML frontmatter (title, date, tags, session_id, project)
- Conversation content grouped by role (User, Claude, Tool Use)
- Tool calls formatted as code blocks with JSON input

## Development

### Testing the Export Hook

```bash
# Verify hook is configured
/hooks

# Manually test the export script
echo '{"session_id":"test","transcript_path":"/path/to/test.jsonl","cwd":"/home/han/Project/claude-histroy"}' | \
  .claude/scripts/export-conversation.sh
```

### Key Script Functions

**export-conversation.py**:

- `parse_transcript()`: Parses JSONL format conversation records
- `extract_content()`: Extracts text content from different message types (user, assistant, tool_use, tool_result)
- `generate_title()`: Generates title from first meaningful user message
- `extract_tags()`: Auto-generates tags based on keyword matching
- `to_markdown()`: Converts conversation to Markdown with YAML frontmatter
- `save_conversation()`: Saves files organized by date (YYYY/MM-DD/)
- `update_index()`: Updates global index.md with new conversation

### Script Paths

- Shell wrapper: `.claude/scripts/export-conversation.sh`
- Python script: `.claude/scripts/export-conversation.py`
- Configuration: `.claude/settings.local.json`

### Permissions Configuration

The `settings.local.json` must include these permissions:

```json
{
  "permissions": {
    "allow": [
      "Bash(timeout:*)",
      "Bash(.claude/scripts/export-conversation.sh:*)"
    ]
  }
}
```

## Important Notes

- The export script runs asynchronously (`async: true`) to avoid blocking the exit process
- The script receives JSON via stdin in hook mode (different from CLI mode)
- Hook mode receives session_id, transcript_path, and cwd from Claude Code environment
- Title generation skips tool-related messages and very short messages (<20 chars)
- Tags are auto-generated from keywords (bug-fix, feature-development, refactoring, testing, etc.)
