from autotrading.application.sources.errors import AssetRequiredError
from autotrading.application.sources.ports import SocialPort, SourceRequest
from autotrading.domain.sources.social import POSTS
from autotrading.domain.sources.source_sample import SourceValue


class ReadSocialUseCase:
    """Reads what is said of an asset on the social networks: the figures of the last 24 hours refer to the instant of
    the reading, every post kept, up to the number of the adapter, to its own (R5.1.3, ADR
    fonte-social-con-adapter-lunarcrush)."""

    def __init__(self, social: SocialPort) -> None:
        self._social = social

    def execute(self, command: SourceRequest) -> tuple[SourceValue, ...]:
        if command.asset is None:
            raise AssetRequiredError
        posts = command.settings[POSTS]
        snapshot = self._social.snapshot(command.asset, posts, command.credentials)
        kept = tuple(SourceValue(post.at, post.values()) for post in snapshot.most_relevant(posts))
        return (SourceValue(command.now, snapshot.values()), *kept)
