"""
Shared test tooling: an in-memory Redis double and a base TestCase with
factories, so every app's tests can build users / orgs / teams / projects and
call the API as a real, token-authenticated user.

Run the suite with:  python manage.py test
(see docs/TESTING.md for per-app commands).
"""
