from app.core.idempotency import streaming_checksum


def test_streaming_checksum_matches_single_buffer() -> None:
    data = b"hello-world"
    assert streaming_checksum([data]) == streaming_checksum([b"hello", b"-", b"world"])
