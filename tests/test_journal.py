import pytest

from autofed.accounting.journal import JournalEntry, JournalLine


def test_journal_rejects_unbalanced() -> None:
    with pytest.raises(ValueError, match="unbalanced"):
        JournalEntry(
            0,
            (
                JournalLine("a", -10.0),
                JournalLine("b", 5.0),
            ),
            memo="bad",
        )


def test_journal_accepts_balanced() -> None:
    e = JournalEntry(
        0,
        (
            JournalLine("a", -10.0),
            JournalLine("b", 10.0),
        ),
        memo="ok",
    )
    assert e.balanced()
