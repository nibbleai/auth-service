#!/usr/bin/env python
from collections import defaultdict
from logging import getLogger

import tornado.ioloop
import tornado.web

from .base import *

AUTH_SERVICE_ENDPOINT = '/auth'
AUTH_SERVICE_PORT = 10001

# Redirect to notebook service by default
SERVICE_PATH_MAPPING = defaultdict(lambda: '/notebook')
SERVICE_PATH_MAPPING.update({
    Service.NOTEBOOK: '/notebook',
    Service.VSCODE: '/vscode',
    Service.TERMINAL: '/notebook/terminals/1'
})

logger = getLogger(__name__)


class AuthHandler(tornado.web.RequestHandler):
    """Main handler to set an auth cookie in exange of a URL query param."""
    def get(self):
        token = self.get_argument('token', strip=True)
        if token != CONFIG.get(TOKEN_CONFIG_KEY, ''):
            logger.error("Authentication failed.")
            raise tornado.web.HTTPError(403)

        logger.info("Authentication succeeded.")
        cookie_data = build_cookie(self.request.host, token)
        self.set_cookie(**cookie_data)

        service = self.get_argument('service', Service.NOTEBOOK).lower()
        redirect_to = SERVICE_PATH_MAPPING[service]

        folder = self.get_argument('folder', '')
        if folder:
            suffix = get_path_suffix(service, folder)
            redirect_to += suffix

        logger.info("Redirecting...")
        self.redirect(redirect_to, permanent=False)


def main():
    ioloop = tornado.ioloop.IOLoop.current()

    app = tornado.web.Application([
        (AUTH_SERVICE_ENDPOINT, AuthHandler)
    ])
    app.listen(AUTH_SERVICE_PORT)

    ioloop.start()


if __name__ == '__main__':
    update_config()
    main()
