#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import functools
import inspect

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


def has_request_argument(fn):
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


class RequestHandler(object):
    """
    Web Request Handler
    """

    def __init__(self, app, fn):
        self.app = app
        self._func = fn
        self._has_request_argument = has_request_argument(fn)

