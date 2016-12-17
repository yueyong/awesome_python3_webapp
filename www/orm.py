#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import aiomysql

__author__ = "Vic Yue"

__pool = None


async def create_connection_pool(loop, **kw):
    """
    create global connection pool
    :param loop: default asyncio.get_event_loop()
    :param kw: kwargs
    :return:
    """
    logging.info("Creating connection pool...")
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get("host", "localhost"),
        port=kw.get("port", 3306),
        user=kw["user"],
        password=kw["password"],
        db=kw["db"],
        charset=kw.get("charset", "utf8"),
        autocommit=kw.get("autocommit", True),
        maxsize=kw.get("maxsize", 10),
        minsize=kw.get("minsize", 1),
        loop=loop
    )


async def select(sql, args, size=None):
    """
    select common method
    :param sql: select sql statement
    :param args: sql args
    :param size: fetch size, default all return
    :return: result dict
    """
    logging.info(sql, args)
    global __pool
    assert isinstance(__pool, aiomysql.Pool)
    async with __pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace("?", "%s"), args or ())
            if size and isinstance(size, int) and size > 0:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
            logging.info("select return size:%s" % len(rs))
            return rs


async def execute(sql, args, autocommit=True):
    """
    execute common method
    :param sql: insert, update, delete statement
    :param args: sql args
    :param autocommit: whether autocommit
    :return:
    """
    logging.info(sql, args)
    global __pool
    assert isinstance(__pool, aiomysql.Pool)
    async with __pool.acquire() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace("?", "%s"), args or ())
                affected = cur.rowcount
                if not autocommit:
                    await conn.commit()
        except BaseException:
            if not autocommit:
                await conn.rollback()
            raise
        return affected


class Field(object):
    """
    orm field class type
    """

    def __init__(self, name, column_type, primary_key, default, nullable):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self._default = default
        self.nullable = nullable

    @property
    def default(self):
        if callable(self._default):
            return self._default()
        return self._default

    def __str__(self):
        return "<%s, %s:%s>" % (self.__class__.__name__, self.column_type, self.name)


class IntegerField(Field):
    """
    orm integer field type
    """

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, "bigint", primary_key, default, False)


class StringField(Field):
    """
    orm string field type
    """

    def __init__(self, name=None, primary_key=False, default=None, ddl="varchar(32)"):
        super().__init__(name, ddl, primary_key, default, False)


class BooleanField(Field):
    """
    orm boolean field type
    """

    def __init__(self, name=None, default=False):
        super().__init__(name, "boolean", False, default, False)


class FloatField(Field):
    """
    orm float field type
    """

    def __init__(self, name=None, default=0.0):
        super().__init__(name, "real", False, default, False)


class TextField(Field):
    """
    orm text field type
    """

    def __init__(self, name=None, default=None):
        super().__init__(name, "text", False, default, False)


def _gen_sql(table_name, mappings, rebuild=True):
    """
    generate create table ddl
    :param table_name:
    :param mappings:
    :return:
    """
    assert isinstance(table_name, str) and isinstance(mappings, dict)
    if rebuild:
        sql = ["--DROP EXISTS TABLE: %s" % table_name, "DROP TABLE IF EXISTS `%s`;" % table_name]
    pk = None
    sql.append("CREATE TABLE `%s` (" % table_name)
    for v in mappings.values():
        if v.primary_key:
            pk = v.name
        ddl = []
        if not v.nullable:
            ddl.append("NOT NULL")
        sql.append("  `%s` %s %s" % (v.name, v.column_type, " ".join(ddl)))
    sql.append("  PRIMARY KEY(`%s`)" % pk)
    sql.append(");")
    return "\n".join(sql)


class ModelMetaclass(type):
    def __new__(mcs, name, bases, attrs):
        if name == "Model":
            return type.__new__(mcs, name, bases, attrs)
        table_name = attrs.get("__table__", None) or name.lower()
        logging.info("Found model: %s (table: %s)" % (name, table_name))
        mappings = {}
        primary_key = None
        fields = []
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info("found mappings %s: %s" % (k, v))
                if v.name is None:
                    v.name = k
                mappings[k] = v
                if v.primary_key:
                    if primary_key:
                        raise Exception("Duplicate primary key for field: %s" % k)
                    primary_key = k
                else:
                    fields.append(k)
        if not primary_key:
            raise Exception("Primary key not found.")
        for k in mappings.keys():
            attrs.pop(k)
        escaped_fields = ", ".join(["`%s`" % f for f in fields])
        attrs["__mappings__"] = mappings  # save model define column attributes
        attrs["__table__"] = table_name
        attrs["__primary_key__"] = primary_key
        attrs["__fields__"] = fields
        # insert sql
        attrs["__insert__"] = "INSERT INTO %s(%s, `%s`) VALUES (%s)" % (
            table_name, escaped_fields, primary_key,
            ", ".join(["?" for _ in range(len(fields) + 1)]))
        # update sql
        attrs["__update__"] = "UPDATE %s SET %s WHERE %s" % (
            table_name, ", ".join(["`%s`=?" % mappings.get(f).name or f for f in fields]), "`%s`=?" % primary_key)
        # delete sql
        attrs["__delete__"] = "DELETE FROM %s WHERE %s" % (table_name, "`%s`=?" % primary_key)
        # select sql
        attrs["__select__"] = "SELECT `%s`, %s FROM %s" % (primary_key, escaped_fields, table_name)
        attrs["__ddl_sql__"] = lambda: _gen_sql(table_name, mappings)
        return type.__new__(mcs, name, bases, attrs)


class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def get_value(self, key):
        return getattr(self, key, None)

    def get_value_or_default(self, key):
        value = self.get_value(key)
        if value is None:
            field = self.__mappings__[key]
            default = field.default
            if default is not None:
                value = default
                logging.info("using default value for %s: %s" % (key, value))
                setattr(self, key, value)
        return value

    @classmethod
    async def find(cls, pk):
        """
        find object by primary key's value
        :param pk: primary key's value
        :return:
        """
        ret = None
        if pk:
            rs = await select("%s WHERE `%s`=?" % (cls.__select__, cls.__primary_key__), [pk], 1)
            if len(rs) == 1:
                ret = cls(**rs[0])
        return ret

    async def save(self):
        """
        save object
        :return:
        """
        args = [self.get_value_or_default(f) for f in self.__fields__]
        args.append(self.get_value_or_default(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warning("failed to insert record: affected rows: %s" % rows)

    async def modify(self):
        """
        update object
        :return:
        """
        args = [self.get_value(f) for f in self.__fields__]
        args.append(self.get_value(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warning("failed to update by primary key: affected rows: %s" % rows)

    async def remove(self):
        """
        delete object
        :return:
        """
        args = [self.get_value(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warning("failed to delete by primary key: affected rows: %s" % rows)

    @classmethod
    async def find_all(cls, where=None, args=None, order_by=None, limit=None):
        sql = [cls.__select__]
        if where and isinstance(where, str):
            sql.append("WHERE")
            sql.append(where)
        if args is None:
            args = []
        assert isinstance(args, list)
        if order_by and isinstance(order_by, str):
            sql.append("ORDER BY")
            sql.append(order_by)
        if limit:
            sql.append("LIMIT")
            if isinstance(limit, int):
                sql.append("?")
                args.append(limit)
            elif isinstance(limit, (tuple, list)) and len(limit) == 2:
                sql.append("?, ?")
                args.extend(limit)
            else:
                error_msg = "Invalid limit arguments: %s" % limit
                logging.warning(error_msg)
                raise ValueError(error_msg)
        rs = await select(" ".join(sql), args)
        return [cls(**r) for r in rs]

    @classmethod
    async def get_count(cls, where=None, args=None):
        sql = ["SELECT COUNT(1) _num_ FROM `%s`" % cls.__table__]
        if where and isinstance(where, str):
            sql.append("WHERE")
            sql.append(where)
        rs = await select(" ".join(sql), args)
        if len(rs) == 0:
            return None
        return rs[0]["_num_"]
