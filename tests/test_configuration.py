"""Fast checks for local application wiring."""

import unittest
from unittest.mock import patch

import calculator
import main
import web_search


class CalculatorTests(unittest.TestCase):
    def test_math_tools(self) -> None:
        self.assertEqual(calculator.add(3, 5), 8)
        self.assertEqual(calculator.multiply(3, 5), 15)


class MainConfigurationTests(unittest.TestCase):
    def test_default_model_is_jev(self) -> None:
        self.assertEqual(main.DEFAULT_MODEL, "typesafe/jev-1.13.0")

    def test_jev_response_format_contains_a_tool_choice(self) -> None:
        response_format = main.JEV_TOOL_RESPONSE_FORMAT
        self.assertEqual(response_format["type"], "questions")
        self.assertEqual(response_format["questions"]["tool"]["type"], "choice")

    def test_calculator_dispatch_supports_basic_arithmetic(self) -> None:
        expression = main.extract_math_expression("what is (3 + 5) * 12?")
        self.assertEqual(main.calculate(expression), 96)
        self.assertEqual(main.calculate(main.extract_math_expression("calculate 12 / 4 - 1")), 2)

    def test_tool_argument_extraction(self) -> None:
        self.assertEqual(main.extract_location("weather in Mumbai"), "Mumbai")
        self.assertEqual(main.extract_search_query("search Python release notes"), "Python release notes")

    def test_jev_tool_choice_is_read_from_structured_response(self) -> None:
        content = '{"answers": {"tool": {"choice": "weather"}}}'
        self.assertEqual(main.extract_tool_choice(content), "weather")

    def test_missing_api_key_has_clear_error(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "API_KEY is not set"):
                main.create_client()

    def test_kodekey_api_key_is_supported(self) -> None:
        with patch.dict("os.environ", {"KODEKEY_API_KEY": "test-key"}, clear=True):
            client = main.create_client()
            self.assertIsNotNone(client)


class GoogleSearchConfigurationTests(unittest.TestCase):
    def test_google_search_uses_google_endpoint(self) -> None:
        self.assertEqual(
            web_search.SEARCH_URL, "https://www.googleapis.com/customsearch/v1"
        )



if __name__ == "__main__":
    unittest.main()
