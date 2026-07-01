import unittest
from types import SimpleNamespace

from mas004_vj6530_zbc_bridge.client import ZbcBridgeClient


class FakeZbcClient:
    def __init__(self, *, fail_once: bool = False):
        self.profile = SimpleNamespace(name="fake-zbc")
        self.connect_calls = 0
        self.close_calls = 0
        self.negotiate_calls = 0
        self.call_count = 0
        self.fail_once = fail_once

    def connect(self):
        self.connect_calls += 1

    def close(self):
        self.close_calls += 1

    def negotiate_host_version(self):
        self.negotiate_calls += 1

    def do_work(self):
        self.call_count += 1
        if self.fail_once:
            self.fail_once = False
            raise TimeoutError("stale socket")
        return f"ok-{self.call_count}"


class PersistentZbcBridgeClientTests(unittest.TestCase):
    def test_with_client_reuses_connected_client(self):
        bridge = ZbcBridgeClient("127.0.0.1", 3002, retry_count=1)
        opened = []

        def open_client():
            client = FakeZbcClient()
            opened.append(client)
            return client

        bridge._open_client = open_client

        self.assertEqual("ok-1", bridge._with_client(lambda client: client.do_work()))
        self.assertEqual("ok-2", bridge._with_client(lambda client: client.do_work()))

        self.assertEqual(1, len(opened))
        self.assertEqual(1, opened[0].connect_calls)
        self.assertEqual(1, opened[0].negotiate_calls)
        self.assertEqual(0, opened[0].close_calls)
        self.assertTrue(bridge.diagnostics()["connected"])

        bridge.close()
        self.assertEqual(1, opened[0].close_calls)

    def test_with_client_reconnects_after_failure(self):
        bridge = ZbcBridgeClient("127.0.0.1", 3002, retry_count=2, retry_delay_s=0.0)
        opened = []

        def open_client():
            client = FakeZbcClient(fail_once=(not opened))
            opened.append(client)
            return client

        bridge._open_client = open_client

        self.assertEqual("ok-1", bridge._with_client(lambda client: client.do_work()))

        self.assertEqual(2, len(opened))
        self.assertEqual(1, opened[0].close_calls)
        self.assertEqual(1, opened[1].connect_calls)
        self.assertTrue(bridge.diagnostics()["connected"])

        bridge.close()


if __name__ == "__main__":
    unittest.main()
