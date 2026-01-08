#!/usr/bin/env python3
"""
Security check script for GeminiBridge
Checks dependencies, configuration, and file permissions
"""
import os
import subprocess
import sys
from pathlib import Path


def check_dependencies():
    """Check for known vulnerabilities in dependencies"""
    try:
        result = subprocess.run(
            ["pip-audit", "--desc"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print("⚠️  Security vulnerabilities found:")
            print(result.stdout)
            return False
        else:
            print("✅ No known vulnerabilities in dependencies")
            return True
    except FileNotFoundError:
        print("⚠️  pip-audit not installed. Run: pip install pip-audit")
        return None
    except Exception as e:
        print(f"❌ Error checking dependencies: {e}")
        return False


def check_env_file():
    """Check .env file security"""
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  .env file not found")
        return False
    
    # Check file permissions (Unix-like systems only)
    if os.name != 'nt':  # Not Windows
        try:
            mode = env_file.stat().st_mode
            if mode & 0o077:  # Check group/other permissions
                print("⚠️  .env file has too permissive permissions")
                print("   Recommended: chmod 600 .env")
                return False
        except Exception as e:
            print(f"⚠️  Could not check .env permissions: {e}")
            return None
    
    print("✅ .env file permissions OK")
    return True


def check_bearer_token():
    """Check bearer token strength"""
    env_file = Path(".env")
    if not env_file.exists():
        return None
    
    try:
        with open(env_file, 'r') as f:
            content = f.read()
            
        # Check for default token
        if "your-secret-token-here-change-this-in-production" in content:
            print("⚠️  Default BEARER_TOKEN detected!")
            print("   Generate a strong token: python scripts/generate_token.py")
            return False
        
        # Extract token length (simple check)
        for line in content.split('\n'):
            if line.startswith('BEARER_TOKEN='):
                token = line.split('=', 1)[1].strip()
                if len(token) < 32:
                    print(f"⚠️  BEARER_TOKEN is too short ({len(token)} characters)")
                    print("   Recommended minimum: 32 characters")
                    return False
        
        print("✅ BEARER_TOKEN appears secure")
        return True
    except Exception as e:
        print(f"⚠️  Could not check BEARER_TOKEN: {e}")
        return None


def check_cli_path():
    """Check if Gemini CLI path is properly configured"""
    env_file = Path(".env")
    if not env_file.exists():
        return None
    
    try:
        with open(env_file, 'r') as f:
            content = f.read()
        
        for line in content.split('\n'):
            if line.startswith('GEMINI_CLI_PATH='):
                cli_path = line.split('=', 1)[1].strip()
                
                # Check if path exists (if not "gemini")
                if cli_path != "gemini":
                    path_obj = Path(cli_path)
                    if not path_obj.exists():
                        print(f"⚠️  GEMINI_CLI_PATH not found: {cli_path}")
                        return False
                
                print(f"✅ GEMINI_CLI_PATH configured: {cli_path}")
                return True
        
        print("⚠️  GEMINI_CLI_PATH not set, using default 'gemini'")
        return True
    except Exception as e:
        print(f"⚠️  Could not check GEMINI_CLI_PATH: {e}")
        return None


def main():
    """Main security check routine"""
    print("🔒 GeminiBridge Security Check\n")
    print("=" * 50)
    
    results = {}
    
    print("\n1. Checking dependencies...")
    results['dependencies'] = check_dependencies()
    
    print("\n2. Checking .env file...")
    results['env_file'] = check_env_file()
    
    print("\n3. Checking BEARER_TOKEN...")
    results['bearer_token'] = check_bearer_token()
    
    print("\n4. Checking GEMINI_CLI_PATH...")
    results['cli_path'] = check_cli_path()
    
    print("\n" + "=" * 50)
    
    # Determine overall status
    failures = [k for k, v in results.items() if v is False]
    warnings = [k for k, v in results.items() if v is None]
    
    if failures:
        print(f"\n❌ Security checks failed: {', '.join(failures)}")
        print("\nPlease address the issues above before deploying.")
        return 1
    elif warnings:
        print(f"\n⚠️  Some checks could not be completed: {', '.join(warnings)}")
        print("\n✅ No critical issues detected")
        return 0
    else:
        print("\n✅ All security checks passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
