import pytest

from models import validate_iso6346


def test_known_valid_id():
    # Canonical example from the handover docs
    assert validate_iso6346("MSKU1234565") is True


def test_wrong_check_digit():
    assert validate_iso6346("MSKU1234560") is False


@pytest.mark.parametrize("bad", [
    "",                # empty
    "MSKU123456",      # too short
    "MSKU12345678",    # too long
    "msku1234565",     # lowercase
    "MSK41234565",     # digit in owner code
    "MSKUABCDEFG",     # letters in serial
    "MSKU١٢٣٤٥٦٥",     # Arabic-Indic digits, not ASCII
])
def test_malformed_ids(bad):
    assert validate_iso6346(bad) is False


def test_another_valid_id():
    # CSQU3054383 is the ISO 6346 spec's own worked example
    assert validate_iso6346("CSQU3054383") is True
