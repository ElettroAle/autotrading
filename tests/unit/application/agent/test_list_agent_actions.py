from autotrading.application.agent.list_agent_actions import ListAgentActionsUseCase


def test_the_actions_are_the_words_the_answer_of_the_agent_admits() -> None:
    assert ListAgentActionsUseCase().execute() == ("apri", "chiudi", "mantieni", "aggiorna", "inverti")
