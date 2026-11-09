from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from scripts.sca_national_independent_layer_census_z9 import LAYERS, session, write_checkpoint


def test_census_session_is_reused_within_worker_thread():
    first = session()
    second = session()
    assert first is second


def test_census_session_is_thread_local():
    main_session = session()
    with ThreadPoolExecutor(max_workers=1) as pool:
        worker_session = pool.submit(session).result()
    assert worker_session is not main_session


def test_checkpoint_uses_requested_path_and_includes_timestamp(tmp_path):
    output = tmp_path / "nested" / "census.json"
    summary = write_checkpoint([], total=0, complete=0, out_path=output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["generated_at"].endswith("Z")
    assert payload["summary"]["tiles_completed"] == 0
    assert summary["tiles_in_bbox"] == 0
    assert set(payload["source_layers"]) == set(LAYERS)
