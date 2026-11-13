from dataclasses import dataclass, field

DEFAULT_PORT = 5432


@dataclass(frozen=True, slots=True)
class _SqlAlchemySettings:
    """Where the database of the installation is and who connects; the password comes from a mounted file."""

    host: str
    name: str
    user: str
    password: str = field(repr=False)
    port: int = DEFAULT_PORT
