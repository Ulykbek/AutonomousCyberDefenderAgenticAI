from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from experiments.evidence_variants import apply_evidence_variant, load_evidence_variant
from experiments.lifecycle import PROJECT_ROOT, file_hashes


class EvidenceVariantTests(unittest.TestCase):
    def test_each_variant_is_deterministic_and_does_not_modify_base_corpus(self):
        source = PROJECT_ROOT / "cases" / "incident02" / "evidence"
        before = file_hashes(source)
        results = {}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for variant_id in ("c91f7a2e", "4d8b2c61", "a73e5f90"):
                evidence = root / variant_id
                shutil.copytree(source, evidence)
                variant = load_evidence_variant(variant_id)
                self.assertIsNotNone(variant)
                apply_evidence_variant(evidence, variant)
                results[variant_id] = file_hashes(evidence)
                self.assertNotEqual(before, results[variant_id])
                self.assertEqual(before["auth.log"], results[variant_id]["auth.log"])
        self.assertEqual(before, file_hashes(source))
        self.assertEqual(3, len({value["web.log"] for value in results.values()}))

    def test_base_variant_is_a_noop(self):
        self.assertIsNone(load_evidence_variant("BASE"))

    def test_unknown_variant_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown evidence variant"):
            load_evidence_variant("not-registered")


if __name__ == "__main__":
    unittest.main()
