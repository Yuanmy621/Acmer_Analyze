from __future__ import annotations

import json
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[1]


class BridgeHooksTest(unittest.TestCase):
    def test_bridge_emits_audit_hooks(self) -> None:
        bridge_log = ROOT_DIR / '.claude' / 'hooks' / 'outputs' / 'bridge' / 'bridge_events.jsonl'
        if bridge_log.exists():
            bridge_log.unlink()

        server = subprocess.Popen(
            [sys.executable, str(ROOT_DIR / 'scripts' / 'run_bridge.py')],
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            time.sleep(0.8)
            payload = json.loads((ROOT_DIR / 'examples' / 'bridge_payload.json').read_text(encoding='utf-8'))
            request = Request(
                'http://127.0.0.1:8765/api/bridge/import-and-run',
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            with urlopen(request, timeout=20) as response:
                body = json.loads(response.read().decode('utf-8'))

            self.assertTrue(body['ok'])
            self.assertTrue(bridge_log.exists())
            lines = [json.loads(line) for line in bridge_log.read_text(encoding='utf-8').splitlines() if line.strip()]
            self.assertTrue(any(item['event_name'] == 'bridge.after_import' for item in lines))
            self.assertTrue(any(item['event_name'] == 'bridge.after_run' for item in lines))
        finally:
            server.terminate()
            server.wait(timeout=5)
            if server.stdout:
                server.stdout.close()
            if server.stderr:
                server.stderr.close()


if __name__ == '__main__':
    unittest.main()
