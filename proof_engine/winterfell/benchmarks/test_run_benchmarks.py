import unittest

from proof_engine.winterfell.benchmarks.run_benchmarks import (
    Measurement,
    parse_key_value_output,
    summarize_case,
)


class BenchmarkSummaryTests(unittest.TestCase):
    def test_summarizes_required_metrics(self):
        summary = summarize_case(
            "Yes",
            [
                Measurement(1.0, 0.5, 4500),
                Measurement(3.0, 1.5, 4520),
            ],
        )

        self.assertEqual(summary["synthetic_ballot_case"], "Yes")
        self.assertEqual(summary["run_count"], 2)
        self.assertEqual(
            summary["generation_time_ms"],
            {"average": 2.0, "minimum": 1.0, "maximum": 3.0},
        )
        self.assertEqual(
            summary["verification_time_ms"],
            {"average": 1.0, "minimum": 0.5, "maximum": 1.5},
        )
        self.assertEqual(
            summary["proof_size_bytes"],
            {"average": 4510, "minimum": 4500, "maximum": 4520},
        )

    def test_summary_does_not_contain_sensitive_fields_or_paths(self):
        summary = summarize_case("No", [Measurement(1.0, 0.5, 4500)])
        serialized = repr(summary).lower()

        for forbidden in (
            "nin",
            "voter",
            "proof_path",
            "input_path",
            "decrypted_vote",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_parses_engine_metrics(self):
        output = parse_key_value_output(
            "proof_size_bytes=4523\nproof_generation_ms=1.234567\n"
        )

        self.assertEqual(output["proof_size_bytes"], "4523")
        self.assertEqual(output["proof_generation_ms"], "1.234567")


if __name__ == "__main__":
    unittest.main()
