import unittest

from mas004_vj6530_zbc_bridge._zbc_library import MessageId
from mas004_vj6530_zbc_bridge.client import ZbcBridgeClient


class FakeLibraryClient:
    def __init__(self):
        self.calls = []

    def write_mapped_value(self, mapping: str, value):
        self.calls.append((mapping, str(value)))
        return MessageId.NUL, None


class ClientStatusMappingTests(unittest.TestCase):
    def test_read_mapped_value_returns_numeric_state_code(self):
        client = ZbcBridgeClient("192.168.2.103", 3002)
        client.summary_dict = lambda force_refresh=False: {
            "summary": {},
            "status_values": {"printer_state_code": "5"},
        }

        self.assertEqual("5", client.read_mapped_value("STATUS[PRINTER_STATE_CODE]"))

    def test_write_mapped_value_delegates_numeric_state_code(self):
        client = ZbcBridgeClient("192.168.2.103", 3002)
        fake = FakeLibraryClient()
        client._with_client = lambda fn, retries=None: fn(fake)

        message_id, verified = client.write_mapped_value("STATUS[PRINTER_STATE_CODE]", "3")

        self.assertEqual(MessageId.NUL, message_id)
        self.assertEqual("3", verified)
        self.assertEqual([("STATUS[PRINTER_STATE_CODE]", "3")], fake.calls)
        self.assertEqual("3", client.status_snapshot()["printer_state_code"])
        self.assertEqual("ONLINE", client.status_snapshot()["last_command"])


if __name__ == "__main__":
    unittest.main()
