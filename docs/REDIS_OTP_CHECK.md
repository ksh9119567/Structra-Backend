# How to Check OTPs in Redis

## Quick Methods

### 1. Using the Python Script (Recommended)

```bash
# Show all OTP data
python scripts/inspect_redis_data.py

# Show only email OTPs
python scripts/inspect_redis_data.py email

# Show only phone OTPs
python scripts/inspect_redis_data.py phone

# Show only login OTPs
python scripts/inspect_redis_data.py login

# Show only verify OTPs
python scripts/inspect_redis_data.py verify

# Show only password reset OTPs
python scripts/inspect_redis_data.py password

# Show only refresh tokens
python scripts/inspect_redis_data.py refresh
```

### 2. Using Redis CLI Directly

```bash
# List all OTP keys
redis-cli KEYS "otp:*"

# Get specific OTP value
redis-cli GET "otp:email:test@example.com"

# Get OTP with TTL
redis-cli --csv KEYS "otp:*" | xargs -I {} redis-cli -x TTL {}

# List all keys (including refresh tokens)
redis-cli KEYS "*"

# Interactive Redis CLI
redis-cli
# Then type commands like:
# KEYS otp:*
# GET otp:email:test@example.com
# TTL otp:email:test@example.com
```

### 3. Using Python REPL in Django Shell

```bash
python manage.py shell
```

Then in the shell:

```python
from django.conf import settings
redis_client = settings.REDIS_CLIENT

# Get all OTP keys
redis_client.keys("otp:*")

# Get specific login OTP
redis_client.get("otp:login:email:test@example.com")

# Get verify OTP
redis_client.get("otp:verify:email:test@example.com")

# Get TTL
redis_client.ttl("otp:login:email:test@example.com")
```

## Redis Key Structure

### OTP Keys
```
otp:{purpose}:{type}:{identifier}
otp:login:email:user@example.com        # Login OTP (email)
otp:login:phone:9876543210              # Login OTP (phone)
otp:verify:email:user@example.com       # Email verification OTP
otp:verify:phone:9876543210             # Phone verification OTP
otp:password:email:user@example.com     # Password reset OTP (email)
otp:password:phone:9876543210           # Password reset OTP (phone)
```

### Attempt Counter Keys
```
otp:{purpose}:{type}:{identifier}:attempts
otp:login:email:user@example.com:attempts     # Failed login OTP attempts
otp:verify:email:user@example.com:attempts    # Failed verify OTP attempts
```

### Refresh Token Keys
```
refresh:{JWT_TOKEN}
```

### Reset Token Keys
```
password_reset_token:{TOKEN_UUID}
```

## Examples

### Get OTP for a user and verify it works

```bash
# 1. Request OTP
curl -X POST http://127.0.0.1:8000/api/accounts/otp/email/ \
  -H "Content-Type: application/json" \
  -d '{"kind":"email","identifier":"test@example.com","purpose":"login"}'

# 2. Check the OTP
python scripts/inspect_redis_data.py login

# 3. Use the OTP to verify
curl -X POST http://127.0.0.1:8000/api/accounts/otp/verify/ \
  -H "Content-Type: application/json" \
  -d '{"kind":"email","identifier":"test@example.com","otp":"233516"}'
```

## Redis Data Retention

- **OTP Codes**: 5 minutes (300 seconds) by default
- **Attempt Counters**: 5 minutes (300 seconds) window
- **Refresh Tokens**: 7 days by default
- **Password Reset Tokens**: 15 minutes (900 seconds)

## Useful Redis Commands

```bash
redis-cli FLUSHDB              # Delete all keys (use with caution!)
redis-cli FLUSHALL             # Delete all databases
redis-cli DBSIZE               # Show number of keys
redis-cli INFO                 # Show Redis info
redis-cli SCAN 0               # Scan all keys
redis-cli EXPIRE key 600       # Set key expiry to 600 seconds
redis-cli TTL key              # Get time to live for a key
redis-cli DEL key              # Delete a key
redis-cli MGET key1 key2       # Get multiple keys
```

## Troubleshooting

**Q: Script shows "No active OTP codes" even though I just requested one**
- OTPs expire after 5 minutes. Make sure to check immediately after requesting.

**Q: "Connection refused" error**
- Make sure Redis is running: `redis-cli ping` should return `PONG`

**Q: Can't find the email in the OTP key format**
- Use the exact email address used in the request
- Email addresses are case-sensitive in Redis keys
- Remember to use the new key format: `otp:{purpose}:{type}:{identifier}`

**Q: Want to clear all test data**
```bash
redis-cli FLUSHDB  # Delete all keys in current database
```
