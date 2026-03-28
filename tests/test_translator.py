import pytest
from unittest.mock import MagicMock, patch
from learn_korean.translator_llm import (
    translate_with_gemini,
    extract_phrases_with_gemini,
)


@pytest.fixture
def mock_env_and_client():
    with (
        patch("os.getenv", return_value="fake-key"),
        patch("learn_korean.translator_llm.genai.Client") as mock_client,
    ):
        yield mock_client


def test_extract_phrases_with_gemini_parsing(mock_env_and_client):
    # Setup mock response
    mock_instance = mock_env_and_client.return_value
    mock_response = MagicMock()
    mock_response.text = """
    [
        {
            "Korean": "자리를 잡다",
            "English": "to settle in / take root",
            "Etymology": "자리 (place) + 잡다 (to catch)",
            "Part of Speech": "Phrase",
            "Example Sentence": "이 문화는 한국 사회에 자리를 잡게 되었다.",
            "Sentence Translation": "This culture came to take root in Korean society."
        }
    ]
    """
    mock_instance.models.generate_content.return_value = mock_response

    # Call the function
    phrases = extract_phrases_with_gemini("some text", limit=1)

    # Assertions
    assert len(phrases) == 1
    assert phrases[0]["Korean"] == "자리를 잡다"
    assert phrases[0]["Part of Speech"] == "Phrase"
    assert phrases[0]["English"] == "to settle in / take root"


def test_translate_with_gemini_batching(mock_env_and_client):
    # Setup mock response
    mock_instance = mock_env_and_client.return_value
    mock_response = MagicMock()
    mock_response.text = """
    [
        {
            "Korean": "학교",
            "English": "school",
            "Sentence Translation": "I go to school.",
            "Etymology": "學 (study) + 校 (school)"
        }
    ]
    """
    mock_instance.models.generate_content.return_value = mock_response

    words = [
        {"Korean": "학교", "Part of Speech": "Noun", "Example Sentence": "학교에 가요."}
    ]

    # Call the function
    translated = translate_with_gemini(words)

    # Assertions
    assert len(translated) == 1
    assert translated[0]["English"] == "school"
    assert translated[0]["Etymology"] == "學 (study) + 校 (school)"
