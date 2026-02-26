import logging

logger = logging.getLogger(__name__)


class AuthManager:

    def __init__(self):
        logger.info("AuthManager initialized (no authentication required)")

    def get_headers(self):
        return {}
