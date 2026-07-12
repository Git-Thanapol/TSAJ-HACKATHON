from records import store


def _conn(tmp_path):
    return store.get_conn(str(tmp_path / "t.db"))


def test_genesis_and_chain_linkage(tmp_path):
    conn = _conn(tmp_path)
    e1 = store.append_event(conn, inspection_id="insp_a", container_id="MSKU1234565",
                            type="inspection.started", payload={"direction": "inbound"})
    e2 = store.append_event(conn, inspection_id="insp_b", container_id="MSKU1234565",
                            type="inspection.started", payload={"direction": "outbound"})
    assert e1["prev_hash"] == store.GENESIS
    assert e2["prev_hash"] == e1["hash"]
    assert len(e1["hash"]) == 64


def test_chains_are_per_container(tmp_path):
    conn = _conn(tmp_path)
    store.append_event(conn, inspection_id="i1", container_id="MSKU1234565",
                       type="inspection.started", payload={})
    other = store.append_event(conn, inspection_id="i2", container_id="CSQU3054383",
                               type="inspection.started", payload={})
    assert other["prev_hash"] == store.GENESIS


def test_history_order_and_verify(tmp_path):
    conn = _conn(tmp_path)
    for n in range(3):
        store.append_event(conn, inspection_id=f"i{n}", container_id="MSKU1234565",
                           type="inspection.started", payload={"n": n})
    events = store.get_history(conn, "MSKU1234565")
    assert [e["inspection_id"] for e in events] == ["i0", "i1", "i2"]
    ok, bad = store.verify_chain(events)
    assert ok is True and bad is None


def test_tamper_detection(tmp_path):
    conn = _conn(tmp_path)
    for n in range(3):
        store.append_event(conn, inspection_id=f"i{n}", container_id="MSKU1234565",
                           type="inspection.started", payload={"n": n})
    events = store.get_history(conn, "MSKU1234565")
    events[1]["payload_json"] = '{"n":99}'  # tamper in memory
    ok, bad = store.verify_chain(events)
    assert ok is False and bad == 1


def test_event_ids_unique(tmp_path):
    conn = _conn(tmp_path)
    ids = {store.append_event(conn, inspection_id="i", container_id="MSKU1234565",
                              type="t", payload={})["event_id"] for _ in range(50)}
    assert len(ids) == 50


def test_concurrent_appends_do_not_fork_chain(tmp_path):
    import threading

    db = str(tmp_path / "t.db")
    store.get_conn(db).close()  # create schema once

    def worker(n):
        conn = store.get_conn(db)
        try:
            store.append_event(conn, inspection_id=f"i{n}", container_id="MSKU1234565",
                               type="inspection.started", payload={"n": n})
        finally:
            conn.close()

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    conn = store.get_conn(db)
    events = store.get_history(conn, "MSKU1234565")
    assert len(events) == 10
    ok, bad = store.verify_chain(events)
    assert ok is True and bad is None
    prev_hashes = [e["prev_hash"] for e in events]
    assert len(set(prev_hashes)) == 10  # no fork: every event chains to a distinct predecessor


def test_append_after_plain_sql_write_on_same_conn(tmp_path):
    # API routes write inspections/idempotency via plain SQL on the same
    # connection before appending events; must not raise nested-transaction errors.
    conn = _conn(tmp_path)
    conn.execute(
        "INSERT INTO inspections (inspection_id, container_id, direction, standard_name, status, created_at)"
        " VALUES ('i1', 'MSKU1234565', 'inbound', 'IICL-6', 'started', datetime('now'))"
    )
    event = store.append_event(conn, inspection_id="i1", container_id="MSKU1234565",
                               type="inspection.started", payload={})
    assert event["prev_hash"] == store.GENESIS
    row = conn.execute("SELECT status FROM inspections WHERE inspection_id='i1'").fetchone()
    assert row["status"] == "started"
