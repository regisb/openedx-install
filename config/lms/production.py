from .aws import *
MEDIA_ROOT = "/opt/openedx/uploads/" # FIXME
FEATURES['ENABLE_DISCUSSION_SERVICE'] = False

ALLOWED_HOSTS = [
    ENV_TOKENS.get('LMS_BASE'),
    FEATURES['PREVIEW_LMS_BASE'],
]
