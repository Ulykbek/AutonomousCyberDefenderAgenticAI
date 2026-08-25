from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from policy.policy_engine import PROJECT_ROOT, authorize


class QuarantinePathPolicyTests(unittest.TestCase):
    def decision(self, target: str):
        return authorize("quarantine_file", {"target": target})

    def test_valid_file_below_allowed_directory_is_allowed(self) -> None:
        result = self.decision("cases/incident02/evidence/auth.log")
        self.assertTrue(result.allowed)
        self.assertEqual("ALLOW", result.reason)

    def test_denied_directory_is_component_aware(self) -> None:
        result = self.decision("cases/incident01/evidence/auth.log")
        self.assertFalse(result.allowed)
        self.assertEqual("PATH_EXPLICITLY_DENIED", result.reason)

    def test_dot_component_cannot_bypass_denied_directory(self) -> None:
        result = self.decision("cases/incident01/./evidence/auth.log")
        self.assertFalse(result.allowed)
        self.assertEqual("PATH_EXPLICITLY_DENIED", result.reason)

    def test_parent_traversal_cannot_escape_allowed_directory(self) -> None:
        result = self.decision("cases/../policies/cyberdefender_policy.json")
        self.assertFalse(result.allowed)
        self.assertEqual("PATH_OUTSIDE_ALLOWED_SCOPE", result.reason)

    def test_absolute_posix_path_is_denied(self) -> None:
        result = self.decision(str(PROJECT_ROOT / "cases" / "incident02"))
        self.assertFalse(result.allowed)
        self.assertEqual("PATH_OUTSIDE_ALLOWED_SCOPE", result.reason)

    def test_absolute_windows_path_is_denied(self) -> None:
        result = self.decision(r"C:\cases\incident02\evidence\auth.log")
        self.assertFalse(result.allowed)
        self.assertEqual("PATH_OUTSIDE_ALLOWED_SCOPE", result.reason)

    def test_sibling_prefix_is_not_treated_as_allowed_directory(self) -> None:
        result = self.decision("cases-escape/file.txt")
        self.assertFalse(result.allowed)
        self.assertEqual("PATH_OUTSIDE_ALLOWED_SCOPE", result.reason)

    def test_symlink_escape_is_denied(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "cases") as directory:
            link = Path(directory) / "escape"
            try:
                link.symlink_to(PROJECT_ROOT / "policies", target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlink unavailable: {error}")
            target = str((link / "cyberdefender_policy.json").relative_to(PROJECT_ROOT))
            result = self.decision(target)
        self.assertFalse(result.allowed)
        self.assertEqual("PATH_OUTSIDE_ALLOWED_SCOPE", result.reason)


if __name__ == "__main__":
    unittest.main()
