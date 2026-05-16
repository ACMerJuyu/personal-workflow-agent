import unittest

from scripts.run_evals import run_evals


class EvalRunnerTest(unittest.TestCase):
    def test_eval_suite_passes(self):
        report = run_evals()

        self.assertGreaterEqual(report["total"], 5)
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["passed"], report["total"])


if __name__ == "__main__":
    unittest.main()
