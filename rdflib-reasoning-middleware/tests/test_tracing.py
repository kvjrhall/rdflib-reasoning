from types import SimpleNamespace
from uuid import uuid4

import pytest
from rdflib_reasoning.middleware import TraceRecorder, TraceSink


def test_trace_sink_snapshot_and_clear() -> None:
    sink = TraceSink(max_events=2)
    recorder = TraceRecorder(sink)

    recorder.on_tool_start(
        {"name": "add_triples"},
        "{}",
        run_id=uuid4(),
        inputs={"triples": []},
    )
    recorder.on_tool_end(
        SimpleNamespace(
            name="add_triples",
            tool_call_id="call-1",
            content='{"updated": 0, "message": "ok"}',
        ),
        run_id=uuid4(),
    )

    snapshot = sink.snapshot()

    assert len(snapshot) == 2
    assert snapshot[0].kind == "tool_start"
    assert snapshot[0].name == "add_triples"
    assert snapshot[1].kind == "tool_end"
    assert snapshot[1].payload["tool_call_id"] == "call-1"

    sink.clear()

    assert sink.snapshot() == ()


def test_trace_recorder_captures_llm_events() -> None:
    sink = TraceSink()
    recorder = TraceRecorder(sink)
    run_id = uuid4()

    recorder.on_llm_new_token(
        "[TOOL_CALLS]",
        chunk=SimpleNamespace(
            content="[TOOL_CALLS]",
            tool_call_chunks=[
                {
                    "index": 0,
                    "id": "call-1",
                    "name": "add_triples",
                    "args": '{"triples":[]}',
                }
            ],
        ),
        run_id=run_id,
    )
    recorder.on_llm_end(
        SimpleNamespace(
            generations=[
                [
                    SimpleNamespace(
                        text="",
                        message=SimpleNamespace(
                            content="",
                            tool_calls=[{"name": "add_triples"}],
                            invalid_tool_calls=[],
                            response_metadata={"finish_reason": "tool_calls"},
                        ),
                    )
                ]
            ]
        ),
        run_id=run_id,
    )

    snapshot = sink.snapshot()

    assert [event.kind for event in snapshot] == ["llm_new_token", "llm_end"]
    assert snapshot[0].payload["tool_call_chunks"][0]["name"] == "add_triples"
    assert snapshot[1].payload["response_metadata"]["finish_reason"] == "tool_calls"


def test_live_notebook_trace_attach_and_stop(monkeypatch) -> None:
    pytest.importorskip("IPython")
    from rdflib_reasoning.middleware.tracing_notebook import LiveNotebookTrace

    class _Handle:
        def __init__(self) -> None:
            self.updates: list[object] = []

        def update(self, value: object) -> None:
            self.updates.append(value)

    handle = _Handle()

    monkeypatch.setattr(
        "rdflib_reasoning.middleware.tracing_notebook.display",
        lambda value, display_id: handle,
    )
    monkeypatch.setattr(
        "rdflib_reasoning.middleware.tracing_notebook.Markdown",
        lambda text: text,
    )

    trace = LiveNotebookTrace(refresh_interval_seconds=0.01)

    class _Runnable:
        def __init__(self) -> None:
            self.config: dict[str, object] | None = None

        def with_config(self, config: dict[str, object]) -> "_Runnable":
            self.config = config
            return self

    runnable = _Runnable()

    attached = trace.attach(runnable)
    assert attached is runnable
    assert runnable.config == {"callbacks": [trace.recorder]}

    trace.start()
    trace.recorder.on_tool_start(
        {"name": "serialize_dataset"},
        "{}",
        run_id=uuid4(),
        inputs={"format": "turtle"},
    )
    trace.stop()

    assert handle.updates
