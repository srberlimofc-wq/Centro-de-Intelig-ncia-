import tempfile
import unittest
from pathlib import Path

from config_store import ConfigStore


class ConfigStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_defaults_and_persistence(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            store = ConfigStore(path)
            await store.load()

            initial = await store.get(123)
            self.assertIsNone(initial["log_channel_id"])
            self.assertTrue(initial["categories"]["canais"])

            await store.update(
                123,
                log_channel_id=456,
                admin_role_id=789,
                categories={"canais": False},
            )

            reloaded = ConfigStore(path)
            await reloaded.load()
            result = await reloaded.get(123)

            self.assertEqual(result["log_channel_id"], 456)
            self.assertEqual(result["admin_role_id"], 789)
            self.assertFalse(result["categories"]["canais"])
            self.assertTrue(result["categories"]["membros"])


if __name__ == "__main__":
    unittest.main()
