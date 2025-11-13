"""
Script to inspect OTPs and refresh tokens stored in Redis.

Usage:
    python scripts/check_redis_otp.py          # Show all OTP and token data
    python scripts/check_redis_otp.py email    # Show only email OTPs
    python scripts/check_redis_otp.py phone    # Show only phone OTPs
    python scripts/check_redis_otp.py refresh  # Show only refresh tokens
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
    
    # OTP email
    email_otps = [k for k in all_keys if k.startswith("otp:email:") and ":attempts" not in k]
    email_attempts = [k for k in all_keys if k.startswith("otp:email:") and ":attempts" in k]
    
    # OTP phone
    phone_otps = [k for k in all_keys if k.startswith("otp:phone:") and ":attempts" not in k]
    phone_attempts = [k for k in all_keys if k.startswith("otp:phone:") and ":attempts" in k]
    
    # OTP login
    login_otps = [k for k in all_keys if k.startswith("otp:login:")]
    
    # OTP password
    password_otps = [k for k in all_keys if k.startswith("otp:password:")]
    
    # Refresh tokens
    refresh_tokens = [k for k in all_keys if k.startswith("refresh:")]
    
    # Reset tokens
    reset_tokens = [k for k in all_keys if k.startswith("password_reset_token:")]
    
    print("📧 EMAIL OTP CODES:")
    print("-" * 80)
    if email_otps:
        for key in email_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            email = key.replace("otp:email:", "")
            print(f"  Email: {email}")
            print(f"  Code:  {val}")
            print(f"  TTL:   {format_ttl(ttl)}\n")
    else:
        print("  (None)\n")
    
    print("📞 PHONE OTP CODES:")
    print("-" * 80)
    if phone_otps:
        for key in phone_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            phone = key.replace("otp:phone:", "")
            print(f"  Phone: {phone}")
            print(f"  Code:  {val}")
            print(f"  TTL:   {format_ttl(ttl)}\n")
    else:
        print("  (None)\n")
    
    print("🔐 LOGIN OTP CODES:")
    print("-" * 80)
    if login_otps:
        for key in login_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            print(f"  Key:  {key}")
            print(f"  Code: {val}")
            print(f"  TTL:  {format_ttl(ttl)}\n")
    else:
        print("  (None)\n")
    
    print("🔑 PASSWORD RESET OTP CODES:")
    print("-" * 80)
    if password_otps:
        for key in password_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            print(f"  Key:  {key}")
            print(f"  Code: {val}")
            print(f"  TTL:  {format_ttl(ttl)}\n")
    else:
        print("  (None)\n")
    
    print("📊 ATTEMPT COUNTERS:")
    print("-" * 80)
    all_attempts = email_attempts + phone_attempts
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
    all_keys = redis_client.keys("otp:email:*")
    email_otps = [k for k in all_keys if ":attempts" not in k]
    
    print("\n📧 EMAIL OTP CODES:\n")
    if email_otps:
        for key in email_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            email = key.replace("otp:email:", "")
            print(f"  Email: {email}")
            print(f"  Code:  {val}")
            print(f"  TTL:   {format_ttl(ttl)}\n")
    else:
        print("  (No email OTPs found)\n")


def show_phone():
    """Show only phone OTPs."""
    all_keys = redis_client.keys("otp:phone:*")
    phone_otps = [k for k in all_keys if ":attempts" not in k]
    
    print("\n📞 PHONE OTP CODES:\n")
    if phone_otps:
        for key in phone_otps:
            val = redis_client.get(key)
            ttl = redis_client.ttl(key)
            phone = key.replace("otp:phone:", "")
            print(f"  Phone: {phone}")
            print(f"  Code:  {val}")
            print(f"  TTL:   {format_ttl(ttl)}\n")
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


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "email":
            show_email()
        elif arg == "phone":
            show_phone()
        elif arg == "refresh":
            show_refresh()
        else:
            print(f"Unknown argument: {arg}")
            print("Use: email, phone, or refresh")
    else:
        show_all()
