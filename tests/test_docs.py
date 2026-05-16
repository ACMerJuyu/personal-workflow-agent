import unittest
from pathlib import Path


class DocsTest(unittest.TestCase):
    def test_readme_includes_demo_flow(self):
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("Demo Flow", readme)
        self.assertIn("Open the dashboard", readme)
        self.assertIn("Run evals", readme)


if __name__ == "__main__":
    unittest.main()
