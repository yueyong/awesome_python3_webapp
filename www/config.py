#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import config_default as default

__author__ = "Vic Yue"

"""web server config file"""


class Dict(dict):
    """Simple dict support access d.x style."""
    def __init__(self, names=(), values=(), **kw):
        super().__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError("'Dict' has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value


def merge(defaults, overrides):
    r = {}
    for k, v in defaults.items():
        if k in overrides:
            if isinstance(v, dict):
                r[k] = merge(v, overrides[k])
            else:
                r[k] = overrides[k]
        else:
            r[k] = v
    return r


def to_dict(d):
    r = Dict()
    for k, v in d.items():
        r[k] = to_dict(v) if isinstance(v, dict) else v
    return r

configs = default.configs

try:
    import config_override as override
    configs = merge(configs, override.configs)
except ImportError:
    pass

configs = to_dict(configs)
