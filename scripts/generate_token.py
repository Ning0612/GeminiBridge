#!/usr/bin/env python3
"""
Generate secure bearer token for GeminiBridge
"""
import secrets
import sys


def generate_token(length: int = 32) -> str:
    """Generate URL-safe token"""
    return secrets.token_urlsafe(length)


if __name__ == "__main__":
    # Allow custom length from command line
    length = 32
    if len(sys.argv) > 1:
        try:
            length = int(sys.argv[1])
            if length < 16:
                print("⚠️  WARNING: Token length should be at least 16 characters")
                length = 16
        except ValueError:
            print("Using default length: 32")
    
    token = generate_token(length)
    print(f"Generated Bearer Token ({len(token)} characters):")
    print(token)
    print("\nAdd this to your .env file:")
    print(f"BEARER_TOKEN={token}")
    print("\nFor strict mode (production), also add:")
    print("SECURITY_STRICT_MODE=true")
