#!/usr/bin/env python3
"""
Export Claude Code conversation transcripts to Markdown format.

This script reads JSONL transcript files and converts them to organized
Markdown files with YAML frontmatter for easy reference.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def parse_transcript(transcript_path: str) -> List[Dict[str, Any]]:
    """Parse JSONL format conversation transcript."""
    messages = []
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Extract relevant message types
                    msg_type = data.get('type')
                    if msg_type in ['user', 'assistant']:
                        # Actual content is in 'message' field
                        if 'message' in data:
                            msg_data = data['message']
                            # Add type info for content extraction
                            msg_data['_msg_type'] = msg_type
                            messages.append(msg_data)
                    elif msg_type in ['tool_use', 'tool_result']:
                        messages.append(data)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print(f"Warning: Transcript file not found: {transcript_path}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error reading transcript: {e}", file=sys.stderr)
        return []

    return messages


def extract_content(message: Dict[str, Any]) -> Optional[str]:
    """Extract text content from a message."""
    # Get message type from special field or role
    msg_type = message.pop('_msg_type', message.get('role', ''))

    if msg_type == 'user' or message.get('role') == 'user':
        # User messages have 'content' as array or string
        content = message.get('content', '')
        if isinstance(content, list):
            # Handle content blocks (text, images, etc.)
            texts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get('type') == 'text':
                        texts.append(block.get('text', ''))
                    elif block.get('type') == 'image':
                        texts.append(f"[Image: {block.get('source', {}).get('media_type', 'unknown')}]")
                    elif block.get('type') == 'tool_result':
                        # Tool results in user messages
                        tool_name = block.get('tool_use_id', 'unknown')
                        texts.append(f"[Tool Result: {tool_name}]")
                        if 'content' in block:
                            result_content = block['content']
                            if isinstance(result_content, str):
                                texts.append(result_content)
                            elif isinstance(result_content, list):
                                for item in result_content:
                                    if isinstance(item, dict) and item.get('type') == 'text':
                                        texts.append(item.get('text', ''))
                elif isinstance(block, str):
                    texts.append(block)
            return '\n'.join(texts).strip()
        return str(content)

    elif msg_type == 'assistant' or message.get('role') == 'assistant':
        # Assistant messages have 'content' as array
        content = message.get('content', [])
        if isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get('type') == 'text':
                        texts.append(block.get('text', ''))
                    elif block.get('type') == 'tool_use':
                        tool_name = block.get('name', 'unknown')
                        texts.append(f"\n**Tool Use**: `{tool_name}`\n")
                        # Add tool input if present
                        if 'input' in block:
                            input_data = block['input']
                            if isinstance(input_data, dict) and input_data:
                                texts.append(f"```json\n{json.dumps(input_data, indent=2, ensure_ascii=False)}\n```\n")
                elif isinstance(block, str):
                    texts.append(block)
            return '\n'.join(texts).strip()
        return str(content)

    elif message.get('type') == 'tool_use':
        # Standalone tool use messages
        tool_name = message.get('name', 'unknown')
        result = f"**Tool Use**: `{tool_name}`\n"
        if 'input' in message:
            input_data = message['input']
            if isinstance(input_data, dict) and input_data:
                result += f"```json\n{json.dumps(input_data, indent=2, ensure_ascii=False)}\n```\n"
        return result

    elif message.get('type') == 'tool_result':
        # Tool result messages
        tool_use_id = message.get('tool_use_id', 'unknown')
        result = f"**Tool Result**: `{tool_use_id}`\n"
        if 'content' in message:
            content = message['content']
            if isinstance(content, str):
                result += f"```\n{content}\n```\n"
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        result += f"```\n{item.get('text', '')}\n```\n"
        return result

    return None


def generate_title(messages: List[Dict[str, Any]], session_id: str) -> str:
    """Generate a title from the first meaningful user message."""
    for msg in messages:
        if msg.get('role') == 'user':
            content = extract_content(msg)
            if content:
                content = content.strip()
                # Skip tool-related or system messages
                skip_prefixes = ['[Tool Result:', '[Tool Use:', '[Request interrupted', '[Image:']
                if any(content.startswith(p) for p in skip_prefixes):
                    continue
                # Skip very short messages (less than 20 chars)
                if len(content) < 20:
                    continue
                # Use first line or first 50 chars
                first_line = content.split('\n')[0].strip()
                if len(first_line) > 50:
                    return first_line[:47] + "..."
                if first_line:
                    return first_line
    return f"Conversation {session_id[:8]}"


def extract_tags(messages: List[Dict[str, Any]]) -> List[str]:
    """Extract tags from conversation content."""
    # Look for common keywords
    all_text = ""
    for msg in messages:
        content = extract_content(msg)
        if content:
            all_text += content.lower() + " "

    tags = []
    # Common development tags
    keywords = {
        'bug': 'bug-fix',
        'fix': 'bug-fix',
        'feature': 'feature-development',
        'implement': 'feature-development',
        'refactor': 'refactoring',
        'test': 'testing',
        'review': 'code-review',
        'deploy': 'deployment',
        'debug': 'debugging',
        'api': 'api',
        'documentation': 'documentation',
        'help': 'help',
        'explain': 'explanation',
    }

    for keyword, tag in keywords.items():
        if keyword in all_text and tag not in tags:
            tags.append(tag)

    return tags[:5]  # Limit to 5 tags


def to_markdown(messages: List[Dict[str, Any]], metadata: Dict[str, Any]) -> str:
    """Convert conversation to Markdown format."""
    title = metadata.get('title', 'Untitled Conversation')
    date = metadata.get('date', datetime.now().strftime('%Y-%m-%d'))
    tags = metadata.get('tags', [])
    session_id = metadata.get('session_id', 'unknown')
    cwd = metadata.get('cwd', '')

    # Build YAML frontmatter
    frontmatter = [
        '---',
        f'title: "{title}"',
        f'date: {date}',
        f'tags: {json.dumps(tags)}',
        f'session_id: {session_id}',
    ]
    if cwd:
        frontmatter.append(f'project: {cwd}')
    frontmatter.append('---')

    # Build markdown content
    output = []
    output.append('\n'.join(frontmatter))
    output.append('')
    output.append(f'# {title}')
    output.append('')
    output.append(f'**Session ID**: `{session_id}`')
    output.append(f'**Date**: {date}')
    output.append(f'**Messages**: {metadata.get("message_count", len(messages))}')
    if tags:
        output.append(f'**Tags**: {", ".join(tags)}')
    output.append('')
    output.append('---')
    output.append('')

    # Group messages by type
    current_role = None
    current_content = []

    for msg in messages:
        # Get type from role field (actual format) or type field (fallback)
        role_value = msg.get('role') or msg.get('type')

        # Map message types to roles
        if role_value == 'user':
            role = '## User'
        elif role_value == 'assistant':
            role = '## Claude'
        elif role_value == 'tool_use':
            role = '## Tool Use'
        elif role_value == 'tool_result':
            role = '## Tool Result'
        else:
            continue

        content = extract_content(msg)
        if not content:
            continue

        # If role changed, output previous content
        if current_role and current_role != role:
            if current_content:
                output.append('\n'.join(current_content))
                output.append('')
                output.append('---')
                output.append('')
            current_content = []

        current_role = role
        if not current_content:
            current_content.append(role)
            current_content.append('')

        # Add content (preserve line breaks)
        current_content.append(content)

    # Output last section
    if current_content:
        output.append('\n'.join(current_content))

    return '\n'.join(output)


def update_index(output_dir: Path, session_id: str, metadata: Dict[str, Any]) -> None:
    """Update the index.md file with new conversation."""
    index_path = output_dir / 'index.md'

    # Create index if it doesn't exist
    if not index_path.exists():
        index_content = [
            '# Conversation Index\n',
            '\n',
            'This index contains all exported Claude Code conversations.\n',
            '\n',
            '## Conversations\n',
            '\n',
        ]
    else:
        with open(index_path, 'r', encoding='utf-8') as f:
            index_content = f.readlines()

    # Add new entry
    date = metadata.get('date', datetime.now().strftime('%Y-%m-%d'))
    title = metadata.get('title', 'Untitled')
    tags = metadata.get('tags', [])

    # Calculate relative path: YYYY/MM-DD/session-id.md
    year = date[:4]
    month = date[5:7]
    day = date[8:10]
    rel_path = f"{year}/{month}-{day}/{session_id}.md"

    entry = f"- [{date}] [{title}]({rel_path})"
    if tags:
        entry += f" - {', '.join(tags)}"
    entry += '\n'

    # Insert after header
    insert_pos = len(index_content)
    for i, line in enumerate(index_content):
        if '## Conversations' in line:
            insert_pos = i + 2
            break

    index_content.insert(insert_pos, entry)

    # Write back
    with open(index_path, 'w', encoding='utf-8') as f:
        f.writelines(index_content)


def save_conversation(
    markdown: str,
    output_dir: str,
    session_id: str,
    metadata: Dict[str, Any]
) -> None:
    """Save conversation to organized directory structure."""
    output_path = Path(output_dir)
    date = metadata.get('date', datetime.now().strftime('%Y-%m-%d'))

    # Parse date for directory structure
    year = date[:4]
    month = date[5:7]
    day = date[8:10]

    # Create date-based directory: YYYY/MM-DD/
    date_dir = output_path / year / f"{month}-{day}"
    date_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename: session-id.md
    filename = f"{session_id}.md"
    filepath = date_dir / filename

    # Write markdown file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(markdown)

    print(f"Exported: {filepath}", file=sys.stderr)

    # Update index
    update_index(output_path, session_id, metadata)


def main():
    # Check if we're receiving JSON from stdin (hook mode)
    if len(sys.argv) == 1 and not sys.stdin.isatty():
        # Hook mode: read JSON from stdin
        try:
            hook_data = json.load(sys.stdin)
            session_id = hook_data.get('session_id', '')
            transcript_path = hook_data.get('transcript_path', '')
            cwd = hook_data.get('cwd', '')
        except json.JSONDecodeError as e:
            print(f"Error parsing hook JSON: {e}", file=sys.stderr)
            return 1

        if not session_id or not cwd:
            print("Error: Missing session_id or cwd in hook data", file=sys.stderr)
            return 1

        output_dir = f"{cwd}/.claude/history"
        state_file = f"{output_dir}/.exported_state"

        # Create export directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Check if already exported
        if Path(state_file).exists():
            with open(state_file, 'r') as f:
                if session_id in f.read():
                    return 0

        # Export if transcript exists
        if transcript_path and Path(transcript_path).exists():
            messages = parse_transcript(transcript_path)
            if messages:
                now = datetime.now()
                metadata = {
                    'session_id': session_id,
                    'date': now.strftime('%Y-%m-%d'),
                    'message_count': len(messages),
                    'cwd': cwd,
                }
                metadata['title'] = generate_title(messages, session_id)
                metadata['tags'] = extract_tags(messages)
                markdown = to_markdown(messages, metadata)
                save_conversation(markdown, output_dir, session_id, metadata)

        # Record as exported
        with open(state_file, 'a') as f:
            f.write(f"{session_id}\n")

        return 0

    # Normal CLI mode
    parser = argparse.ArgumentParser(
        description='Export Claude Code conversation to Markdown'
    )
    parser.add_argument('--session-id', required=True, help='Session identifier')
    parser.add_argument('--transcript', required=True, help='Path to JSONL transcript file')
    parser.add_argument('--output', required=True, help='Output directory')
    parser.add_argument('--cwd', help='Current working directory (project path)')
    args = parser.parse_args()

    # Parse transcript
    messages = parse_transcript(args.transcript)
    if not messages:
        print("No messages found in transcript", file=sys.stderr)
        return 1

    # Generate metadata
    now = datetime.now()
    metadata = {
        'session_id': args.session_id,
        'date': now.strftime('%Y-%m-%d'),
        'message_count': len(messages),
        'cwd': args.cwd,
    }

    # Extract title and tags
    metadata['title'] = generate_title(messages, args.session_id)
    metadata['tags'] = extract_tags(messages)

    # Convert to markdown
    markdown = to_markdown(messages, metadata)

    # Save to file
    save_conversation(markdown, args.output, args.session_id, metadata)

    return 0


if __name__ == '__main__':
    sys.exit(main())
