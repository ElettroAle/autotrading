import logging
import time


class UtcFormatter(logging.Formatter):
    """Writes the moment of every record in UTC, ISO 8601, whatever the clock of the machine says.

    The services take it from the logging configuration of uvicorn (deploy/logging.json), which sends the records of
    the application to the output of the container: the register of the decryptions among them (ADR 0102).
    """

    @staticmethod
    def converter(seconds: float | None = None, /) -> time.struct_time:
        return time.gmtime(seconds)
