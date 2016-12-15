#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import asyncio
import logging

from aiohttp import web

__author__ = "Vic Yue"

logging.basicConfig(level=logging.INFO)


async def index(req):
    return web.Response(body=b"<h1>Awesome python</h1>", content_type="text/html")


async def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route("GET", "/", index)
    host, port = ("127.0.0.1", 9000)
    srv = await loop.create_server(app.make_handler(), host, port)
    logging.info("Server is running at http://%s:%s" % (host, port))
    return srv


def run_server():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(loop))
    loop.run_forever()


if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        logging.info("Press ctrl+c shutting down server")
