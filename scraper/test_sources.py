import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bundle
from sources import ethz


class Response:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


class Session:
    def __init__(self):
        self.urls = []

    def get(self, url, timeout):
        self.urls.append(url)
        if url == ethz.LIST_URL:
            return Response('<a href="/job/view/1">Doctoral Position, Zurich</a>'
                            '<a href="/job/view/2">PhD Researcher, Singapore</a>'
                            '<a href="/job/view/3">Postdoctoral Researcher, Zurich</a>')
        return Response('<h1>Doctoral Position in Simulation</h1><p>Apply online</p>')


class SourceTests(unittest.TestCase):
    def test_ethz_excludes_asia_and_postdocs(self):
        session = Session()
        with patch.object(ethz.time, "sleep"):
            jobs = ethz.fetch(session)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["country"], "CH")
        self.assertEqual(jobs[0]["source_url"], "https://www.jobs.ethz.ch/job/view/1")
        self.assertEqual(len(session.urls), 2)
        self.assertIsNone(jobs[0]["deadline"])

    def test_offline_bundle_contains_current_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "data").mkdir()
            payload = {"total": 1, "jobs": [{"title": "博士"}]}
            (root / "data/jobs.json").write_text(json.dumps(payload))
            with patch.object(bundle, "ROOT", root):
                bundle.bundle()
            script = (root / "data/offline-data.js").read_text()
            decoded = json.loads(script.removeprefix("window.PHD_OFFLINE_DATA = ").rstrip(";\n"))
            self.assertEqual(decoded["jobs"], payload)


if __name__ == "__main__":
    unittest.main()
