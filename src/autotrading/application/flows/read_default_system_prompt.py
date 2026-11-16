from dataclasses import dataclass

from autotrading.domain.flows.system_prompt import DEFAULT_SYSTEM_PROMPT, PromptPlaceholder


@dataclass(frozen=True, slots=True)
class DefaultSystemPrompt:
    template: str
    placeholders: tuple[PromptPlaceholder, ...]


class ReadDefaultSystemPromptUseCase:
    """The system prompt a new flow follows until the user writes its own, with the placeholders a template may use
    (R1.4.8).
    """

    def execute(self) -> DefaultSystemPrompt:
        return DefaultSystemPrompt(DEFAULT_SYSTEM_PROMPT, tuple(PromptPlaceholder))
