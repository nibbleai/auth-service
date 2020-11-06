import json
import time

COOKIE_NAME = 'nibble_auth_token'
COOKIE_LIFETIME = 3600 * 24 * 7  # 7 days

WORKDIR_CONFIG_KEY = 'working_dir'
TOKEN_CONFIG_KEY = 'token'

CONFIG_LOCATION = '/etc/nibble/config.json'
CONFIG = {}  # to be updated at runtime

# If the expected folder is not found, redirect users to home directory
FALLBACK_LOCATION = '/home'


class Service:
    VSCODE = 'vscode'
    NOTEBOOK = 'notebook'
    TERMINAL = 'terminal'


def build_cookie(host: str, token: str) -> dict:
    # Remove suffix corresponding to port number, if any
    domain = host.split(':')[0] if ':' in host else host
    return {
        'name': COOKIE_NAME,
        'value': token,
        'domain': domain,
        'expires': time.time() + COOKIE_LIFETIME
    }


def update_config():
    global CONFIG
    try:
        with open(CONFIG_LOCATION, 'rb') as fp:
            runtime_config = json.load(fp)
    except FileNotFoundError:
        return

    CONFIG.update(runtime_config)


def get_path_suffix(service: str, folder: str) -> str:
    """Return the URL suffix to redirect users to expected location."""
    if service == Service.VSCODE:
        working_dir = CONFIG.get(WORKDIR_CONFIG_KEY)
        if working_dir is None:
            return FALLBACK_LOCATION
        return f'?folder={working_dir}/{folder}'

    elif service == Service.NOTEBOOK:
        # Path is already relative to the working dir, because that's where
        # the notebook service is started from.
        return f'/tree/{folder}'

    return ''
