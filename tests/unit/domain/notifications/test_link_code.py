import hashlib

import pytest

from autotrading.domain.notifications.link_code import ALPHABET, LinkCode


def test_a_new_code_has_eight_characters_of_the_unambiguous_alphabet() -> None:
    code = LinkCode.new()

    assert len(code.text) == 8
    assert set(code.text) <= set(ALPHABET)
    assert not set(code.text) & set("01IO")


def test_two_new_codes_differ() -> None:
    assert len({LinkCode.new().text for _ in range(50)}) == 50


def test_the_digest_is_the_sha256_of_the_code() -> None:
    assert LinkCode("ABCD2345").digest == hashlib.sha256(b"ABCD2345").digest()


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ("ABCD2345", "ABCD2345"),
        ("  abcd2345 \n", "ABCD2345"),
        ("/start ABCD2345", "ABCD2345"),
        ("/START abcd2345", "ABCD2345"),
        ("hello there", "HELLO THERE"),
    ],
)
def test_the_code_of_a_message_is_read_alone_or_after_the_start_command(message: str, code: str) -> None:
    assert LinkCode.in_message(message) == LinkCode(code)


@pytest.mark.parametrize("message", ["", "   ", "/start", "/START  ", "/help", "/help ABCD2345", "/stop now"])
def test_a_message_without_a_code_or_with_another_command_has_no_code(message: str) -> None:
    assert LinkCode.in_message(message) is None


def test_the_code_never_shows_in_its_representation() -> None:
    assert "ABCD2345" not in repr(LinkCode("ABCD2345"))


def test_the_alphabet_leaves_out_the_characters_a_reader_confuses() -> None:
    assert not set(ALPHABET) & set("01IO")
    assert len(set(ALPHABET)) == len(ALPHABET) == 32
