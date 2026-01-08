"""
Prompt builder utility
Converts OpenAI messages format to Gemini CLI prompt format
"""

from typing import List, Tuple

MAX_MESSAGES = 20  # Prevent oversized prompts (matches Node.js behavior)


class Message:
    """Message model matching OpenAI format"""
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


def build_prompt(messages: List[dict]) -> str:
    """
    Build a Gemini CLI prompt from OpenAI messages array

    Format:
    [System]
    system message content

    [User]
    user message content

    [Assistant]
    assistant message content

    Args:
        messages: List of message dicts with 'role' and 'content' keys

    Returns:
        Formatted prompt string
    """
    # Limit conversation history to last MAX_MESSAGES (prevent oversized prompts)
    limited_messages = messages[-MAX_MESSAGES:] if len(messages) > MAX_MESSAGES else messages

    prompt_parts: List[str] = []

    for message in limited_messages:
        role = message["role"].capitalize()
        content = message["content"]

        prompt_parts.append(f"[{role}]")
        prompt_parts.append(content)
        prompt_parts.append("")  # Empty line separator

    return "\n".join(prompt_parts).strip()


def validate_messages(messages: List[dict]) -> Tuple[bool, str | None]:
    """
    Validate messages array structure

    Args:
        messages: List of message dicts

    Returns:
        Tuple of (valid: bool, error_message: str | None)
    """
    if not isinstance(messages, list):
        return False, "Messages must be an array"

    if len(messages) == 0:
        return False, "Messages array cannot be empty"

    valid_roles = {"system", "user", "assistant"}

    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            return False, f"Message at index {i} must be an object"

        if "role" not in msg or "content" not in msg:
            return False, f"Message at index {i} missing required fields (role, content)"

        if msg["role"] not in valid_roles:
            return False, f"Message at index {i} has invalid role: {msg['role']}"

        if not isinstance(msg["content"], str):
            return False, f"Message at index {i} content must be a string"

    return True, None


def validate_request_size(messages: List[dict]) -> Tuple[bool, str | None]:
    """
    Validate request size constraints to prevent DoS attacks
    Matches Node.js behavior (100 messages max, 100K chars per message)

    Args:
        messages: List of message dicts

    Returns:
        Tuple of (valid: bool, error_message: str | None)
    """
    # Limit message array length (100 messages is very generous)
    if len(messages) > 100:
        return False, "Too many messages. Maximum 100 messages allowed."

    # Limit individual message content length
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str) and len(content) > 100000:
            return False, "Message content too long. Maximum 100,000 characters per message."

    return True, None
