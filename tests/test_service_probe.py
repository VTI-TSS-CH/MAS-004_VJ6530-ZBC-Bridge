import unittest
from types import SimpleNamespace

from mas004_vj6530_zbc_bridge.service import probe


class FakeClient:
    def __init__(self, snapshot=None, error: Exception | None = None):
        self.snapshot = snapshot or SimpleNamespace(
            profile_name="vj6530-tcp-no-crc",
            machine_name="Nimitz",
            job_name="EMMI",
            active_faults=(),
            active_warnings=(),
            ribbon_level="8",
        )
        self.error = error
        self.probe_calls = 0

    def probe(self):
        self.probe_calls += 1
        if self.error is not None:
            raise self.error
        return self.snapshot


def _cfg(host: str = "192.168.2.103", port: int = 3002, timeout_s: float = 8.0):
    return SimpleNamespace(host=host, port=port, timeout_s=timeout_s)


class ServiceProbeTests(unittest.TestCase):
    def test_probe_reuses_supplied_client(self):
        client = FakeClient()

        ok, msg, reused = probe(_cfg(), client=client)

        self.assertTrue(ok)
        self.assertIn("profile=vj6530-tcp-no-crc", msg)
        self.assertIs(reused, client)
        self.assertEqual(1, client.probe_calls)

    def test_probe_creates_client_when_missing(self):
        created = []

        def factory(host, port, timeout_s):
            client = FakeClient()
            created.append((host, port, timeout_s, client))
            return client

        ok, msg, client = probe(_cfg(), client=None, client_factory=factory)

        self.assertTrue(ok)
        self.assertIn("machine=Nimitz", msg)
        self.assertEqual(1, len(created))
        self.assertEqual("192.168.2.103", created[0][0])
        self.assertEqual(3002, created[0][1])
        self.assertEqual(8.0, created[0][2])
        self.assertIs(client, created[0][3])

    def test_probe_keeps_client_on_failure(self):
        client = FakeClient(error=TimeoutError("timed out"))

        ok, msg, reused = probe(_cfg(), client=client)

        self.assertFalse(ok)
        self.assertIn("timed out", msg)
        self.assertIs(reused, client)
        self.assertEqual(1, client.probe_calls)

    def test_probe_returns_none_when_host_missing(self):
        client = FakeClient()

        ok, msg, reused = probe(_cfg(host="", port=0), client=client)

        self.assertFalse(ok)
        self.assertEqual("host/port not configured", msg)
        self.assertIsNone(reused)


if __name__ == "__main__":
    unittest.main()
