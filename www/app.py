#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import asyncio
import logging
import os

from aiohttp import web

from www import orm
from jinja2 import Environment, FileSystemLoader

__author__ = "Vic Yue"

logging.basicConfig(level=logging.INFO)


def init_jinjia2(app, **kw):
    """
    Init server jinjia2 module
    :param app: web.Application object.
    :param kw: var named args.
    :return:
    """
    logging.info("Init jinjia2 ...")
    options = dict()
    path = kw.get("path", None)
    if not path:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    env = Environment()


async def init(loop):
    await orm.create_connection_pool()
    app = web.Application(loop=loop)
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
