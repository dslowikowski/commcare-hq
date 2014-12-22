from django.core.cache.backends.locmem import LocMemCache
from django.test import SimpleTestCase
import time
from corehq.util.quickcache import quickcache, TieredCache

BUFFER = []


class CacheMock(LocMemCache):
    def __init__(self, name, params):
        self.name = name
        super(CacheMock, self).__init__(name, params)

    def get(self, key, default=None, version=None):
        result = super(CacheMock, self).get(key, default, version)
        if result is default:
            BUFFER.append('{} miss'.format(self.name))
        else:
            BUFFER.append('{} hit'.format(self.name))
        return result

SHORT_TIME_UNIT = 1

_local_cache = CacheMock('local', {'timeout': SHORT_TIME_UNIT})
_shared_cache = CacheMock('shared', {'timeout': 2 * SHORT_TIME_UNIT})
_cache = TieredCache([_local_cache, _shared_cache])


class QuickcacheTest(SimpleTestCase):

    def tearDown(self):
        self.consume_buffer()

    def consume_buffer(self):
        result = list(BUFFER)
        while True:
            try:
                BUFFER.pop()
            except IndexError:
                break
        return result

    def test_tiered_cache(self):
        @quickcache(cache=_cache)
        def simple():
            BUFFER.append('called')
            return 'VALUE'

        self.assertEqual(simple(), 'VALUE')
        self.assertEqual(self.consume_buffer(), ['local miss', 'shared miss', 'called'])
        self.assertEqual(simple(), 'VALUE')
        self.assertEqual(self.consume_buffer(), ['local hit'])
        # let the local cache expire
        time.sleep(SHORT_TIME_UNIT)
        self.assertEqual(simple(), 'VALUE')
        self.assertEqual(self.consume_buffer(), ['local miss', 'shared hit'])
        # let the shared cache expire
        time.sleep(SHORT_TIME_UNIT)
        self.assertEqual(simple(), 'VALUE')
        self.assertEqual(self.consume_buffer(), ['local miss', 'shared miss', 'called'])
        # and that this is again cached locally
        self.assertEqual(simple(), 'VALUE')
        self.assertEqual(self.consume_buffer(), ['local hit'])

    def test_vary_on(self):
        @quickcache(['n'], cache=_cache)
        def fib(n):
            BUFFER.append(n)
            if n < 2:
                return 1
            else:
                return fib_r(n - 1) + fib_r(n - 2)

        fib_r = fib

        # [1, 1, 2, 3, 5, 8]
        self.assertEqual(fib(5), 8)
        self.assertEqual(self.consume_buffer(),
                         ['local miss', 'shared miss', 5,
                          'local miss', 'shared miss', 4,
                          'local miss', 'shared miss', 3,
                          'local miss', 'shared miss', 2,
                          'local miss', 'shared miss', 1,
                          'local miss', 'shared miss', 0,
                          # fib(3/4/5) also ask for fib(1/2/3)
                          # so three cache hits
                          'local hit', 'local hit', 'local hit'])

    def test_vary_on_attr(self):
        class Item(object):
            def __init__(self, id, name):
                self.id = id
                self.name = name

            @quickcache(['self.id'], cache=_cache)
            def get_name(self):
                BUFFER.append('called method')
                return self.name

        @quickcache(['item.id'], cache=_cache)
        def get_name(item):
            BUFFER.append('called function')
            return item.name

        james = Item(1, 'james')
        fred = Item(2, 'fred')
        self.assertEqual(get_name(james), 'james')
        self.assertEqual(self.consume_buffer(),
                         ['local miss', 'shared miss', 'called function'])
        self.assertEqual(get_name(fred), 'fred')
        self.assertEqual(self.consume_buffer(),
                         ['local miss', 'shared miss', 'called function'])
        self.assertEqual(get_name(james), 'james')
        self.assertEqual(self.consume_buffer(), ['local hit'])
        self.assertEqual(get_name(fred), 'fred')
        self.assertEqual(self.consume_buffer(), ['local hit'])

        # this also works, and uses different keys
        self.assertEqual(james.get_name(), 'james')
        self.assertEqual(self.consume_buffer(),
                         ['local miss', 'shared miss', 'called method'])
        self.assertEqual(fred.get_name(), 'fred')
        self.assertEqual(self.consume_buffer(),
                         ['local miss', 'shared miss', 'called method'])
        self.assertEqual(james.get_name(), 'james')
        self.assertEqual(self.consume_buffer(), ['local hit'])
        self.assertEqual(fred.get_name(), 'fred')
        self.assertEqual(self.consume_buffer(), ['local hit'])

    def test_bad_vary_on(self):
        with self.assertRaisesRegexp(ValueError, 'cucumber'):
            @quickcache(['cucumber'], cache=_cache)
            def square(number):
                return number * number

    def test_weird_data(self):
        @quickcache(['bytes'])
        def encode(bytes):
            return hash(bytes)

        symbols = '!@#$%^&*():{}"?><.~`'
        bytes = '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09'
        self.assertEqual(encode(symbols), hash(symbols))
        self.assertEqual(encode(bytes), hash(bytes))

    def test_lots_of_args(self):
        @quickcache('abcdef')
        def lots_of_args(a, b, c, d, e, f):
            pass

        # doesn't fail
        lots_of_args('\xff', '\xff', '\xff', '\xff', '\xff', '\xff')
        key = lots_of_args.get_cache_key(
            '\xff', '\xff', '\xff', '\xff', '\xff', '\xff')
        self.assertLess(len(key), 250)
        # assert it's actually been hashed
        self.assertEqual(
            len(key), len('quickcache.lots_of_args.xxxxxxxx/H') + 32, key)

    def test_really_long_function_name(self):
        @quickcache()
        def aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa():
            """60 a's in a row"""
            pass

        # doesn't fail
        aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa()
        key = (aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
               .get_cache_key())
        self.assertEqual(
            len(key), len('quickcache.' + 'a' * 40 + '...xxxxxxxx/'), key)
