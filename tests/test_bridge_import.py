from __future__ import annotations

import json
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[1]


class BridgeImportTest(unittest.TestCase):
    def test_bridge_import_and_pipeline(self) -> None:
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
                'http://127.0.0.1:8765/api/bridge/import',
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            with urlopen(request, timeout=10) as response:
                body = json.loads(response.read().decode('utf-8'))

            self.assertTrue(body['ok'])
            import_id = body['import_id']

            command = [
                sys.executable,
                str(ROOT_DIR / 'scripts' / 'run_pipeline.py'),
                '--source',
                'browser_bridge',
                '--target-team',
                'tourist',
                '--aliases',
                'tourist',
                '--bridge-import-id',
                import_id,
                '--start-stage',
                'normalize',
                '--skip-analyze',
            ]
            completed = subprocess.run(command, cwd=ROOT_DIR, capture_output=True, text=True, check=True)
            result = json.loads(completed.stdout)

            self.assertEqual(result['canonical_id'], 'team_tourist')
            self.assertIn('normalize', result['executed_stages'])
            self.assertIn('validate_final', result['executed_stages'])
            self.assertNotIn('analyze', result['executed_stages'])
        finally:
            server.terminate()
            server.wait(timeout=5)
            if server.stdout:
                server.stdout.close()
            if server.stderr:
                server.stderr.close()

    def test_bridge_import_and_run(self) -> None:
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
            payload.setdefault('metadata', {})['skip_analyze'] = True
            request = Request(
                'http://127.0.0.1:8765/api/bridge/import-and-run',
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            with urlopen(request, timeout=20) as response:
                body = json.loads(response.read().decode('utf-8'))

            self.assertTrue(body['ok'])
            self.assertEqual(body['status'], 'completed')
            self.assertTrue(body['run_id'].startswith('run_'))
            self.assertTrue(body['report_path'].endswith('.html'))
            self.assertTrue(body['visualization_path'].endswith('.html'))

            status_request = Request(f"http://127.0.0.1:8765/api/bridge/runs/{body['run_id']}")
            with urlopen(status_request, timeout=10) as response:
                status_body = json.loads(response.read().decode('utf-8'))

            self.assertTrue(status_body['ok'])
            self.assertEqual(status_body['status'], 'completed')
            self.assertIn('validate_final', status_body['executed_stages'])
        finally:
            server.terminate()
            server.wait(timeout=5)
            if server.stdout:
                server.stdout.close()
            if server.stderr:
                server.stderr.close()


if __name__ == '__main__':
    unittest.main()
