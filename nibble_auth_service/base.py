from datetime import datetime, timedelta
import json
from logging import getLogger
import time

import tornado.web

logger = getLogger(__name__)

COOKIE_NAME = 'nibble_auth_token'
COOKIE_LIFETIME = 3600 * 24 * 7  # 7 days

CONFIG_LOCATION = '/etc/nibble/config.json'
CONFIG = {}  # to be updated at runtime

WORKDIR_CONFIG_KEY = 'working_dir'
TOKEN_CONFIG_KEY = 'token'

# If the expected folder is not found, redirect users to home directory
FALLBACK_LOCATION = '/home'

MAX_FAILURES = 5
PURGE_DELAY = 300  # 5 minutes

__all__ = ['AuthHandler', 'update_config']


class Service:
    VSCODE = 'vscode'
    NOTEBOOK = 'notebook'
    TERMINAL = 'terminal'


class AuthFailure:
    count = 0
    last_fail = None

    @classmethod
    def new(cls):
        cls.count += 1
        cls.last_fail = datetime.utcnow()

    @classmethod
    def reset(cls):
        cls.count = 0
        cls.last_fail = None


class AuthHandler(tornado.web.RequestHandler):
    """Main handler to set an auth cookie in exange of a URL query param."""
    AUTH_TOKEN = None

    def prepare(self) -> None:
        self.AUTH_TOKEN = CONFIG.get(TOKEN_CONFIG_KEY, '')
        self.authenticate()
        accepted = accept_new_auth_attempt()
        if not (accepted and self.authenticate()):
            raise tornado.web.HTTPError(403)

    def authenticate(self) -> bool:
        """Return True if request is authentified."""
        token = self.get_argument('token', None, strip=True)
        if token == self.AUTH_TOKEN:
            logger.info("Authentication succeeded.")
            return True

        logger.error("Authentication failed.")
        AuthFailure.new()
        return False

    def get(self) -> None:
        # At this point, an unauthorized user would already be rejected.
        cookie = self.get_cookie(COOKIE_NAME)
        if cookie != self.AUTH_TOKEN:
            # This browser either does not have the authentication cookie set,
            # or has an old one. In both cases, it needs a fresh cookie.
            cookie_data = build_cookie(self.request.host, self.AUTH_TOKEN)
            self.set_cookie(**cookie_data)

        service = self.get_argument('service', Service.NOTEBOOK).lower()
        folder = self.get_argument('folder', '')

        redirect_to = get_redirection_path(service)
        suffix = get_path_suffix(service, folder)
        redirect_to += suffix

        logger.info("Redirecting...")
        self.redirect(redirect_to, permanent=False)


def accept_new_auth_attempt() -> bool:
    """Return False if auth process is blocked for security reasons."""
    if (
        AuthFailure.count <= MAX_FAILURES
        or datetime.utcnow() > (AuthFailure.last_fail
                                + timedelta(seconds=PURGE_DELAY))
    ):
        AuthFailure.reset()
        return True

    return False


def build_cookie(host: str, token: str) -> dict:
    # Remove suffix corresponding to port number, if any
    domain = host.split(':')[0] if ':' in host else host
    return {
        'name': COOKIE_NAME,
        'value': token,
        'domain': domain,
        'expires': time.time() + COOKIE_LIFETIME
    }


def get_redirection_path(service: str) -> str:
    if service == Service.VSCODE:
        return '/vscode'
    if service == Service.TERMINAL:
        return '/notebook/terminals/1'
    return '/notebook'  # redirect to notebook service by default


def get_path_suffix(service: str, folder: str) -> str:
    """Return the URL suffix to redirect users to expected location."""
    if service == Service.VSCODE:
        working_dir = CONFIG.get(WORKDIR_CONFIG_KEY)
        if working_dir is None:
            return FALLBACK_LOCATION
        else:
            return f'?folder={working_dir}/{folder}'
    elif service == Service.NOTEBOOK:
        # Path is already relative to the working dir, because that's where
        # the notebook service is started from.
        return f'/tree/{folder}'

    return ''


def update_config() -> None:
    global CONFIG
    try:
        with open(CONFIG_LOCATION, 'rb') as fp:
            runtime_config = json.load(fp)
    except FileNotFoundError:
        return

    CONFIG.update(runtime_config)
