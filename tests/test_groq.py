import pytest

from black_bloc.groq import CHAT_URL, DEFAULT_MODEL, GroqClient, message_text
from black_bloc.llm import (
    BROKEN,
    GROQ,
    MAX_TOKENS,
    RATE_LIMITED,
    REFUSED,
    UNREACHABLE,
    LLMError,
    Usage,
)


def answering(status=200, payload=None, raises=None):
    seen = {}

    async def request(url, *, headers, json):
        seen.update({"url": url, "headers": headers, "json": json})
        if raises is not None:
            raise raises
        return status, payload if payload is not None else {}

    return request, seen


def said(text="Pull up a chair.", tokens=True):
    body = {"choices": [{"message": {"role": "assistant", "content": text}}]}
    if tokens:
        body["usage"] = {"prompt_tokens": 30, "completion_tokens": 12}
    return body


def test_the_answer_is_read_out_of_the_first_choice_that_has_words():
    assert message_text(said("hi")) == "hi"
    assert message_text({"choices": [{"message": {"content": ""}}, *said("later")["choices"]]}) == (
        "later"
    )
    assert message_text({}) == ""


async def test_the_post_is_the_openai_compatible_shape_with_the_same_ceiling():
    request, seen = answering(payload=said())
    client = GroqClient("k", request=request)
    answer = await client.reply(system="be warm", messages=[{"role": "user", "content": "hi"}])
    assert seen["url"] == CHAT_URL
    assert seen["json"]["model"] == DEFAULT_MODEL
    assert seen["json"]["max_tokens"] == MAX_TOKENS
    assert seen["json"]["messages"][0] == {"role": "system", "content": "be warm"}
    assert seen["json"]["messages"][1] == {"role": "user", "content": "hi"}
    assert answer.provider == GROQ
    assert answer.usage == Usage(input_tokens=30, output_tokens=12)


async def test_the_model_comes_from_the_setting_so_groqs_churn_is_a_settings_change():
    request, seen = answering(payload=said())
    await GroqClient("k", model="llama-4-whatever", request=request).reply(
        system="s", messages=[]
    )
    assert seen["json"]["model"] == "llama-4-whatever"


async def test_a_blank_model_setting_falls_back_to_the_pinned_default():
    request, seen = answering(payload=said())
    await GroqClient("k", model="", request=request).reply(system="s", messages=[])
    assert seen["json"]["model"] == DEFAULT_MODEL


async def test_the_key_rides_the_authorization_header_and_nothing_else():
    request, seen = answering(payload=said())
    await GroqClient("secret-groq-key", request=request).reply(system="s", messages=[])
    assert seen["headers"]["Authorization"] == "Bearer secret-groq-key"
    assert "secret-groq-key" not in str(seen["json"])


async def test_each_status_becomes_the_reason_that_decides_what_the_ladder_does_next():
    for status, reason in ((429, RATE_LIMITED), (401, REFUSED), (400, REFUSED), (502, UNREACHABLE)):
        request, _ = answering(status=status, payload={})
        with pytest.raises(LLMError) as caught:
            await GroqClient("k", request=request).reply(system="s", messages=[])
        assert caught.value.reason == reason
        assert caught.value.status == status


async def test_an_answer_with_no_words_in_it_is_a_failure_not_a_silent_blank():
    request, _ = answering(payload={"choices": [{"message": {"content": ""}}]})
    with pytest.raises(LLMError) as caught:
        await GroqClient("k", request=request).reply(system="s", messages=[])
    assert caught.value.reason == BROKEN


async def test_a_transport_error_is_wrapped_at_the_boundary_so_callers_catch_one_type():
    request, _ = answering(raises=LLMError(UNREACHABLE, "groq unreachable: OSError"))
    with pytest.raises(LLMError) as caught:
        await GroqClient("k", request=request).reply(system="s", messages=[])
    assert caught.value.reason == UNREACHABLE

    request, _ = answering(raises=ValueError("odd"))
    with pytest.raises(LLMError) as caught:
        await GroqClient("k", request=request).reply(system="s", messages=[])
    assert caught.value.reason == BROKEN


async def test_closing_a_client_that_never_opened_a_session_is_quiet():
    await GroqClient("k", request=answering()[0]).close()
