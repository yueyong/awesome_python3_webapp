#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import asyncio
import json
import logging
import os
import time
from datetime import datetime

from aiohttp import web
from jinja2 import Environment, FileSystemLoader

import orm
import coroweb
from config import configs

__author__ = "Vic Yue"

logging.basicConfig(level=logging.INFO)


def init_jinja2(app, *, path=None, filters=None):
    """
    Init server jinja2 module
    :param app: web.Application object.
    :param path: jinja2 template path.
    :param filters: jinja2 convert filters.
    :return:
    """
    logging.info("Init jinja2 ...")
    options = dict(auto_reload=True,
                   block_start_string="{%",
                   block_end_string="%}",
                   variable_start_string="{{",
                   variable_end_string="}}",
                   autoescape=True)
    if not path:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    logging.info("set jinja2 template path: %s" % path)
    env = Environment(loader=FileSystemLoader(path), **options)
    if filters is not None and isinstance(filters, dict):
        for name, filter_func in filters.items():
            env.filters[name] = filter_func
    app["__templating__"] = env


async def logger_factory(app, handler):
    async def logger(request):
        assert isinstance(request, web.Request)
        logging.info("Request: %s: %s" % (request.method, request.path))
        return await handler(request)

    return logger


async def data_factory(app, handler):
    async def data_parse(request):
        assert isinstance(request, web.Request)
        if request.method == "POST":
            content = request.content_type
            if content.startswith("application/json"):
                request.__data__ = await request.json()
                logging.info("request with json: %s" % str(request.__data__))
            elif content.startswith("application/x-www-form-urlencoded"):
                request.__data__ = await request.post()
                logging.info("request with post: %s" % str(request.__data__))
        return await handler(request)

    return data_parse


async def response_factory(app, handler):
    async def response(request):
        assert isinstance(request, web.Request)
        logging.info("Response handler...")
        r = await handler(request)
        if isinstance(r, web.StreamResponse):
            return r
        elif isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = "application/octet-stream"
            return resp
        elif isinstance(r, str):
            redirect = "redirect:"
            if r.startswith(redirect):
                return web.HTTPFound(r[len(redirect) + 1:])
            resp = web.Response(body=r.encode())
            resp.content_type = "text/html;charset=utf-8"
            return resp
        elif isinstance(r, dict):
            template = r.get("__template__", None)
            if template is None:
                body = json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__)
                resp = web.Response(body=body.encode())
                resp.content_type = "application/json;charset=utf-8"
                return resp
            jinja_env = app["__templating__"]
            assert isinstance(jinja_env, Environment)
            body = jinja_env.get_template(template).render(**r)
            resp = web.Response(body=body.encode())
            resp.content_type = "text/html;charset=utf-8"
            return resp
        elif isinstance(r, int) and 100 <= r < 600:
            return web.Response(status=r)
        elif isinstance(r, tuple) and len(r) == 2:
            s, m = r
            if isinstance(s, int) and 100 <= s < 600:
                return web.Response(status=s, reason=str(m))
        else:
            resp = web.Response(body=str(r).encode())
            resp.content_type = "text/plain;charset=utf-8"
            return resp

    return response


def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:  # 1分钟
        return "1分钟前"
    elif delta < 60 * 60:  # 1小时内
        return "%s分钟前" % (delta // 60)
    elif delta < 60 * 60 * 24:  # 24小时内
        return "%s小时前" % (delta // (60 * 60))
    elif delta < 60 * 60 * 24 * 7:  # 1星期内
        return "%s天内" % (delta // (60 * 60 * 24))
    else:  # 一星期外
        dt = datetime.fromtimestamp(t)
        return "%s年%s月%s日" % (dt.year, dt.month, dt.day)


async def init(loop):
    await orm.create_connection_pool(loop, user=configs.db.user, password=configs.db.password, db=configs.db.database,
                                     host=configs.db.host)
    app = web.Application(loop=loop, middlewares=(
        logger_factory, data_factory, response_factory
    ))
    init_jinja2(app, filters={"datetime": datetime_filter})
    coroweb.add_routes(app, "handlers")
    coroweb.add_static(app)
    host = configs.web.host
    port = configs.web.port
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
