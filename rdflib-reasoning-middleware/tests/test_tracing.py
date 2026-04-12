from types import SimpleNamespace
from uuid import uuid4

import pytest
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from rdflib_reasoning.middleware import TraceRecorder, TraceSink, TurnTracer
from rdflib_reasoning.middleware.tracing import TraceEvent


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


def test_trace_recorder_prefers_tool_message_artifact_on_tool_end() -> None:
    from langchain_core.messages import ToolMessage
    from rdflib_reasoning.middleware.rdf_vocabulary_middleware import (
        TermInspectionResponse,
    )

    sink = TraceSink()
    recorder = TraceRecorder(sink)
    run_id = uuid4()
    artifact = TermInspectionResponse(
        uri="<http://www.w3.org/2000/01/rdf-schema#label>",
        label="label",
        definition="A human-readable name for the subject.",
        termType="property",
        vocabulary="<http://www.w3.org/2000/01/rdf-schema#>",
        domain=("<http://www.w3.org/2000/01/rdf-schema#Resource>",),
        range=("<http://www.w3.org/2000/01/rdf-schema#Literal>",),
    )

    recorder.on_tool_end(
        ToolMessage(
            content="label",
            artifact=artifact,
            name="inspect_term",
            tool_call_id="call-1",
        ),
        run_id=run_id,
    )

    snapshot = sink.snapshot()

    assert snapshot[0].kind == "tool_end"
    assert snapshot[0].payload["tool_call_id"] == "call-1"
    assert snapshot[0].payload["output"] == artifact


def test_trace_recorder_captures_llm_events_and_input_summary() -> None:
    sink = TraceSink()
    recorder = TraceRecorder(sink)
    run_id = uuid4()

    recorder.on_chat_model_start(
        {"name": "test-model"},
        [[SystemMessage(content="System prompt"), HumanMessage(content="Question?")]],
        run_id=run_id,
    )
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
                            tool_calls=[{"id": "call-1", "name": "add_triples"}],
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

    assert [event.kind for event in snapshot] == [
        "chat_model_start",
        "llm_new_token",
        "llm_end",
    ]
    assert snapshot[0].payload["input_summary"][1]["content_preview"] == "Question?"
    assert snapshot[1].payload["tool_call_chunks"][0]["name"] == "add_triples"
    assert snapshot[2].payload["response_metadata"]["finish_reason"] == "tool_calls"


def test_trace_recorder_captures_all_tool_messages_from_chain_end() -> None:
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
                ),
                ToolMessage(
                    content="Already satisfied.",
                    name="add_triples",
                    tool_call_id="call-2",
                    status="success",
                ),
            ]
        },
        run_id=run_id,
    )

    snapshot = sink.snapshot()

    assert [event.kind for event in snapshot] == ["tool_message", "tool_message"]
    assert snapshot[0].payload["status"] == "success"
    assert snapshot[1].payload["status"] == "error"


def test_turn_tracer_correlates_simple_tool_turn() -> None:
    run_id = uuid4()
    sink = TraceSink()
    sink.append(
        TraceEvent(
            kind="chat_model_start",
            run_id=run_id,
            payload={
                "input_summary": (
                    {"type": "system", "content_preview": "System prompt"},
                    {"type": "human", "content_preview": "Create RDF."},
                )
            },
        )
    )
    sink.append(
        TraceEvent(
            kind="llm_end",
            run_id=run_id,
            payload={
                "content": "",
                "tool_calls": (
                    {"id": "call-1", "name": "add_triples", "args": {"triples": []}},
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
            name="add_triples",
            payload={"inputs": {"triples": []}},
        )
    )
    sink.append(
        TraceEvent(
            kind="tool_end",
            run_id=uuid4(),
            name="add_triples",
            payload={"output": {"updated": 1}, "tool_call_id": "call-1"},
        )
    )

    turns = TurnTracer().snapshot(sink.snapshot())

    assert len(turns) == 1
    turn = turns[0]
    assert len(turn.requested_tool_calls) == 1
    assert turn.requested_tool_calls[0]["name"] == "add_triples"
    assert len(turn.tool_invocations) == 1
    assert turn.tool_invocations[0].tool_call_id == "call-1"
    assert turn.tool_invocations[0].result == {"updated": 1}


def test_turn_tracer_correlates_multi_tool_turn() -> None:
    run_id = uuid4()
    turns = TurnTracer().snapshot(
        (
            TraceEvent(
                kind="chat_model_start",
                run_id=run_id,
                payload={"input_summary": ()},
            ),
            TraceEvent(
                kind="llm_end",
                run_id=run_id,
                payload={
                    "content": "",
                    "tool_calls": (
                        {"id": "call-1", "name": "list_terms", "args": {"limit": 5}},
                        {"id": "call-2", "name": "inspect_term", "args": {"term": "x"}},
                    ),
                    "invalid_tool_calls": (),
                    "response_metadata": {"finish_reason": "tool_calls"},
                },
            ),
            TraceEvent(
                kind="tool_end",
                run_id=uuid4(),
                name="list_terms",
                payload={"output": {"terms": []}, "tool_call_id": "call-1"},
            ),
            TraceEvent(
                kind="tool_end",
                run_id=uuid4(),
                name="inspect_term",
                payload={"output": {"label": "Class"}, "tool_call_id": "call-2"},
            ),
        )
    )

    assert len(turns) == 1
    assert [call.name for call in turns[0].tool_invocations] == [
        "list_terms",
        "inspect_term",
    ]


def test_turn_tracer_correlates_final_answer_turn() -> None:
    run_id = uuid4()

    turns = TurnTracer().snapshot(
        (
            TraceEvent(
                kind="chat_model_start",
                run_id=run_id,
                payload={
                    "input_summary": (
                        {"type": "human", "content_preview": "Summarize the graph."},
                    )
                },
            ),
            TraceEvent(
                kind="llm_new_token",
                run_id=run_id,
                payload={"token": "Done.", "content": "Done.", "tool_call_chunks": ()},
            ),
            TraceEvent(
                kind="llm_end",
                run_id=run_id,
                payload={
                    "content": "Done.",
                    "tool_calls": (),
                    "invalid_tool_calls": (),
                    "response_metadata": {"finish_reason": "stop"},
                },
            ),
        )
    )

    assert len(turns) == 1
    assert turns[0].agent_output == "Done."
    assert turns[0].final_content == "Done."
    assert turns[0].response_metadata["finish_reason"] == "stop"


def test_turn_tracer_keeps_non_error_tool_messages() -> None:
    run_id = uuid4()
    turns = TurnTracer().snapshot(
        (
            TraceEvent(
                kind="chat_model_start", run_id=run_id, payload={"input_summary": ()}
            ),
            TraceEvent(
                kind="llm_end",
                run_id=run_id,
                payload={
                    "content": "",
                    "tool_calls": (
                        {
                            "id": "call-1",
                            "name": "add_triples",
                            "args": {"triples": []},
                        },
                    ),
                    "invalid_tool_calls": (),
                    "response_metadata": {"finish_reason": "tool_calls"},
                },
            ),
            TraceEvent(
                kind="tool_message",
                run_id=uuid4(),
                name="add_triples",
                payload={
                    "content": "Already satisfied.",
                    "tool_call_id": "call-1",
                    "status": "success",
                },
            ),
        )
    )

    assert turns[0].tool_invocations[0].tool_message == {
        "status": "success",
        "tool_call_id": "call-1",
        "content": "Already satisfied.",
    }


def test_turn_tracer_includes_middleware_injected_reminder_in_input_summary() -> None:
    run_id = uuid4()
    turns = TurnTracer().snapshot(
        (
            TraceEvent(
                kind="chat_model_start",
                run_id=run_id,
                payload={
                    "input_summary": (
                        {"type": "system", "content_preview": "System prompt"},
                        {
                            "type": "human",
                            "content_preview": "[rdflib_reasoning-recovery] A tool call just failed.",
                        },
                    )
                },
            ),
            TraceEvent(
                kind="llm_end",
                run_id=run_id,
                payload={
                    "content": "Retry with fixed triples.",
                    "tool_calls": (),
                    "invalid_tool_calls": (),
                    "response_metadata": {"finish_reason": "stop"},
                },
            ),
        )
    )

    assert (
        turns[0].input_summary[1]["content_preview"]
        == "[rdflib_reasoning-recovery] A tool call just failed."
    )


def test_turn_tracer_preserves_partial_tool_lifecycle() -> None:
    run_id = uuid4()
    turns = TurnTracer().snapshot(
        (
            TraceEvent(
                kind="chat_model_start", run_id=run_id, payload={"input_summary": ()}
            ),
            TraceEvent(
                kind="llm_end",
                run_id=run_id,
                payload={
                    "content": "",
                    "tool_calls": (
                        {
                            "id": "call-1",
                            "name": "serialize_dataset",
                            "args": {"format": "turtle"},
                        },
                    ),
                    "invalid_tool_calls": (),
                    "response_metadata": {"finish_reason": "tool_calls"},
                },
            ),
            TraceEvent(
                kind="tool_start",
                run_id=uuid4(),
                name="serialize_dataset",
                payload={"inputs": {"format": "turtle"}},
            ),
        )
    )

    assert len(turns) == 1
    assert turns[0].tool_invocations[0].name == "serialize_dataset"
    assert turns[0].tool_invocations[0].result is None


def test_turn_tracer_matches_repeated_tool_names_by_tool_call_id() -> None:
    run_id = uuid4()
    turns = TurnTracer().snapshot(
        (
            TraceEvent(
                kind="chat_model_start", run_id=run_id, payload={"input_summary": ()}
            ),
            TraceEvent(
                kind="llm_end",
                run_id=run_id,
                payload={
                    "content": "",
                    "tool_calls": (
                        {
                            "id": "call-1",
                            "name": "add_triples",
                            "args": {"triples": ["first"]},
                        },
                        {
                            "id": "call-2",
                            "name": "add_triples",
                            "args": {"triples": ["second"]},
                        },
                    ),
                    "invalid_tool_calls": (),
                    "response_metadata": {"finish_reason": "tool_calls"},
                },
            ),
            TraceEvent(
                kind="tool_end",
                run_id=uuid4(),
                name="add_triples",
                payload={"output": {"updated": 1}, "tool_call_id": "call-2"},
            ),
            TraceEvent(
                kind="tool_end",
                run_id=uuid4(),
                name="add_triples",
                payload={"output": {"updated": 2}, "tool_call_id": "call-1"},
            ),
        )
    )

    assert turns[0].tool_invocations[0].tool_call_id == "call-1"
    assert turns[0].tool_invocations[0].result == {"updated": 2}
    assert turns[0].tool_invocations[1].tool_call_id == "call-2"
    assert turns[0].tool_invocations[1].result == {"updated": 1}


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
    trace.recorder.on_chat_model_start(
        {"name": "test-model"},
        [[HumanMessage(content="Serialize the dataset.")]],
        run_id=uuid4(),
    )
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
    from rdflib_reasoning.middleware.tracing_notebook import NotebookTraceRenderer

    sink = TraceSink()
    sink.append(
        TraceEvent(
            kind="chat_model_start", run_id=uuid4(), payload={"input_summary": ()}
        )
    )
    sink.append(
        TraceEvent(
            kind="llm_end",
            run_id=uuid4(),
            payload={
                "content": "",
                "tool_calls": (
                    {
                        "id": "call-1",
                        "name": "inspect_term",
                        "args": {"term": "http://www.w3.org/2000/01/rdf-schema#Class"},
                    },
                    {
                        "id": "call-2",
                        "name": "list_terms",
                        "args": {"vocabulary": "http://www.w3.org/2000/01/rdf-schema#"},
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
    assert "`inspect_term`" in markdown
    assert '"term": "http://www.w3.org/2000/01/rdf-schema#Class"' in markdown
    assert "#### Invalid Tool Calls" in markdown
    assert '"name": "list_terms"' in markdown


def test_notebook_trace_renderer_compacts_single_tool_lifecycle() -> None:
    pytest.importorskip("IPython")
    from rdflib_reasoning.middleware.tracing_notebook import NotebookTraceRenderer

    sink = TraceSink()
    run_id = uuid4()
    sink.append(
        TraceEvent(
            kind="chat_model_start", run_id=run_id, payload={"input_summary": ()}
        )
    )
    sink.append(
        TraceEvent(
            kind="llm_end",
            run_id=run_id,
            payload={
                "content": "",
                "tool_calls": (
                    {
                        "id": "call-1",
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
            payload={
                "output": "@prefix ex: <http://example.com/> .",
                "tool_call_id": "call-1",
            },
        )
    )

    renderer = NotebookTraceRenderer.__new__(NotebookTraceRenderer)
    renderer.sink = sink
    renderer.heading = "Trace"

    markdown = renderer._render_markdown(sink.snapshot())

    assert "#### Requested Tool Calls" not in markdown
    assert "### Tool: serialize_dataset" in markdown
    assert "#### Arguments" in markdown
    assert "#### Result" in markdown
    assert '"format": "turtle"' in markdown


def test_notebook_trace_renderer_shows_input_summary_and_tool_messages() -> None:
    pytest.importorskip("IPython")
    from rdflib_reasoning.middleware.tracing_notebook import NotebookTraceRenderer

    sink = TraceSink()
    run_id = uuid4()
    sink.append(
        TraceEvent(
            kind="chat_model_start",
            run_id=run_id,
            payload={
                "input_summary": (
                    {"type": "system", "content_preview": "System prompt"},
                    {
                        "type": "human",
                        "content_preview": "[rdflib_reasoning-recovery] A tool call just failed.",
                    },
                )
            },
        )
    )
    sink.append(
        TraceEvent(
            kind="llm_end",
            run_id=run_id,
            payload={
                "content": "",
                "tool_calls": (
                    {"id": "call-1", "name": "add_triples", "args": {"triples": []}},
                ),
                "invalid_tool_calls": (),
                "response_metadata": {"finish_reason": "tool_calls"},
            },
        )
    )
    sink.append(
        TraceEvent(
            kind="tool_message",
            run_id=uuid4(),
            name="add_triples",
            payload={
                "content": "Already satisfied.",
                "tool_call_id": "call-1",
                "status": "success",
            },
        )
    )

    renderer = NotebookTraceRenderer.__new__(NotebookTraceRenderer)
    renderer.sink = sink
    renderer.heading = "Trace"

    markdown = renderer._render_markdown(sink.snapshot())

    assert "### Model Input Summary" in markdown
    assert "[rdflib_reasoning-recovery] A tool call just failed." in markdown
    assert "#### Message" in markdown
    assert '"status": "success"' in markdown


def test_notebook_trace_renderer_pretty_prints_pydantic_tool_results() -> None:
    pytest.importorskip("IPython")
    from rdflib_reasoning.middleware.rdf_vocabulary_middleware import (
        VocabularyListResponse,
        VocabularySummary,
    )
    from rdflib_reasoning.middleware.tracing_notebook import NotebookTraceRenderer

    sink = TraceSink()
    run_id = uuid4()
    sink.append(
        TraceEvent(
            kind="chat_model_start", run_id=run_id, payload={"input_summary": ()}
        )
    )
    sink.append(
        TraceEvent(
            kind="tool_start",
            run_id=uuid4(),
            name="list_vocabularies",
            payload={"inputs": {}},
        )
    )
    sink.append(
        TraceEvent(
            kind="tool_end",
            run_id=uuid4(),
            name="list_vocabularies",
            payload={
                "output": VocabularyListResponse(
                    vocabularies=(
                        VocabularySummary(
                            namespace="http://www.w3.org/2000/01/rdf-schema#",
                            label="RDFS",
                            description="Schema-level RDF terms.",
                            term_count=15,
                        ),
                    )
                ),
                "tool_call_id": "call-1",
            },
        )
    )

    renderer = NotebookTraceRenderer.__new__(NotebookTraceRenderer)
    renderer.sink = sink
    renderer.heading = "Trace"

    markdown = renderer._render_markdown(sink.snapshot())

    assert "### Tool: list_vocabularies" in markdown
    assert '"label": "RDFS"' in markdown
    assert '"description": "Schema-level RDF terms."' in markdown
    assert "VocabularySummary(" not in markdown


def test_notebook_trace_renderer_pretty_prints_tool_message_artifacts() -> None:
    pytest.importorskip("IPython")
    from langchain_core.messages import ToolMessage
    from rdflib_reasoning.middleware.rdf_vocabulary_middleware import (
        TermInspectionResponse,
    )
    from rdflib_reasoning.middleware.tracing_notebook import NotebookTraceRenderer

    sink = TraceSink()
    run_id = uuid4()
    sink.append(
        TraceEvent(
            kind="chat_model_start", run_id=run_id, payload={"input_summary": ()}
        )
    )

    recorder = TraceRecorder(sink)
    recorder.on_tool_end(
        ToolMessage(
            content="label",
            artifact=TermInspectionResponse(
                uri="<http://www.w3.org/2000/01/rdf-schema#label>",
                label="label",
                definition="A human-readable name for the subject.",
                termType="property",
                vocabulary="<http://www.w3.org/2000/01/rdf-schema#>",
                domain=("<http://www.w3.org/2000/01/rdf-schema#Resource>",),
                range=("<http://www.w3.org/2000/01/rdf-schema#Literal>",),
            ),
            name="inspect_term",
            tool_call_id="call-1",
        ),
        run_id=uuid4(),
        parent_run_id=run_id,
    )

    renderer = NotebookTraceRenderer.__new__(NotebookTraceRenderer)
    renderer.sink = sink
    renderer.heading = "Trace"

    markdown = renderer._render_markdown(sink.snapshot())

    assert "### Tool: inspect_term" in markdown
    assert '"label": "label"' in markdown
    assert '"termType": "property"' in markdown
    assert "TermInspectionResponse(" not in markdown


def test_notebook_trace_renderer_shows_tool_rejection() -> None:
    pytest.importorskip("IPython")
    from rdflib_reasoning.middleware.tracing_notebook import NotebookTraceRenderer

    sink = TraceSink()
    run_id = uuid4()
    sink.append(
        TraceEvent(
            kind="chat_model_start", run_id=run_id, payload={"input_summary": ()}
        )
    )
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
