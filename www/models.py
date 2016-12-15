#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid, time
from .orm import Model, StringField, BooleanField, IntegerField, TextField

__author__ = "Vic Yue"


def business_id():
    """
    Generate business id
    """
    return uuid.uuid4().hex


class User(Model):
    """
    User Model
    """
    __table__ = "t_users"

    id = StringField(primary_key=True, default=business_id)
    email = StringField(ddl="varchar(50)")
    passwd = StringField(ddl="varchar(50)")
    admin = BooleanField()
    name = StringField(ddl="varchar(50)")
    image = StringField(ddl="varchar(255)")
    create_at = IntegerField(default=lambda: int(time.time()))


class Blog(Model):
    """
    Blog Model
    """
    __table__ = "t_blogs"

    id = StringField(primary_key=True, default=business_id)
    user_id = StringField()
    name = StringField(ddl="varchar(50)")
    summary = StringField(ddl="varchar(200)")
    content = TextField()
    image = StringField(ddl="varchar(255)")
    create_at = IntegerField(default=lambda: int(time.time()))


class Comment(Model):
    """
    Comment Model
    """
    __table__ = "t_comments"

    id = StringField(primary_key=True, default=business_id)
    blog_id = StringField()
    user_id = StringField()
    content = TextField()
    create_at = IntegerField(default=lambda: int(time.time()))
