"""
Script to inspect OTPs and refresh tokens stored in Redis.

Usage:
    python scripts/inspect_redis_data.py          # Show all OTP and token data
    python scripts/inspect_redis_data.py email    # Show only email OTPs
    python scripts/inspect_redis_data.py phone    # Show only phone OTPs
    python scripts/inspect_redis_data.py refresh  # Show only refresh tokens
    python scripts/inspect_redis_data.py login    # Show only login OTPs
    python scripts/inspect_redis_data.py verify   # Show only verify OTPs
    python scripts/inspect_redis_data.py password # Show only password reset OTPs
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.conf import settings

redis_client = settings.REDIS_CLIENT


def format_ttl(seconds):
    """Format TTL in human-readable format."""
    if seconds < 0:
        return "Expired"
    elif seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    else:
        return f"{seconds // 3600}h {(seconds % 3600) // 60}m"


def show_all():
    """Show all Redis keys."""
    all_keys = redis_client.keys("*")
    
    print("\n" + "=" * 80)
    print(" " * 20 + "REDIS DATA INSPECTION")
    print("=" * 80 + "\n")
    
    # OTP keys by purpose and kind
    login_email_otps = [k for k in all_keys if k.startswith("otp:login:email:") and ":attempts" not in k]
    login_phone_otps = [k for k in all_keys if k.startswith("otp:login:phone:") and ":attempts" not in k]
    
    verify_email_otps = [k for k in all_keys if k.startswith("otp:verify:email:") and ":attempts" not in k]
    verify_phone_otps = [k for k in all_keys if k.startswith("otp:verify:phone:") and ":attempts" not in k]
    
    password_email_otps = [k for k in all_keys if k.startswith("otp:password:email:") and ":attempts" not in k]
    password_phone_otps = [k for k in all_keys if k.startswith("otp:password:phone:") and ":attempts" not in k]
    
    # Attempt counters
    all_attempts = [k for k in all_keys if k.endswith(":attempts") and k.startswith("otp:")]
    
    # Refresh tokens
    refresh_tokens = [k for k in all_keys if k.startswith("refresh:")]
    
    # Reset tokens
    reset_tokens = [k for k in all_keys if k.startswith("password_reset_token:")]
    
    print("🔐 LOGIN OTP CODES:")
    print("-" * 80)
    if login_email_otps or login_phone_otps:
        for key in login_email_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            email = key.replace("otp:login:email:", "")
            print(f"  Email: {email}")
            print(f"  Code:  {val}")
            print(f"  TTL:   {format_ttl(ttl)}\n")
        for key in login_phone_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            phone = key.replace("otp:login:phone:", "")
            print(f"  Phone: {phone}")
            print(f"  Code:  {val}")
            print(f"  TTL:   {format_ttl(ttl)}\n")
    else:
        print("  (None)\n")
    
    print("✅ VERIFY OTP CODES:")
    print("-" * 80)
    if verify_email_otps or verify_phone_otps:
        for key in verify_email_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            email = key.replace("otp:verify:email:", "")
            print(f"  Email: {email}")
            print(f"  Code:  {val}")
            print(f"  TTL:   {format_ttl(ttl)}\n")
        for key in verify_phone_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            phone = key.replace("otp:verify:phone:", "")
            print(f"  Phone: {phone}")
            print(f"  Code:  {val}")
            print(f"  TTL:   {format_ttl(ttl)}\n")
    else:
        print("  (None)\n")
    
    print("🔑 PASSWORD RESET OTP CODES:")
    print("-" * 80)
    if password_email_otps or password_phone_otps:
        for key in password_email_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            email = key.replace("otp:password:email:", "")
            print(f"  Email: {email}")
            print(f"  Code:  {val}")
            print(f"  TTL:   {format_ttl(ttl)}\n")
        for key in password_phone_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            phone = key.replace("otp:password:phone:", "")
            print(f"  Phone: {phone}")
            print(f"  Code:  {val}")
            print(f"  TTL:   {format_ttl(ttl)}\n")
    else:
        print("  (None)\n")
    
    print("📊 ATTEMPT COUNTERS:")
    print("-" * 80)
    if all_attempts:
        for key in all_attempts:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            print(f"  {key}: {val} attempts (TTL: {format_ttl(ttl)})")
        print()
    else:
        print("  (None)\n")
    
    print("🎟️  REFRESH TOKENS:")
    print("-" * 80)
    if refresh_tokens:
        print(f"  Total: {len(refresh_tokens)} active refresh tokens\n")
        for key in refresh_tokens[:5]:  # Show first 5
            user_id = redis_client.get(key)
            ttl = redis_client.ttl(key)
            token_preview = key[:50] + "..."
            print(f"  Token: {token_preview}")
            print(f"  User:  {user_id}")
            print(f"  TTL:   {format_ttl(ttl)}\n")
        if len(refresh_tokens) > 5:
            print(f"  ... and {len(refresh_tokens) - 5} more refresh tokens\n")
    else:
        print("  (None)\n")
    
    print("🔓 PASSWORD RESET TOKENS:")
    print("-" * 80)
    if reset_tokens:
        for key in reset_tokens:
            user_id = redis_client.get(key)
            ttl = redis_client.ttl(key)
            print(f"  Token: {key}")
            print(f"  User:  {user_id}")
            print(f"  TTL:   {format_ttl(ttl)}\n")
    else:
        print("  (None)\n")
    
    print("=" * 80)


def show_email():
    """Show only email OTPs."""
    all_keys = redis_client.keys("otp:*:email:*")
    email_otps = [k for k in all_keys if ":attempts" not in k]
    
    print("\n📧 EMAIL OTP CODES:\n")
    if email_otps:
        for key in email_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            # Extract identifier (everything after the last ':')
            parts = key.split(":")
            purpose = parts[1]  # e.g., 'login', 'verify', 'password'
            identifier = ":".join(parts[3:])  # Everything after 'email:'
            print(f"  Purpose:  {purpose}")
            print(f"  Email:    {identifier}")
            print(f"  Code:     {val}")
            print(f"  TTL:      {format_ttl(ttl)}\n")
    else:
        print("  (No email OTPs found)\n")


def show_phone():
    """Show only phone OTPs."""
    all_keys = redis_client.keys("otp:*:phone:*")
    phone_otps = [k for k in all_keys if ":attempts" not in k]
    
    print("\n📞 PHONE OTP CODES:\n")
    if phone_otps:
        for key in phone_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            # Extract identifier (everything after the last ':')
            parts = key.split(":")
            purpose = parts[1]  # e.g., 'login', 'verify', 'password'
            identifier = ":".join(parts[3:])  # Everything after 'phone:'
            print(f"  Purpose:  {purpose}")
            print(f"  Phone:    {identifier}")
            print(f"  Code:     {val}")
            print(f"  TTL:      {format_ttl(ttl)}\n")
    else:
        print("  (No phone OTPs found)\n")


def show_refresh():
    """Show only refresh tokens."""
    all_keys = redis_client.keys("refresh:*")
    
    print(f"\n🎟️  REFRESH TOKENS ({len(all_keys)} total):\n")
    if all_keys:
        for key in all_keys:
            user_id = redis_client.get(key)
            ttl = redis_client.ttl(key)
            token_preview = key[:50] + "..."
            print(f"  Token: {token_preview}")
            print(f"  User:  {user_id}")
            print(f"  TTL:   {format_ttl(ttl)}\n")
    else:
        print("  (No refresh tokens found)\n")


def show_login():
    """Show only login OTPs."""
    all_keys = redis_client.keys("otp:login:*")
    login_otps = [k for k in all_keys if ":attempts" not in k]
    
    print("\n🔐 LOGIN OTP CODES:\n")
    if login_otps:
        for key in login_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            kind = key.split(":")[2]  # email or phone
            identifier = ":".join(key.split(":")[3:])
            print(f"  Kind:       {kind}")
            print(f"  Identifier: {identifier}")
            print(f"  Code:       {val}")
            print(f"  TTL:        {format_ttl(ttl)}\n")
    else:
        print("  (No login OTPs found)\n")


def show_verify():
    """Show only verify OTPs."""
    all_keys = redis_client.keys("otp:verify:*")
    verify_otps = [k for k in all_keys if ":attempts" not in k]
    
    print("\n✅ VERIFY OTP CODES:\n")
    if verify_otps:
        for key in verify_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            kind = key.split(":")[2]  # email or phone
            identifier = ":".join(key.split(":")[3:])
            print(f"  Kind:       {kind}")
            print(f"  Identifier: {identifier}")
            print(f"  Code:       {val}")
            print(f"  TTL:        {format_ttl(ttl)}\n")
    else:
        print("  (No verify OTPs found)\n")


def show_password():
    """Show only password reset OTPs."""
    all_keys = redis_client.keys("otp:password:*")
    password_otps = [k for k in all_keys if ":attempts" not in k]
    
    print("\n🔑 PASSWORD RESET OTP CODES:\n")
    if password_otps:
        for key in password_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            kind = key.split(":")[2]  # email or phone
            identifier = ":".join(key.split(":")[3:])
            print(f"  Kind:       {kind}")
            print(f"  Identifier: {identifier}")
            print(f"  Code:       {val}")
            print(f"  TTL:        {format_ttl(ttl)}\n")
    else:
        print("  (No password reset OTPs found)\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "email":
            show_email()
        elif arg == "phone":
            show_phone()
        elif arg == "refresh":
            show_refresh()
        elif arg == "login":
            show_login()
        elif arg == "verify":
            show_verify()
        elif arg == "password":
            show_password()
        else:
            print(f"Unknown argument: {arg}")
            print("Use: email, phone, refresh, login, verify, or password")
    else:
        show_all()
