from types import SimpleNamespace

from langchain_core.messages import SystemMessage
from rdflib_reasoning.middleware.ministral_middleware import (
    MinistralPromptSuffixMiddleware,
)


def test_wrap_model_call_appends_ministral_prompt_suffix() -> None:
    middleware = MinistralPromptSuffixMiddleware()

    request = SimpleNamespace(
        system_message=SystemMessage(content="Base prompt"),
        override=lambda **kwargs: SimpleNamespace(**kwargs),
    )

    captured = {}

    def handler(next_request):
        captured["system_message"] = next_request.system_message
        return "ok"

    result = middleware.wrap_model_call(request, handler)

    assert result == "ok"
    assert "HOW YOU SHOULD THINK AND ANSWER" in str(captured["system_message"].content)


def test_ministral_middleware_has_no_after_model_intervention() -> None:
    middleware = MinistralPromptSuffixMiddleware()
    state = {"messages": []}

    result = middleware.after_model(state, runtime=None)

    assert result is None
