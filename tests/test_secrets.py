import unittest

from agent_checkpoint.secrets import find_secret_kind


class SecretTests(unittest.TestCase):
    def test_detects_each_supported_structured_secret_class(self):
        """Catches removal of any required structured credential signature."""
        candidates = (
            ("-----BEGIN " + "PRIVATE KEY-----", "private key"),
            ("gh" + "p_" + ("a" * 24), "access token"),
            ("s" + "k-" + ("a" * 21), "access token"),
            ("AK" + "IA" + ("A" * 16), "AWS access key"),
        )

        for candidate, expected_kind in candidates:
            self.assertEqual(find_secret_kind(candidate), expected_kind)

    def test_detects_non_placeholder_sensitive_assignment(self):
        """Catches accepting an assigned credential merely because it is unstructured."""
        text = "api_" + "key = " + ("live" + "-credential")

        self.assertEqual(find_secret_kind(text), "API key")

    def test_detects_pem_private_key_closing_delimiter(self):
        """Catches scanning only the opening half of a private-key PEM block."""
        delimiter = "-----END " + "PRIVATE KEY-----"

        self.assertEqual(find_secret_kind(delimiter), "private key")

    def test_detects_openai_style_value_ending_in_hyphen(self):
        """Catches a word boundary that excludes a valid terminal suffix character."""
        candidate = "s" + "k-" + ("a" * 20) + "-"

        self.assertEqual(find_secret_kind(candidate), "access token")

    def test_allows_documented_placeholder_assignments(self):
        """Catches rejecting safe templates that contain no candidate credential."""
        placeholders = (
            "api_key = <your-api-key>",
            "token: ${TOKEN}",
            'secret = "REDACTED"',
            "password = changeme",
        )

        for text in placeholders:
            self.assertIsNone(find_secret_kind(text))

    def test_placeholder_boundary_does_not_exempt_prefixed_candidate(self):
        """Catches broad prefix exemptions that can hide assigned credentials."""
        candidate = "api_" + "key = " + ("test" + "-credential")

        self.assertEqual(find_secret_kind(candidate), "API key")

    def test_allows_shell_variable_placeholder(self):
        """Catches rejecting an unmistakable unbraced shell-variable template."""
        placeholder = "token = " + "$" + "TOKEN"

        self.assertIsNone(find_secret_kind(placeholder))

    def test_rejects_shell_expansion_with_literal_default(self):
        """Catches exempting arbitrary shell expansions with embedded values."""
        expansion = "token = " + "${" + "TOKEN:-fallback}"

        self.assertEqual(find_secret_kind(expansion), "access token")

    def test_allows_whitespace_separated_assignment_comment(self):
        """Catches treating a configuration comment as an assigned credential."""
        text = "password: # configure during deployment"

        self.assertIsNone(find_secret_kind(text))

    def test_detects_sensitive_command_line_option_assignment(self):
        """Catches option syntax bypassing parser-error credential redaction."""
        option = "--password=" + "production-value"

        self.assertEqual(find_secret_kind(option), "password")


if __name__ == "__main__":
    unittest.main()
