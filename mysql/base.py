import random
from django.core.exceptions import ImproperlyConfigured

try:
    import MySQLdb as Database
except ImportError as err:
    raise ImproperlyConfigured(
        "Error loading MySQLdb module.\n" "Did you install mysqlclient?"
    ) from err

from django.db.backends.mysql.base import DatabaseWrapper as _DatabaseWrapper


class DatabaseWrapper(_DatabaseWrapper):
    def get_new_connection(self, conn_params):
        pool_size = self.settings_dict.get("POOL_SIZE")
        return ConnectPool(conn_params, pool_size).get_connection()

    def _close(self):
        pass  # 覆盖掉原来的close方法，查询结束后连接不会自动关闭


class ConnectPool(object):
    _instance = None
    _conn_params = None
    _pool_size = None
    _connects = None
    
    def __new__(cls, conn_params, pool_size, *args, **kwargs):
        if cls._instance is None:
            cls._conn_params = conn_params
            cls._pool_size = pool_size
            cls._connects = []
            cls._instance = super(ConnectPool, cls).__new__(cls)
        return cls._instance

    def __init__(self, conn_params, pool_size):
        if self._instance is not None:
            return

    def get_connection(self):
        if len(self._connects) < self._pool_size:
            new_connect = Database.connect(**self._conn_params)
            self._connects.append(new_connect)
            return new_connect
        index = random.randint(0, len(self._connects) - 1)
        try:
            self._connects[index].ping()
        except Database.Error:
            self._connects[index] = Database.connect(**self._conn_params)
        return self._connects[index] 

