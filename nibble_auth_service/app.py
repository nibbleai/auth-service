#!/usr/bin/env python
import tornado.ioloop
import tornado.web

from .base import AuthHandler, update_config, logger

AUTH_SERVICE_ENDPOINT = '/auth'
AUTH_SERVICE_PORT = 10001


def main():
    ioloop = tornado.ioloop.IOLoop.current()

    app = tornado.web.Application([
        (AUTH_SERVICE_ENDPOINT, AuthHandler)
    ])
    app.listen(AUTH_SERVICE_PORT)

    ioloop.start()


if __name__ == '__main__':
    update_config()
    logger.info("Starting authentication service...")
    main()
