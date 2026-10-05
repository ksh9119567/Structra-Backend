import os
import sys


def main():
    """Run administrative tasks."""
    # `manage.py test` runs against config.settings_test (in-memory DB, fake
    # Redis, eager Celery) so tests never need - or touch - real services.
    # Export DJANGO_SETTINGS_MODULE yourself to override.
    default_settings = 'config.settings_test' if sys.argv[1:2] == ['test'] else 'config.settings'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', default_settings)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
