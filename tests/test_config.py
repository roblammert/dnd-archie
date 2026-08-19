from archie.config import settings


def test_llm_runtime_settings_exist():
    assert isinstance(settings.llm_timeout, float)
    assert settings.llm_timeout > 0

    assert isinstance(settings.llm_max_tokens, int)
    assert settings.llm_max_tokens > 0
