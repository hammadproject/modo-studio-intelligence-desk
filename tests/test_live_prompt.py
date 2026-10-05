from app.providers.live import build_answer_system
from app.services.chat import guard_customer_answer


def test_live_answer_prompt_enforces_concise_default():
    prompt = build_answer_system(
        "Use approved Modo Studio knowledge.",
        "[source:timeline]\nBrand Foundation typically takes 5–7 weeks.",
    )

    assert "1 to 3 short sentences" in prompt
    assert "no more than 100 words" in prompt
    assert "Markdown bullet list" in prompt
    assert "numbered Markdown list" in prompt
    assert "Bottom line" in prompt
    assert "only when the user explicitly asks for detail" in prompt
    assert "[source:timeline]" in prompt


def test_assistant_config_builds_customer_facing_prompt(settings):
    assistant = settings.load_assistant_config()

    assert assistant.assistant.name == "Ren"
    assert "Never expose internal implementation language" in (
        assistant.customer_facing_instructions
    )
    assert "knowledge base" in assistant.customer_facing_instructions


def test_internal_language_guard_replaces_unsafe_answer(settings):
    assistant = settings.load_assistant_config()
    guarded, replaced = guard_customer_answer(
        "The knowledge base does not list that timeline.",
        assistant.customer_facing_language.internal_terms_to_avoid,
        assistant.general_behavior.unknown_business_detail.response,
    )

    assert replaced is True
    assert "knowledge base" not in guarded.lower()
    assert guarded == assistant.general_behavior.unknown_business_detail.response
