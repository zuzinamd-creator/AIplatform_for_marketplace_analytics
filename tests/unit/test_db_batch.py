from app.etl.db_batch import INSERT_BATCH_SIZE, iter_batches


def test_iter_batches_chunks_list() -> None:
    values = list(range(12_001))
    batches = list(iter_batches(values, batch_size=INSERT_BATCH_SIZE))
    assert len(batches) == 3
    assert len(batches[0]) == INSERT_BATCH_SIZE
    assert len(batches[-1]) == 2001
