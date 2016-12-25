#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import functools
import inspect
import logging
import os
from urllib import parse

from aiohttp import web

from apis import APIError

__author__ = "Vic Yue"


def url_route(path, method="GET"):
    """
    Define decorator @url_route("/path", method="GET")
    :param path: url deal path
    :param method: request method
    :return:
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)

        assert method in ("GET", "POST", "DELETE", "PUT", "OPTION")
        wrapper.__method__ = method
        wrapper.__route__ = path
        return wrapper

    return decorator


def has_request_args(fn):
    sign = inspect.signature(fn)
    params = sign.parameters
    found = False
    for name, param in params.items():
        if name == "request":
            found = True
            continue
        if found and (param.kind not in (
                inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.VAR_KEYWORD)):
            raise ValueError("Request parameter must be the last named parameter in function: %s:%s"
                             % (fn.__name__, str(sign)))
        return found


def has_named_kw_args(fn):
    flg = False
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            flg = True
            return flg
    return flg


def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)


def has_var_kw_arg(fn):
    flg = False
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            flg = True
            return flg
    return flg


def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)


class RequestHandler(object):
    """
    Web Request Handler
    """

    def __init__(self, app, fn):
        self.app = app
        self._func = fn
        self._has_request_args = has_request_args(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

    async def __call__(self, request):
        kw = None
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            if request.method == "POST":
                ct = request.content_type
                if not ct:
                    return web.HTTPBadRequest("Missing Content-Type.")
                ct = ct.lower()
                if ct.startswith("application/json"):
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest("JSON body must be object.")
                    kw = params
                elif ct.startswith("application/x-www-form-urlencoded") or ct.startswith("multipart/form-data"):
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest("Unsupported Content-Type: %s" % ct)
            elif request.method == "GET":
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                # remove all unnamed kw:
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            # check named args:
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning("Duplicate arg in named arg and kw args: %s" % k)
                kw[k] = v
        if self._has_request_args:
            kw["request"] = request
        # check required kw
        if self._required_kw_args:
            for name in self._required_kw_args:
                if name not in kw:
                    return web.HTTPBadRequest("Missing required argument: %s" % name)
        logging.info("Call with args: %s" % str(kw))
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)


def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    app.router.add_static("/static/", path)
    logging.info("add static /static/ -> %s." % path)


def add_route(app, fn):
    method = getattr(fn, "__method__", None)
    path = getattr(fn, "__route__", None)
    if method is None or path is None:
        raise ValueError("@url_route was not defined on %s" % str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info(
        "add router %s %s -> %s(%s)." % (method, path, fn.__name__, ", ".join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))


def add_routes(app, module_name):
    """
    auto scan specify modules
    :param app:
    :param module_name:
    :return:
    """
    assert isinstance(module_name, str)
    modules = module_name.split(".")
    if len(modules) == 1:
        mod = __import__(modules[0], globals(), locals())
    else:
        mod = getattr(__import__(modules[0], globals(), locals(), (modules[1])), modules[1])
    for attr in dir(mod):
        if attr.startswith("_"):
            continue
        fn = getattr(mod, attr)
        if callable(fn) and hasattr(fn, "__method__") and hasattr(fn, "__route__"):
            add_route(app, fn)
