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

__all__ = ['AuthHandler', 'update_config']


class Service:
    VSCODE = 'vscode'
    NOTEBOOK = 'notebook'
    TERMINAL = 'terminal'


class AuthHandler(tornado.web.RequestHandler):
    """Main handler to set an auth cookie in exange of a URL query param."""
    def prepare(self) -> None:
        self._auth_token = CONFIG.get(TOKEN_CONFIG_KEY, '')
        self.authenticate()

    def authenticate(self) -> None:
        token = self.get_argument('token', None, strip=True)
        if token == self._auth_token:
            logger.info("Authentication succeeded.")
            return
        logger.error("Authentication failed.")
        raise tornado.web.HTTPError(403)

    def get(self) -> None:
        # At this point, an unauthorized user would already be rejected.
        cookie = self.get_cookie(COOKIE_NAME)
        if cookie != self._auth_token:
            # This browser either does not have the authentication cookie set,
            # or has an old one. In both cases, it needs a fresh cookie.
            cookie_data = build_cookie(self.request.host, self._auth_token)
            self.set_cookie(**cookie_data)

        service = self.get_argument('service', Service.NOTEBOOK).lower()
        folder = self.get_argument('folder', '')

        redirect_to = get_redirection_path(service)
        suffix = get_path_suffix(service, folder)
        redirect_to += suffix

        logger.info("Redirecting...")
        self.redirect(redirect_to, permanent=False)


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
