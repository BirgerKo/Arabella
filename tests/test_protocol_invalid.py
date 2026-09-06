import pytest
from blauberg_vento.exceptions import VentoChecksumError, VentoProtocolError
from blauberg_vento.protocol import parse_response, verify_checksum


@pytest.mark.parametrize(
    "raw, expected_error",
    [
        (b"\xFD\xFD\x02\x10", VentoProtocolError),
        (b"\x00\x00\x00\x00", VentoProtocolError),
        (b"\xFD\xFD\x02\x10" + b"\x00" * 16 + b"\x00\x06" + b"\x00\x00", VentoChecksumError),
    ],
)
def test_invalid_packet_rejections(raw: bytes, expected_error: type[Exception]) -> None:
    with pytest.raises(expected_error):
        if len(raw) >= 4 and raw[:2] == b"\xFD\xFD":
            verify_checksum(raw)
        parse_response(raw)


def test_parse_response_rejects_truncated_packet() -> None:
    raw = b"\xFD\xFD\x02\x10" + b"\x00" * 16 + b"\x00\x06" + b"\x00\x00"
    with pytest.raises(VentoProtocolError):
        parse_response(raw)
