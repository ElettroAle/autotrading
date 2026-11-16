from autotrading.application.flows.read_default_system_prompt import (
    DefaultSystemPrompt,
    ReadDefaultSystemPromptUseCase,
)
from autotrading.domain.flows.system_prompt import DEFAULT_SYSTEM_PROMPT, PromptPlaceholder


def test_the_default_is_the_template_of_the_platform_with_every_declared_placeholder() -> None:
    assert ReadDefaultSystemPromptUseCase().execute() == DefaultSystemPrompt(
        DEFAULT_SYSTEM_PROMPT,
        (
            PromptPlaceholder.INSTRUCTIONS,
            PromptPlaceholder.ACTIONS,
            PromptPlaceholder.MAX_LEVERAGE,
            PromptPlaceholder.ASSETS,
        ),
    )
