import logging
import asyncio
from www import orm
from www.models import User


async def test(lp):
    await orm.create_connection_pool(lp, user="root", password="usbw", db="qjcg")
    u = User(name="vic", email="test@126.com", passwd="123456", image="about:blank")
    print(u.__select__)
    # sql = User.__ddl_sql__()
    # print(sql)
    # await u.save()
    ret = await User.find_all()
    print(len(ret), ret)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test(loop))
