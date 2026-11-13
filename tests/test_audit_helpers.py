import unittest

import discord

from audit import permission_changes


class AuditHelperTests(unittest.TestCase):
    def test_permission_changes_only_returns_differences(self):
        before = discord.Permissions.none()
        after = discord.Permissions.none()
        after.send_messages = True
        after.view_channel = True

        changes = permission_changes(before, after)

        self.assertIn("send_messages", "\n".join(changes))
        self.assertIn("view_channel", "\n".join(changes))
        self.assertTrue(
            all("Não permitida → Permitida" in item for item in changes)
        )

    def test_no_permission_changes(self):
        before = discord.Permissions.none()
        after = discord.Permissions.none()

        self.assertEqual(permission_changes(before, after), [])


if __name__ == "__main__":
    unittest.main()
