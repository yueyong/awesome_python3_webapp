import www.orm as orm
from www.models import User


def test():
    yield orm.create_connection_pool(None, user="root", password="usbw", db="qjcg")
    u = User(name="vic", email="test@126.com", passwd="123456", image="about:blank")
    print(u.__ddl_sql__())


# loop = asyncio.get_event_loop()
# loop.run_until_complete(test(loop))
# loop.run_forever()
for _ in test():
    pass
