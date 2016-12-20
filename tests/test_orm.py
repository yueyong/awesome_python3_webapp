import logging
import asyncio
from www import orm
from www.models import User


async def test(lp):
    await orm.create_connection_pool(lp, user="pabb", password="pabb", db="awesome", host="192.168.3.250")
    # u = User(name="vic", email="test@126.com", passwd="123456", image="about:blank")
    # print(User.__select__)
    sql = User.__select__
    print(sql)
    # sql = User.__ddl_sql__()
    # print(sql)
    # await u.save()
    # ret = await User.find_all()
    # print(len(ret), ret)
    rets = await orm.select(sql, [])
    print(rets)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test(loop))
