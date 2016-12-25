#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from coroweb import url_route
from models import User

__author__ = "Vic Yue"

""" define url handler with @url_route(path, method)"""


@url_route("/")
async def index():
    users = await User.find_all()
    return {
        "__template__": "test.html",
        "users": users
    }
