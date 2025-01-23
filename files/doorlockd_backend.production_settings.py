# doorlockd_backend/settings.py

# import default settings
from .settings import *

# mail exceptions:
ADMINS = [('Doorlockd Development Team','doorlockd@dewar.nl')]
EMAIL_HOST = 'mail.dewar.nl'
SERVER_EMAIL = 'Doorlockd Development Team <doorlockd@dewar.nl>'

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}