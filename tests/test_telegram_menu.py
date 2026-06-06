import re
import unittest

from integrations.telegram.commands import (
    botfather_commands_text,
    telegram_command_menu,
)

_NAME = re.compile(r"^[a-z0-9_]{1,32}$")


class TestTelegramMenu(unittest.TestCase):
    def test_menu_shape_and_validity(self):
        menu = telegram_command_menu()
        self.assertTrue(menu)
        names = [c["command"] for c in menu]
        # Telegram exige des noms minuscules [a-z0-9_], 1-32 car.
        for c in menu:
            self.assertRegex(c["command"], _NAME, c["command"])
            self.assertTrue(1 <= len(c["description"]) <= 256)
        # Les commandes métier clés sont présentes.
        for expected in ("help", "status", "scan", "proposals", "approve",
                         "reject", "listings", "pause", "resume", "config",
                         "logs", "tops", "health"):
            self.assertIn(expected, names)

    def test_no_duplicate_commands(self):
        names = [c["command"] for c in telegram_command_menu()]
        self.assertEqual(len(names), len(set(names)))

    def test_botfather_text_format(self):
        text = botfather_commands_text()
        # Chaque ligne au format 'command - description'.
        for line in text.splitlines():
            self.assertIn(" - ", line)
            cmd = line.split(" - ", 1)[0]
            self.assertRegex(cmd, _NAME, cmd)
        self.assertIn("status - ", text)
        self.assertIn("scan - ", text)


if __name__ == "__main__":
    unittest.main()
