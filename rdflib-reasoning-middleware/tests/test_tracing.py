from types import SimpleNamespace
from uuid import uuid4

import pytest
from langchain_core.messages import ToolMessage
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


def test_trace_recorder_captures_error_tool_messages_from_chain_end() -> None:
    sink = TraceSink()
    recorder = TraceRecorder(sink)
    run_id = uuid4()

    recorder.on_chain_end(
        {
            "messages": [
                ToolMessage(
                    content="Misuse: `reset_dataset` was rejected.",
                    name="reset_dataset",
                    tool_call_id="call-1",
                    status="error",
                )
            ]
        },
        run_id=run_id,
    )

    snapshot = sink.snapshot()

    assert [event.kind for event in snapshot] == ["tool_message"]
    assert snapshot[0].name == "reset_dataset"
    assert snapshot[0].payload["status"] == "error"
    assert snapshot[0].payload["tool_call_id"] == "call-1"


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


def test_notebook_trace_renderer_shows_requested_and_invalid_tool_calls() -> None:
    pytest.importorskip("IPython")
    from rdflib_reasoning.middleware.tracing import TraceEvent, TraceSink
    from rdflib_reasoning.middleware.tracing_notebook import NotebookTraceRenderer

    sink = TraceSink()
    sink.append(
        TraceEvent(
            kind="llm_end",
            run_id=uuid4(),
            payload={
                "content": "",
                "tool_calls": (
                    {
                        "name": "describe_term",
                        "args": {"term": "http://www.w3.org/2000/01/rdf-schema#Class"},
                    },
                ),
                "invalid_tool_calls": (
                    {
                        "name": "list_terms",
                        "args": '{"vocabulary": ',
                        "error": "Expecting value",
                    },
                ),
                "response_metadata": {"finish_reason": "tool_calls"},
            },
        )
    )

    renderer = NotebookTraceRenderer.__new__(NotebookTraceRenderer)
    renderer.sink = sink
    renderer.heading = "Trace"

    markdown = renderer._render_markdown(sink.snapshot())

    assert "#### Requested Tool Calls" in markdown
    assert "`describe_term`" in markdown
    assert '"term": "http://www.w3.org/2000/01/rdf-schema#Class"' in markdown
    assert "#### Invalid Tool Calls" in markdown
    assert '"name": "list_terms"' in markdown


def test_notebook_trace_renderer_compacts_single_tool_lifecycle() -> None:
    pytest.importorskip("IPython")
    from rdflib_reasoning.middleware.tracing import TraceEvent, TraceSink
    from rdflib_reasoning.middleware.tracing_notebook import NotebookTraceRenderer

    sink = TraceSink()
    sink.append(
        TraceEvent(
            kind="llm_end",
            run_id=uuid4(),
            payload={
                "content": "",
                "tool_calls": (
                    {
                        "name": "serialize_dataset",
                        "args": {"format": "turtle"},
                    },
                ),
                "invalid_tool_calls": (),
                "response_metadata": {"finish_reason": "tool_calls"},
            },
        )
    )
    sink.append(
        TraceEvent(
            kind="tool_start",
            run_id=uuid4(),
            name="serialize_dataset",
            payload={"inputs": {"format": "turtle"}},
        )
    )
    sink.append(
        TraceEvent(
            kind="tool_end",
            run_id=uuid4(),
            name="serialize_dataset",
            payload={"output": "@prefix ex: <http://example.com/> ."},
        )
    )

    renderer = NotebookTraceRenderer.__new__(NotebookTraceRenderer)
    renderer.sink = sink
    renderer.heading = "Trace"

    markdown = renderer._render_markdown(sink.snapshot())

    assert "#### Requested Tool Calls" not in markdown
    assert "### Tool Call: serialize_dataset" not in markdown
    assert "### Tool Result: serialize_dataset" not in markdown
    assert "### Tool: serialize_dataset" in markdown
    assert "#### Arguments" in markdown
    assert "#### Result" in markdown
    assert '"format": "turtle"' in markdown


def test_notebook_trace_renderer_shows_tool_rejection() -> None:
    pytest.importorskip("IPython")
    from rdflib_reasoning.middleware.tracing import TraceEvent, TraceSink
    from rdflib_reasoning.middleware.tracing_notebook import NotebookTraceRenderer

    sink = TraceSink()
    sink.append(
        TraceEvent(
            kind="tool_message",
            run_id=uuid4(),
            name="reset_dataset",
            payload={
                "content": "Misuse: `reset_dataset` was rejected.",
                "tool_call_id": "call-1",
                "status": "error",
            },
        )
    )

    renderer = NotebookTraceRenderer.__new__(NotebookTraceRenderer)
    renderer.sink = sink
    renderer.heading = "Trace"

    markdown = renderer._render_markdown(sink.snapshot())

    assert "### Tool: reset_dataset" in markdown
    assert "#### Rejection" in markdown
    assert '"status": "error"' in markdown
    assert "Misuse: `reset_dataset` was rejected." in markdown
