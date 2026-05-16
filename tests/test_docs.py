import unittest
from pathlib import Path


class DocsTest(unittest.TestCase):
    def test_readme_includes_demo_flow(self):
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("Demo Flow", readme)
        self.assertIn("Open the dashboard", readme)
        self.assertIn("Run evals", readme)

    def test_maintenance_files_exist(self):
        expected_paths = [
            ".env.example",
            "scripts/dev.ps1",
            "scripts/check.ps1",
            ".github/workflows/ci.yml",
        ]

        for path in expected_paths:
            self.assertTrue(Path(path).exists(), f"Missing {path}")

    def test_check_script_runs_tests_and_evals(self):
        check_script = Path("scripts/check.ps1").read_text(encoding="utf-8")

        self.assertIn("unittest discover -s tests", check_script)
        self.assertIn("scripts/run_evals.py", check_script)

    def test_ci_runs_tests_and_evals(self):
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

        self.assertIn("python -m unittest discover -s tests", workflow)
        self.assertIn("python scripts/run_evals.py", workflow)

    def test_readme_documents_maintenance_scripts(self):
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("scripts/dev.ps1", readme)
        self.assertIn("scripts/check.ps1", readme)
        self.assertIn(".env.example", readme)


if __name__ == "__main__":
    unittest.main()
