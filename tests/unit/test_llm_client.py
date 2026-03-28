import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from google.api_core import exceptions as gexc

from backend.utils.llm_client import GeminiInvalidKeyError, GeminiRateLimitError, LLMClient, probe_gemini_status


@pytest.mark.asyncio
async def test_llm_client_falls_back_to_next_model():
    def model_factory(model_name):
        model = MagicMock()
        if model_name == 'gemini-2.5-flash':
            model.generate_content.side_effect = gexc.NotFound('model not found')
        elif model_name == 'gemini-2.0-flash':
            model.generate_content.return_value = MagicMock(text='fallback answer')
        else:
            model.generate_content.side_effect = AssertionError(f'unexpected model {model_name}')
        return model

    with patch('backend.utils.llm_client.genai.GenerativeModel', side_effect=model_factory) as mock_model_cls:
        llm = LLMClient(api_key='AIzaSyC_valid_key_for_testing_1234567890')
        result = await llm.summarize('This is a test document.')

    assert result == 'fallback answer'
    assert [call.args[0] for call in mock_model_cls.call_args_list[:2]] == [
        'gemini-2.5-flash',
        'gemini-2.0-flash',
    ]


@pytest.mark.asyncio
async def test_llm_client_raises_invalid_key_error():
    def model_factory(_model_name):
        model = MagicMock()
        model.generate_content.side_effect = gexc.Unauthenticated('invalid api key')
        return model

    with patch('backend.utils.llm_client.genai.GenerativeModel', side_effect=model_factory):
        llm = LLMClient(api_key='AIzaSyC_invalid_key_for_testing_123456')
        with pytest.raises(GeminiInvalidKeyError) as exc_info:
            await llm.summarize('This is a test document.')

    assert exc_info.value.status_code == 401
    assert exc_info.value.error_code == 'invalid_api_key'


@pytest.mark.asyncio
async def test_llm_client_raises_rate_limit_error_when_all_models_fail():
    def model_factory(_model_name):
        model = MagicMock()
        model.generate_content.side_effect = gexc.ResourceExhausted('quota exceeded')
        return model

    with patch('backend.utils.llm_client.genai.GenerativeModel', side_effect=model_factory):
        llm = LLMClient(api_key='AIzaSyC_rate_limit_key_for_testing_12345')
        with pytest.raises(GeminiRateLimitError) as exc_info:
            await llm.summarize('This is a test document.')

    assert exc_info.value.status_code == 429
    assert exc_info.value.error_code == 'rate_limited'


def test_probe_gemini_status_reports_degraded_when_primary_model_missing():
    models = [
        SimpleNamespace(name='models/gemini-2.0-flash', supported_generation_methods=['generateContent']),
        SimpleNamespace(name='models/gemini-1.5-pro', supported_generation_methods=['generateContent']),
    ]

    with patch('backend.utils.llm_client.genai.list_models', return_value=models):
        status = probe_gemini_status('AIzaSyC_valid_key_for_testing_1234567890')

    assert status['status'] == 'degraded'
    assert status['model_status'] == 'fallback'
    assert status['active_model'] == 'gemini-2.0-flash'
    assert status['available_models'][0] == 'gemini-2.0-flash'
