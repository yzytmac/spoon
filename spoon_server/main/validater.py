import time
import concurrent.futures

from spoon_server.util.validate import validate
from spoon_server.main.manager import Manager

from spoon_server.database.redis_config import RedisConfig


class Validater(Manager):
    def __init__(self, url_prefix=None, database=None, checker=None, validater_thread_num=30):
        super(Validater, self).__init__(database=database, url_prefix=url_prefix, checker=checker)
        self.validater_thread_num = validater_thread_num

    def _validate_proxy(self, each_proxy):
        if isinstance(each_proxy, bytes):
            each_proxy = each_proxy.decode('utf-8')
        value = int(self.database.getvalue(self.generate_name(self._useful_prefix), each_proxy))
        if value < 0:
            self.database.delete(self.generate_name(self._useful_prefix), each_proxy)
        else:
            if validate(self._url_prefix, each_proxy, self._checker):
                self.database.zadd(self.generate_name(self._current_prefix), each_proxy, int(-1 * time.time()))
                self.database.zremrangebyrank(self.generate_name(self._current_prefix), 100, 10000)
                if not value >= 100:
                    if value == 99:
                        self.database.set_value(self.generate_name(self._hundred_prefix), each_proxy, time.time())
                    self.database.inckey(self.generate_name(self._useful_prefix), each_proxy, 1)
                else:
                    self.database.set_value(self.generate_name(self._hundred_prefix), each_proxy, time.time())
                    self.database.set_value(self.generate_name(self._useful_prefix), each_proxy, 100)
            else:
                self.database.zrem(self.generate_name(self._current_prefix), each_proxy)
                if value > 0:
                    self.database.set_value(self.generate_name(self._useful_prefix), each_proxy, value // 2)
                self.database.inckey(self.generate_name(self._useful_prefix), each_proxy, -1)

    def main(self):
        while True:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.validater_thread_num) as executor:
                proxy_list = [each_proxy for each_proxy in
                              self.database.get_all(self.generate_name(self._useful_prefix))]
                for proxy in proxy_list:
                    executor.submit(self._validate_proxy, proxy)


def validater_run(url=None, database=None, checker=None, validater_thread_num=30):
    validater = Validater(url_prefix=url,
                          database=database,
                          checker=checker,
                          validater_thread_num=validater_thread_num)
    validater.main()


if __name__ == '__main__':
    redis = RedisConfig("127.0.0.1", 21009)
    p = Validater(url_prefix="https://www.google.com", database=redis)
    p.main()
