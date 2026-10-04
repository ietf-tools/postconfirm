from src.db import close_db_pools
from src.db import db as db_module


class FakePool:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class TestCloseDbPools:
    def test_closes_and_forgets_every_pool(self):
        pools = {"db": FakePool(), "lists": FakePool()}
        db_module.pool_cache.update(pools)

        close_db_pools()

        assert all(pool.closed for pool in pools.values())
        assert db_module.pool_cache == {}
