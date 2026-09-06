import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os

import message


class TestMessage(unittest.TestCase):

    def test_normalize_phone(self):
        # Standard French phone number starting with 0
        vars1 = message.normalize_phone("06 12 34 56 78")
        self.assertIn("0612345678", vars1)
        self.assertIn("33612345678", vars1)
        self.assertIn("612345678", vars1)

        # International format starting with +33
        vars2 = message.normalize_phone("+33 6 12 34 56 78")
        self.assertIn("33612345678", vars2)
        self.assertIn("0612345678", vars2)

        # Invalid / Empty input
        self.assertEqual(message.normalize_phone("abc"), set())

    def test_load_group_members(self):
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as f:
            f.write("# Comment line\n")
            f.write("0612345678\n")
            f.write("Jean Dupont\n")
            f.write(" Alice Smith \n")
            file_path = f.name

        try:
            members = message.load_group_members(file_path)
            self.assertIn("0612345678", members)
            self.assertIn("33612345678", members)
            self.assertIn("jean dupont", members)
            self.assertIn("alice smith", members)
        finally:
            os.remove(file_path)

    def test_is_person_in_group(self):
        group_members = {"0612345678", "33612345678", "jean dupont"}

        # Person matching by phone
        p1 = {"nom": "Martin", "prenom": "Paul", "tel": "0612345678", "tel_display": "+33612345678"}
        self.assertTrue(message.is_person_in_group(p1, group_members))

        # Person matching by name
        p2 = {"nom": "Dupont", "prenom": "Jean", "tel": "0700000000", "tel_display": "+33700000000"}
        self.assertTrue(message.is_person_in_group(p2, group_members))

        # Person not in group
        p3 = {"nom": "Durand", "prenom": "Jacques", "tel": "0699999999", "tel_display": "+33699999999"}
        self.assertFalse(message.is_person_in_group(p3, group_members))

    @patch("subprocess.run")
    def test_send_imessage(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        success, detail = message.send_imessage("0612345678", "Hello")
        self.assertTrue(success)
        self.assertEqual(detail, "ok")


if __name__ == "__main__":
    unittest.main()
