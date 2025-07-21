# test_order_parser.py
import unittest
from unittest.mock import patch, MagicMock
from app import extract_order

class TestOrderParser(unittest.TestCase):

    @patch('vibe.model.generate_content')
    def test_valid_order(self, mock_generate):
        mock_response = MagicMock()
        mock_response.text = """
        {
            "items": [
                {"name": "pizza", "qty": 2, "modifiers": ["extra cheese"]},
                {"name": "coke", "qty": 1, "modifiers": []}
            ]
        }
        """
        mock_generate.return_value = mock_response

        result = extract_order("I want 2 pizzas with extra cheese and a coke")
        self.assertEqual(len(result['items']), 2)
        self.assertEqual(result['items'][0]['name'], 'pizza')
        self.assertIn('extra cheese', result['items'][0]['modifiers'])

    @patch('vibe.model.generate_content')
    def test_malformed_response(self, mock_generate):
        mock_response = MagicMock()
        mock_response.text = "Here's your order: pizza and coke"
        mock_generate.return_value = mock_response

        result = extract_order("pizza and coke")
        self.assertEqual(result['items'], [])

    @patch('vibe.model.generate_content')
    def test_partial_json(self, mock_generate):
        mock_response = MagicMock()
        mock_response.text = """
        ```json
        {
            "items": [
                {"name": "burger", "qty": 1, "modifiers": []}
            ]
        }
        ```
        """
        mock_generate.return_value = mock_response

        result = extract_order("Just one burger")
        self.assertEqual(result['items'][0]['name'], "burger")

if __name__ == '__main__':
    unittest.main()
