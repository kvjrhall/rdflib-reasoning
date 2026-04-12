from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD
from rdflib_reasoning.middleware import (
    DatasetMiddleware,
    DatasetMiddlewareConfig,
    DatasetRuntime,
    RunTermTelemetry,
    VocabularyConfiguration,
    VocabularyContext,
    VocabularyDeclaration,
)
from rdflib_reasoning.middleware._message_heuristics import has_recent_guard_reminder
from rdflib_reasoning.middleware.dataset_middleware import (
    ADD_TRIPLES_TOOL_DESCRIPTION,
    DATASET_SYSTEM_PROMPT,
    REMOVE_TRIPLES_TOOL_DESCRIPTION,
    SERIALIZE_DATASET_TOOL_DESCRIPTION,
    WhitelistViolation,
    _format_whitelist_violation_message,
)
from rdflib_reasoning.middleware.dataset_model import SerializationResponse
from rdflib_reasoning.middleware.namespaces.spec_whitelist import (
    RestrictedNamespaceWhitelist,
    WhitelistEntry,
)

EX = "urn:test:"
EX_NS = Namespace(EX)


def _default_vocabulary_context() -> VocabularyContext:
    return VocabularyConfiguration.bundled_plus(
        VocabularyDeclaration(prefix="ex", namespace=EX_NS)
    ).build_context()


def _restricted_vocabulary_context() -> VocabularyContext:
    return VocabularyConfiguration(
        declarations=(
            VocabularyDeclaration(prefix="ex", namespace=EX_NS),
            VocabularyDeclaration(prefix="owl", namespace=OWL),
            VocabularyDeclaration(prefix="rdf", namespace=RDF),
            VocabularyDeclaration(prefix="rdfs", namespace=RDFS),
            VocabularyDeclaration(prefix="xsd", namespace=XSD),
        )
    ).build_context()


def _dataset_middleware() -> DatasetMiddleware:
    return DatasetMiddleware(
        DatasetMiddlewareConfig(vocabulary_context=_default_vocabulary_context())
    )


def _core_whitelist() -> RestrictedNamespaceWhitelist:
    return RestrictedNamespaceWhitelist(
        (
            WhitelistEntry(prefix="owl", namespace=OWL),
            WhitelistEntry(prefix="rdf", namespace=RDF),
            WhitelistEntry(prefix="rdfs", namespace=RDFS),
            WhitelistEntry(prefix="xsd", namespace=XSD),
        )
    )


def test_default_graph_starts_empty() -> None:
    middleware = _dataset_middleware()

    assert middleware.list_triples() == ()


def test_default_graph_triple_crud() -> None:
    middleware = _dataset_middleware()
    triple = (URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))

    add_response = middleware.add_triples([triple])

    assert add_response.requested == 1
    assert add_response.updated == 1
    assert add_response.unchanged == 0
    assert add_response.no_action_needed is False
    assert middleware.list_triples() == (triple,)

    remove_response = middleware.remove_triples([triple])

    assert remove_response.updated == 1
    assert middleware.list_triples() == ()


def test_serialize_default_graph() -> None:
    middleware = _dataset_middleware()
    triple = (URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("default"))

    middleware.add_triples([triple])

    output = middleware.serialize(format="turtle")

    assert "default" in output


def test_serialize_dataset_tool_reports_empty_default_graph_explicitly() -> None:
    middleware = _dataset_middleware()
    tools = {tool.name: tool for tool in middleware.tools}

    response = tools["serialize_dataset"].invoke({"format": "turtle"})

    assert response.default_graph_triple_count == 0
    assert response.is_empty is True
    assert response.message is not None
    assert "Changing serialization formats will not add data" in response.message


def test_serialize_dataset_tool_reports_nonempty_default_graph_count() -> None:
    middleware = _dataset_middleware()
    middleware.add_triples([(URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))])
    tools = {tool.name: tool for tool in middleware.tools}

    response = tools["serialize_dataset"].invoke({"format": "turtle"})

    assert response.default_graph_triple_count == 1
    assert response.is_empty is False
    assert (
        response.message == "Serialized the current default graph containing 1 triples."
    )


def test_reset_dataset_replaces_existing_dataset() -> None:
    middleware = _dataset_middleware()
    middleware.add_triples([(URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))])

    response = middleware.reset_dataset()

    assert response.updated == 1
    assert middleware.list_triples() == ()


def test_dataset_middleware_uses_injected_runtime() -> None:
    runtime = DatasetRuntime()
    first = DatasetMiddleware(
        DatasetMiddlewareConfig(
            vocabulary_context=_default_vocabulary_context(),
            runtime=runtime,
        )
    )
    second = DatasetMiddleware(
        DatasetMiddlewareConfig(
            vocabulary_context=_default_vocabulary_context(),
            runtime=runtime,
        )
    )
    triple = (URIRef(f"{EX}s"), RDF.type, RDFS.Class)

    first.add_triples([triple])

    assert second.list_triples() == (triple,)


def test_add_triples_records_asserted_term_usage_in_telemetry() -> None:
    telemetry = RunTermTelemetry()
    middleware = DatasetMiddleware(
        DatasetMiddlewareConfig(
            vocabulary_context=_default_vocabulary_context(),
            run_term_telemetry=telemetry,
        )
    )
    triple = (URIRef(f"{EX}s"), RDF.type, RDFS.Class)

    middleware.add_triples([triple])
    middleware.add_triples([triple])

    assert telemetry.asserted_term_count(triple[0]) == 1
    assert telemetry.asserted_term_count(triple[1]) == 1
    assert telemetry.asserted_term_count(triple[2]) == 1


def test_add_triples_reports_no_action_needed_for_exact_repeat() -> None:
    middleware = _dataset_middleware()
    triples = (
        (URIRef(f"{EX}john"), RDF.type, URIRef(f"{EX}Person")),
        (URIRef(f"{EX}Person"), RDFS.subClassOf, URIRef(f"{EX}Human")),
    )

    middleware.add_triples(triples)
    response = middleware.add_triples(triples)

    assert response.requested == 2
    assert response.updated == 0
    assert response.unchanged == 2
    assert response.no_action_needed is True
    assert "already present" in response.message
    assert "Do not retry" in response.message


def test_dataset_system_prompt_gives_rejection_specific_add_triples_guidance() -> None:
    assert (
        "If you encounter tool rejection for `add_triples`, you SHOULD partition"
        not in DATASET_SYSTEM_PROMPT
    )
    assert (
        "If an `add_triples` call fails validation, you SHOULD correct the invalid "
        "triple or triples before retrying."
    ) in DATASET_SYSTEM_PROMPT
    assert (
        "you MUST NOT submit any of those same triples again in this run"
    ) in DATASET_SYSTEM_PROMPT
    assert (
        "whether in the same batch, a reordered batch, or a smaller subset."
    ) in DATASET_SYSTEM_PROMPT
    assert (
        "you SHOULD follow the remediation advice in the tool response rather than "
        "retrying automatically."
    ) in DATASET_SYSTEM_PROMPT


def test_add_triples_tool_description_explains_no_action_needed_recovery() -> None:
    assert (
        "you MUST NOT submit any of those same triples again in this run"
    ) in ADD_TRIPLES_TOOL_DESCRIPTION
    assert (
        "whether in the same batch, a reordered batch, or a smaller subset."
    ) in ADD_TRIPLES_TOOL_DESCRIPTION
    assert (
        "you SHOULD continue with different triples that are"
    ) in ADD_TRIPLES_TOOL_DESCRIPTION


def test_dataset_system_prompt_gives_remove_triples_noop_recovery_guidance() -> None:
    assert (
        "If a `remove_triples` response sets `no_action_needed=true`, you MUST NOT "
        "submit any of those same triples again in this run,"
    ) in DATASET_SYSTEM_PROMPT
    assert (
        "you SHOULD continue with a different specific dataset change, inspect the "
        "dataset once if you are unsure whether the correction is already reflected,"
    ) in DATASET_SYSTEM_PROMPT


def test_remove_triples_tool_description_explains_no_action_needed_recovery() -> None:
    assert (
        "Literal text MUST be encoded as RDF literals"
        in REMOVE_TRIPLES_TOOL_DESCRIPTION
    )
    assert (
        "you MUST NOT submit any of those same triples again in this run"
    ) in REMOVE_TRIPLES_TOOL_DESCRIPTION
    assert (
        "you SHOULD continue with a different specific dataset"
    ) in REMOVE_TRIPLES_TOOL_DESCRIPTION


def test_dataset_system_prompt_gives_strong_serialize_stop_branch() -> None:
    assert (
        "changing serialization formats cannot improve an unchanged dataset"
    ) in DATASET_SYSTEM_PROMPT
    assert (
        "If a `serialize_dataset` response sets `is_empty=true`, the default graph is empty"
    ) in DATASET_SYSTEM_PROMPT
    assert (
        "you MUST NOT call `serialize_dataset` again until you have changed the dataset."
    ) in DATASET_SYSTEM_PROMPT
    assert (
        "you MUST either return your final answer immediately or make one or more "
        "specific dataset changes before using `serialize_dataset` again."
    ) in DATASET_SYSTEM_PROMPT


def test_dataset_system_prompt_includes_local_name_style_guidance_for_minted_iris() -> (
    None
):
    assert (
        "the local name SHOULD be singular and use `PascalCase`"
        in DATASET_SYSTEM_PROMPT
    )
    assert (
        "for example `ProjectReport`, `FieldObservation`, or `QualityRating`"
        in DATASET_SYSTEM_PROMPT
    )
    assert "the local name SHOULD use `camelCase`" in DATASET_SYSTEM_PROMPT
    assert (
        "for example `hasInventoryCode`, `recordedAtFacility`, or `reviewStatus`"
        in DATASET_SYSTEM_PROMPT
    )


def test_serialize_tool_description_explains_post_rejection_next_step() -> None:
    assert (
        "Changing serialization formats cannot improve an unchanged dataset"
    ) in SERIALIZE_DATASET_TOOL_DESCRIPTION
    assert (
        "If the response sets `is_empty=true`, the default graph is empty"
    ) in SERIALIZE_DATASET_TOOL_DESCRIPTION
    assert (
        "you MUST NOT call `serialize_dataset` again until"
    ) in SERIALIZE_DATASET_TOOL_DESCRIPTION
    assert (
        "you MUST either return your final answer immediately or"
    ) in SERIALIZE_DATASET_TOOL_DESCRIPTION


def test_wrap_tool_call_rejects_immediate_identical_retry_after_noop() -> None:
    middleware = _dataset_middleware()
    request = SimpleNamespace(
        tool=None,
        tool_call={
            "name": "add_triples",
            "id": "call-2",
            "args": {
                "triples": [
                    {
                        "subject": "<urn:test:s>",
                        "predicate": "<urn:test:p>",
                        "object": '"o"',
                    }
                ]
            },
        },
    )

    middleware._last_add_triples_noop_signature = middleware._tool_call_signature(
        request
    )

    result = middleware.wrap_tool_call(request, lambda _: None)

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "already satisfied" in str(result.content)


def test_wrap_tool_call_rejects_immediate_identical_retry_after_remove_noop() -> None:
    middleware = _dataset_middleware()
    request = SimpleNamespace(
        tool=None,
        tool_call={
            "name": "remove_triples",
            "id": "call-remove",
            "args": {
                "triples": [
                    {
                        "subject": "<urn:test:s>",
                        "predicate": "<urn:test:p>",
                        "object": '"o"',
                    }
                ]
            },
        },
    )

    middleware._last_remove_triples_noop_signature = middleware._tool_call_signature(
        request
    )

    result = middleware.wrap_tool_call(request, lambda _: None)

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "already satisfied" in str(result.content)


def test_wrap_tool_call_rejects_identical_retry_after_noop_for_json_string_args() -> (
    None
):
    middleware = _dataset_middleware()
    previous_request = SimpleNamespace(
        tool=None,
        tool_call={
            "name": "add_triples",
            "id": "call-previous",
            "args": '{"triples":[{"subject":"<urn:test:s>","predicate":"<urn:test:p>","object":"\\"o\\""}]}',
        },
    )
    current_request = SimpleNamespace(
        tool=None,
        tool_call={
            "name": "add_triples",
            "id": "call-current",
            "args": '{\n  "triples": [\n    {\n      "subject": "<urn:test:s>",\n      "predicate": "<urn:test:p>",\n      "object": "\\"o\\""\n    }\n  ]\n}',
        },
    )

    middleware._last_add_triples_noop_signature = middleware._tool_call_signature(
        previous_request
    )

    result = middleware.wrap_tool_call(current_request, lambda _: None)

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "already satisfied" in str(result.content)


def test_wrap_tool_call_rejects_repeated_serialize_when_dataset_unchanged() -> None:
    middleware = _dataset_middleware()
    middleware.add_triples([(URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))])
    request = SimpleNamespace(
        tool=None,
        state={"continuation_mode": "normal"},
        tool_call={
            "name": "serialize_dataset",
            "id": "call-serialize",
            "args": {"format": "turtle"},
        },
    )

    first_result = middleware.wrap_tool_call(
        request,
        lambda _: SerializationResponse(
            format="turtle",
            content=middleware.serialize(format="turtle"),
            default_graph_triple_count=1,
            is_empty=False,
            message="Serialized the current default graph containing 1 triples.",
        ),
    )

    assert isinstance(first_result, SerializationResponse)

    second_result = middleware.wrap_tool_call(request, lambda _: None)

    assert isinstance(second_result, Command)
    assert second_result.update["continuation_mode"] == "finalize_only"
    tool_message = second_result.update["messages"][0]
    assert isinstance(tool_message, ToolMessage)
    assert tool_message.status == "error"
    content = str(tool_message.content)
    assert "Re-serializing will not reformat or improve the graph" in content
    assert "Use the previous successful serialization as your final answer" in content
    assert (
        "Do not call `serialize_dataset` again until you have changed the dataset"
        in content
    )
    assert "Return your final answer now" in content


def test_wrap_tool_call_rejects_any_serialize_in_finalize_only_mode() -> None:
    middleware = _dataset_middleware()
    middleware.add_triples([(URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))])
    request = SimpleNamespace(
        tool=None,
        state={"continuation_mode": "finalize_only"},
        tool_call={
            "name": "serialize_dataset",
            "id": "call-serialize",
            "args": {"format": "trig"},
        },
    )

    result = middleware.wrap_tool_call(request, lambda _: None)

    assert isinstance(result, Command)
    assert "continuation_mode" not in result.update
    tool_message = result.update["messages"][0]
    assert isinstance(tool_message, ToolMessage)
    assert tool_message.status == "error"
    content = str(tool_message.content)
    assert (
        "changing serialization formats will not add data or improve the graph"
        in content
    )
    assert "Do not call `serialize_dataset` again" in content


def test_finalize_only_state_persists_across_repeated_serialize_rejection_until_dataset_changes() -> (
    None
):
    middleware = _dataset_middleware()
    triple = (URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))
    middleware.add_triples([triple])
    serialize_request = SimpleNamespace(
        tool=None,
        state={"continuation_mode": "normal"},
        tool_call={
            "name": "serialize_dataset",
            "id": "call-serialize",
            "args": {"format": "turtle"},
        },
    )

    first_result = middleware.wrap_tool_call(
        serialize_request,
        lambda _: SerializationResponse(
            format="turtle",
            content=middleware.serialize(format="turtle"),
            default_graph_triple_count=1,
            is_empty=False,
            message="Serialized the current default graph containing 1 triples.",
        ),
    )

    assert isinstance(first_result, SerializationResponse)

    repeated_result = middleware.wrap_tool_call(serialize_request, lambda _: None)

    assert isinstance(repeated_result, Command)
    repeated_state = repeated_result.update
    assert repeated_state["continuation_mode"] == "finalize_only"

    blocked_request = SimpleNamespace(
        tool=None,
        state=repeated_state,
        tool_call={
            "name": "serialize_dataset",
            "id": "call-serialize-again",
            "args": {"format": "trig"},
        },
    )

    blocked_result = middleware.wrap_tool_call(blocked_request, lambda _: None)

    assert isinstance(blocked_result, Command)
    assert "continuation_mode" not in blocked_result.update
    blocked_message = blocked_result.update["messages"][0]
    assert isinstance(blocked_message, ToolMessage)
    assert blocked_message.status == "error"
    assert "already in final-answer-only mode" in str(blocked_message.content)

    add_request = SimpleNamespace(
        tool=None,
        state={"continuation_mode": "finalize_only", **blocked_result.update},
        tool_call={
            "name": "add_triples",
            "id": "call-add",
            "args": {
                "triples": [
                    {
                        "subject": "<urn:test:s2>",
                        "predicate": "<urn:test:p>",
                        "object": '"o2"',
                    }
                ]
            },
        },
    )

    def add_handler(_: SimpleNamespace) -> ToolMessage:
        middleware.add_triples([(URIRef(f"{EX}s2"), URIRef(f"{EX}p"), Literal("o2"))])
        return ToolMessage(
            content="requested=1 updated=1 unchanged=0 no_action_needed=False message='1 of 1 triples added.'",
            name="add_triples",
            tool_call_id="call-add",
            status="success",
        )

    add_result = middleware.wrap_tool_call(add_request, add_handler)

    assert isinstance(add_result, Command)
    assert add_result.update["continuation_mode"] == "normal"


def test_wrap_tool_call_rejects_repeated_serialize_when_runtime_returns_tool_message() -> (
    None
):
    middleware = _dataset_middleware()
    middleware.add_triples([(URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))])
    request = SimpleNamespace(
        tool=None,
        state={"continuation_mode": "normal"},
        tool_call={
            "name": "serialize_dataset",
            "id": "call-serialize",
            "args": {"format": "turtle"},
        },
    )

    first_result = middleware.wrap_tool_call(
        request,
        lambda _: ToolMessage(
            content="format='turtle' content='@prefix ns1: <urn:test:> .'",
            name="serialize_dataset",
            tool_call_id="call-serialize",
            status="success",
        ),
    )

    assert isinstance(first_result, ToolMessage)
    assert first_result.status == "success"

    second_result = middleware.wrap_tool_call(request, lambda _: None)

    assert isinstance(second_result, Command)
    assert second_result.update["continuation_mode"] == "finalize_only"
    tool_message = second_result.update["messages"][0]
    assert isinstance(tool_message, ToolMessage)
    assert tool_message.status == "error"
    content = str(tool_message.content)
    assert "Re-serializing will not reformat or improve the graph" in content
    assert "Use the previous successful serialization as your final answer" in content
    assert (
        "Do not call `serialize_dataset` again until you have changed the dataset"
        in content
    )
    assert "Return your final answer now" in content


def test_wrap_tool_call_rejects_identical_retry_after_runtime_noop_add_triples() -> (
    None
):
    middleware = _dataset_middleware()
    request = SimpleNamespace(
        tool=None,
        state={"continuation_mode": "normal"},
        tool_call={
            "name": "add_triples",
            "id": "call-add",
            "args": {
                "triples": [
                    {
                        "subject": "<urn:test:s>",
                        "predicate": "<urn:test:p>",
                        "object": '"o"',
                    }
                ]
            },
        },
    )

    middleware.add_triples([(URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))])
    first_result = middleware.wrap_tool_call(
        request,
        lambda _: ToolMessage(
            content=(
                "requested=1 updated=0 unchanged=1 no_action_needed=True "
                "message='No action was needed. All 1 requested triples were already "
                "present in the default graph. Do not retry this same `add_triples` "
                "call unless you change the triples.'"
            ),
            name="add_triples",
            tool_call_id="call-add",
            status="success",
        ),
    )

    assert isinstance(first_result, ToolMessage)
    assert first_result.status == "success"

    second_result = middleware.wrap_tool_call(request, lambda _: None)

    assert isinstance(second_result, ToolMessage)
    assert second_result.status == "error"
    assert "already satisfied" in str(second_result.content)


def test_remove_triples_reports_no_action_needed_for_exact_repeat() -> None:
    middleware = _dataset_middleware()
    triple = (URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))

    middleware.add_triples([triple])
    middleware.remove_triples([triple])
    response = middleware.remove_triples([triple])

    assert response.requested == 1
    assert response.updated == 0
    assert response.unchanged == 1
    assert response.no_action_needed is True
    assert "already absent" in response.message
    assert "Do not retry" in response.message


def test_wrap_tool_call_resets_finalize_only_mode_after_successful_add_triples_change() -> (
    None
):
    middleware = _dataset_middleware()
    triple = (URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))
    request = SimpleNamespace(
        tool=None,
        state={"continuation_mode": "finalize_only"},
        tool_call={
            "name": "add_triples",
            "id": "call-add",
            "args": {
                "triples": [
                    {
                        "subject": "<urn:test:s>",
                        "predicate": "<urn:test:p>",
                        "object": '"o"',
                    }
                ]
            },
        },
    )

    def handler(_: SimpleNamespace) -> ToolMessage:
        middleware.add_triples([triple])
        return ToolMessage(
            content="requested=1 updated=1 unchanged=0 no_action_needed=False message='1 of 1 triples added.'",
            name="add_triples",
            tool_call_id="call-add",
            status="success",
        )

    result = middleware.wrap_tool_call(
        request,
        handler,
    )

    assert isinstance(result, Command)
    assert result.update["continuation_mode"] == "normal"
    tool_message = result.update["messages"][0]
    assert isinstance(tool_message, ToolMessage)
    assert tool_message.status == "success"


def test_wrap_tool_call_rejects_identical_retry_after_runtime_noop_remove_triples() -> (
    None
):
    middleware = _dataset_middleware()
    request = SimpleNamespace(
        tool=None,
        state={"continuation_mode": "normal"},
        tool_call={
            "name": "remove_triples",
            "id": "call-remove",
            "args": {
                "triples": [
                    {
                        "subject": "<urn:test:s>",
                        "predicate": "<urn:test:p>",
                        "object": '"o"',
                    }
                ]
            },
        },
    )

    first_result = middleware.wrap_tool_call(
        request,
        lambda _: ToolMessage(
            content=(
                "requested=1 updated=0 unchanged=1 no_action_needed=True "
                "message='No action was needed. All 1 requested triples were already "
                "absent from the default graph. Do not retry this same "
                "`remove_triples` call unless you change the triples.'"
            ),
            name="remove_triples",
            tool_call_id="call-remove",
            status="success",
        ),
    )

    assert isinstance(first_result, ToolMessage)
    assert first_result.status == "success"

    second_result = middleware.wrap_tool_call(request, lambda _: None)

    assert isinstance(second_result, ToolMessage)
    assert second_result.status == "error"
    assert "already satisfied" in str(second_result.content)


def test_wrap_tool_call_clears_remove_noop_guard_after_add_change() -> None:
    middleware = _dataset_middleware()
    remove_request = SimpleNamespace(
        tool=None,
        state={"continuation_mode": "normal"},
        tool_call={
            "name": "remove_triples",
            "id": "call-remove",
            "args": {
                "triples": [
                    {
                        "subject": "<urn:test:s>",
                        "predicate": "<urn:test:p>",
                        "object": '"o"',
                    }
                ]
            },
        },
    )
    add_request = SimpleNamespace(
        tool=None,
        state={"continuation_mode": "normal"},
        tool_call={
            "name": "add_triples",
            "id": "call-add",
            "args": {
                "triples": [
                    {
                        "subject": "<urn:test:s>",
                        "predicate": "<urn:test:p>",
                        "object": '"o"',
                    }
                ]
            },
        },
    )

    noop_remove = middleware.wrap_tool_call(
        remove_request,
        lambda _: ToolMessage(
            content=(
                "requested=1 updated=0 unchanged=1 no_action_needed=True "
                "message='No action was needed. All 1 requested triples were already "
                "absent from the default graph. Do not retry this same "
                "`remove_triples` call unless you change the triples.'"
            ),
            name="remove_triples",
            tool_call_id="call-remove",
            status="success",
        ),
    )

    assert isinstance(noop_remove, ToolMessage)
    assert noop_remove.status == "success"

    def add_handler(_: SimpleNamespace) -> ToolMessage:
        middleware.add_triples([(URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))])
        return ToolMessage(
            content="requested=1 updated=1 unchanged=0 no_action_needed=False message='1 of 1 triples added.'",
            name="add_triples",
            tool_call_id="call-add",
            status="success",
        )

    added = middleware.wrap_tool_call(add_request, add_handler)

    assert isinstance(added, ToolMessage)
    assert added.status == "success"

    def remove_handler(_: SimpleNamespace) -> ToolMessage:
        middleware.remove_triples([(URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))])
        return ToolMessage(
            content="requested=1 updated=1 unchanged=0 no_action_needed=False message='Triples removed from the default graph.'",
            name="remove_triples",
            tool_call_id="call-remove",
            status="success",
        )

    allowed_remove = middleware.wrap_tool_call(remove_request, remove_handler)

    assert isinstance(allowed_remove, ToolMessage)
    assert allowed_remove.status == "success"


def test_wrap_tool_call_resets_finalize_only_mode_after_successful_remove_triples_change() -> (
    None
):
    middleware = _dataset_middleware()
    triple = (URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))
    middleware.add_triples([triple])
    request = SimpleNamespace(
        tool=None,
        state={"continuation_mode": "finalize_only"},
        tool_call={
            "name": "remove_triples",
            "id": "call-remove",
            "args": {
                "triples": [
                    {
                        "subject": "<urn:test:s>",
                        "predicate": "<urn:test:p>",
                        "object": '"o"',
                    }
                ]
            },
        },
    )

    def handler(_: SimpleNamespace) -> ToolMessage:
        middleware.remove_triples([triple])
        return ToolMessage(
            content="requested=1 updated=1 unchanged=0 no_action_needed=False message='Triples removed from the default graph.'",
            name="remove_triples",
            tool_call_id="call-remove",
            status="success",
        )

    result = middleware.wrap_tool_call(
        request,
        handler,
    )

    assert isinstance(result, Command)
    assert result.update["continuation_mode"] == "normal"
    tool_message = result.update["messages"][0]
    assert isinstance(tool_message, ToolMessage)
    assert tool_message.status == "success"


def test_after_model_reprompts_when_dataset_is_empty_and_response_is_not_final() -> (
    None
):
    middleware = _dataset_middleware()
    state = {"messages": [AIMessage(content="The dataset is ready to present.")]}

    result = middleware.after_model(state, runtime=None)

    assert isinstance(result, Command)
    assert result.goto == "model"
    reminder = result.update["messages"][0]
    assert isinstance(reminder, HumanMessage)
    assert "dataset is still empty" in str(reminder.content)


def test_after_model_defers_planning_like_output_to_continuation_guard(
    caplog: pytest.LogCaptureFixture,
) -> None:
    middleware = _dataset_middleware()
    state = {"messages": [AIMessage(content="I will now construct the RDF graph.")]}

    result = middleware.after_model(state, runtime=None)

    assert result is None
    assert (
        "Deferring empty-dataset reminder because the latest AI output looks like unfinished continuation content"
        in caplog.text
    )


def test_after_model_defers_when_another_guard_already_reprompted_latest_ai_turn(
    caplog: pytest.LogCaptureFixture,
) -> None:
    middleware = _dataset_middleware()
    state = {
        "messages": [
            HumanMessage(
                content=(
                    "[rdflib_reasoning-continuation] Do not stop at an unfinished plan."
                )
            ),
            AIMessage(content="The dataset is ready to present."),
        ]
    }

    result = middleware.after_model(state, runtime=None)

    assert result is None
    assert (
        "Deferring empty-dataset reminder because another recovery-oriented middleware already injected a reminder"
        in caplog.text
    )
    assert "overlapping_reminder_prefix=[rdflib_reasoning-continuation]" in caplog.text


def test_after_model_does_not_reprompt_for_completed_empty_turtle_answer_on_empty_dataset() -> (
    None
):
    middleware = _dataset_middleware()
    state = {
        "messages": [
            AIMessage(
                content="```text/turtle\n@prefix ex: <urn:ex:> .\n# empty graph\n```"
            )
        ]
    }

    result = middleware.after_model(state, runtime=None)

    assert result is None


def test_after_model_reprompts_for_completed_nonempty_turtle_answer_on_empty_dataset() -> (
    None
):
    middleware = _dataset_middleware()
    state = {
        "messages": [
            AIMessage(
                content="```text/turtle\n@prefix ex: <urn:ex:> .\nex:John a ex:Person .\n```"
            )
        ]
    }

    result = middleware.after_model(state, runtime=None)

    assert isinstance(result, Command)
    assert result.goto == "model"


def test_after_model_does_not_reprompt_when_tool_calls_are_present() -> None:
    middleware = _dataset_middleware()
    state = {
        "messages": [
            AIMessage(
                content="I will add the first triples now.",
                tool_calls=[
                    {
                        "name": "add_triples",
                        "args": {"triples": []},
                        "id": "tool-1",
                        "type": "tool_call",
                    }
                ],
            )
        ]
    }

    result = middleware.after_model(state, runtime=None)

    assert result is None


def test_after_model_only_injects_dataset_reminder_once() -> None:
    middleware = _dataset_middleware()
    state = {
        "messages": [
            HumanMessage(
                content=(
                    "[rdflib_reasoning-dataset] The dataset is still empty. If this "
                    "task requires grounded RDF extraction, emit the needed dataset "
                    "tool call now."
                )
            ),
            AIMessage(content="I will now construct the RDF graph."),
        ]
    }

    result = middleware.after_model(state, runtime=None)

    assert result is None


def test_after_model_does_not_reprompt_when_dataset_is_not_empty() -> None:
    middleware = _dataset_middleware()
    middleware.add_triples([(URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))])
    state = {"messages": [AIMessage(content="I will now continue building the graph.")]}

    result = middleware.after_model(state, runtime=None)

    assert result is None


def test_has_recent_guard_reminder_detects_prefix_before_latest_ai_message() -> None:
    messages = [
        HumanMessage(content="[rdflib_reasoning-dataset] Reminder."),
        AIMessage(content="I will continue."),
    ]

    assert has_recent_guard_reminder(messages, "[rdflib_reasoning-dataset]") is True


# =============================================================================
# Whitelist enforcement tests
# =============================================================================


EX_NS = Namespace("urn:test:")


class TestWhitelistEnforcement:
    """Tests for namespace whitelist integration in DatasetMiddleware."""

    @pytest.fixture()
    def restricted_middleware(self) -> DatasetMiddleware:
        """Middleware with explicit core vocabularies plus open urn:test: namespace.

        The open namespace allows minted subject IRIs to pass while closed
        vocabulary enforcement still applies to predicates and objects.
        """
        config = DatasetMiddlewareConfig(
            vocabulary_context=_restricted_vocabulary_context()
        )
        return DatasetMiddleware(config)

    def test_declared_context_allows_bundled_and_local_terms(self) -> None:
        middleware = _dataset_middleware()
        triple = (URIRef("urn:test:s"), RDF.type, RDFS.Class)

        response = middleware.add_triples([triple])

        assert response.updated == 1
        assert middleware.list_triples() == (triple,)

    def test_allowed_closed_term_passes(
        self, restricted_middleware: DatasetMiddleware
    ) -> None:
        triple = (URIRef("urn:test:s"), RDF.type, RDFS.Class)

        response = restricted_middleware.add_triples([triple])

        assert response.updated == 1
        assert restricted_middleware.list_triples() == (triple,)

    def test_rejected_unknown_namespace(
        self, restricted_middleware: DatasetMiddleware
    ) -> None:
        bad_uri = URIRef("http://totally-unknown.example/foo")
        triple = (bad_uri, RDF.type, RDFS.Class)

        with pytest.raises(WhitelistViolation) as exc_info:
            restricted_middleware.add_triples([triple])

        assert exc_info.value.bad_term == bad_uri
        assert exc_info.value.result.allowed is False
        assert exc_info.value.result.nearest_matches == []

    def test_rejected_near_miss_has_remediation(
        self, restricted_middleware: DatasetMiddleware
    ) -> None:
        bad_uri = URIRef("http://www.w3.org/2000/01/rdf-schema#Classs")
        triple = (URIRef("urn:test:s"), RDF.type, bad_uri)

        with pytest.raises(WhitelistViolation) as exc_info:
            restricted_middleware.add_triples([triple])

        result = exc_info.value.result
        assert result.allowed is False
        assert len(result.nearest_matches) >= 1
        top_qname = result.nearest_matches[0][0].qname
        assert top_qname == "rdfs:Class"

    def test_triple_not_added_on_violation(
        self, restricted_middleware: DatasetMiddleware
    ) -> None:
        bad_uri = URIRef("http://totally-unknown.example/foo")
        triple = (bad_uri, RDF.type, RDFS.Class)

        with pytest.raises(WhitelistViolation):
            restricted_middleware.add_triples([triple])

        assert restricted_middleware.list_triples() == ()

    def test_confirmed_terms_are_cached(
        self, restricted_middleware: DatasetMiddleware
    ) -> None:
        triple = (URIRef("urn:test:s"), RDF.type, RDFS.Class)

        restricted_middleware.add_triples([triple])

        assert RDF.type in restricted_middleware._whitelist_confirmed
        assert RDFS.Class in restricted_middleware._whitelist_confirmed

    def test_open_vocab_prefix_accepted(self) -> None:
        ex = Namespace("http://example.org/voc#")
        vocabulary_context = VocabularyConfiguration(
            declarations=(
                VocabularyDeclaration(prefix="ex", namespace=ex),
                VocabularyDeclaration(prefix="owl", namespace=OWL),
                VocabularyDeclaration(prefix="rdf", namespace=RDF),
                VocabularyDeclaration(prefix="rdfs", namespace=RDFS),
                VocabularyDeclaration(prefix="xsd", namespace=XSD),
            )
        ).build_context()
        config = DatasetMiddlewareConfig(vocabulary_context=vocabulary_context)
        middleware = DatasetMiddleware(config)
        triple = (URIRef("http://example.org/voc#AnyThing"), RDF.type, RDFS.Class)

        response = middleware.add_triples([triple])

        assert response.updated == 1

    def test_literal_objects_are_not_checked(
        self, restricted_middleware: DatasetMiddleware
    ) -> None:
        """Literals are not URIRefs and should never trigger whitelist checks."""
        triple = (URIRef("urn:test:s"), RDFS.label, Literal("hello"))

        response = restricted_middleware.add_triples([triple])

        assert response.updated == 1

    def test_violation_exception_message_contains_uri(
        self, restricted_middleware: DatasetMiddleware
    ) -> None:
        bad_uri = URIRef("http://totally-unknown.example/foo")
        triple = (bad_uri, RDF.type, RDFS.Class)

        with pytest.raises(
            WhitelistViolation, match="http://totally-unknown.example/foo"
        ):
            restricted_middleware.add_triples([triple])

    def test_build_system_prompt_includes_enumeration(
        self, restricted_middleware: DatasetMiddleware
    ) -> None:
        prompt = restricted_middleware._build_system_prompt()
        assert "### Allowed Vocabularies" in prompt
        assert "rdf:" in prompt
        assert "rdfs:" in prompt

    def test_build_system_prompt_uses_context_enumeration(self) -> None:
        middleware = _dataset_middleware()
        prompt = middleware._build_system_prompt()
        assert "### Allowed Vocabularies" in prompt
        assert "foaf:" in prompt
        assert "prov:" in prompt


class TestFormatWhitelistViolationMessage:
    def test_includes_markdown_table_with_qname_iri_distance(self) -> None:
        bad = URIRef("http://www.w3.org/2000/01/rdf-schema#type")
        wl = _core_whitelist()
        result = wl.find_term(bad)
        msg = _format_whitelist_violation_message(bad, result)
        assert "| Qualified name | IRI | Levenshtein distance |" in msg
        assert "`rdf:type`" in msg
        assert f"`{RDF.type}`" in msg
        assert '"allowed"' not in msg
        assert '"nearest_matches"' not in msg
        assert "vocabulary_type" not in msg
        assert (
            "If none of the suggestions fit your intent, you MUST use a different term"
            in msg
        )

    def test_no_matches_branch(self) -> None:
        bad = URIRef("http://totally-unknown.example/term")
        wl = _core_whitelist()
        result = wl.find_term(bad)
        msg = _format_whitelist_violation_message(bad, result)
        assert "No close matches were found" in msg
        assert "| Qualified name | IRI | Levenshtein distance |" not in msg
