from __future__ import annotations

import json
import unittest

from src.bridge.payloads import validate_bridge_payload


class BridgePayloadTest(unittest.TestCase):
    def test_validate_bridge_payload(self) -> None:
        payload = {
            "source": "browser_bridge",
            "site": "codeforces",
            "target_team": "tourist",
            "aliases": ["tourist"],
            "raw_payload": {
                "contests": [],
                "problems": [],
                "standings": [],
            },
            "metadata": {"page_url": "https://example.com"},
        }

        validated = validate_bridge_payload(payload)

        self.assertEqual(validated.source, "browser_bridge")
        self.assertEqual(validated.site, "codeforces")
        self.assertEqual(validated.target_team, "tourist")

    def test_validate_bridge_payload_missing_groups(self) -> None:
        payload = {
            "source": "browser_bridge",
            "site": "codeforces",
            "target_team": "tourist",
            "raw_payload": {
                "contests": [],
                "problems": [],
            },
        }
        with self.assertRaises(ValueError):
            validate_bridge_payload(payload)


if __name__ == "__main__":
    unittest.main()
