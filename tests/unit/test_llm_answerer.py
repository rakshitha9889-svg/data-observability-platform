import pytest

from assistant.llm.llm_question_answerer import (
    LLMAnswer,
    LLMQuestionAnswerer,
    build_runbook_query,
)
from assistant.llm.providers import get_provider_name
from assistant.models import EvidenceRecord, IncidentEvidenceBundle
from assistant.rag.embedder import to_pgvector
from assistant.rag.runbook_retriever import to_evidence
from assistant.rag.runbooks import load_runbook_chunks, split_sections

INCIDENT_EVIDENCE_ID = "observability.incidents:1"


class FakeModel:
    def __init__(self, answer: LLMAnswer) -> None:
        self.answer = answer
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return self.answer


@pytest.fixture
def bundle() -> IncidentEvidenceBundle:
    return IncidentEvidenceBundle(
        incident_id="1",
        incident=EvidenceRecord(
            evidence_id=INCIDENT_EVIDENCE_ID,
            source_table="observability.incidents",
            record={
                "incident_type": "data_quality",
                "affected_table": "raw.payments",
            },
        ),
    )


@pytest.fixture
def runbook_chunk() -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id="runbook:7",
        source_table="observability.runbook_chunks",
        record={"content": "negative_payment - Likely causes\nSign error"},
    )


def make_answer(citations: list[str]) -> LLMAnswer:
    return LLMAnswer(
        response_type="cause_or_hypothesis",
        answer="Hypothesis: a sign error produced a negative payment.",
        citations=citations,
        confidence="medium",
    )


def test_invented_citations_are_removed(bundle, runbook_chunk):
    model = FakeModel(
        make_answer([f"[{INCIDENT_EVIDENCE_ID}]", "runbook:7", "made_up:99"])
    )
    answerer = LLMQuestionAnswerer(
        structured_model=model,
        runbook_search=lambda query: [runbook_chunk],
    )

    response = answerer.answer("Why did this happen?", bundle)

    assert response.citations == [INCIDENT_EVIDENCE_ID, "runbook:7"]
    assert response.response_type == "cause_or_hypothesis"
    assert any("1 citation(s) removed" in n for n in response.limitations)


def test_prompt_contains_evidence_and_runbooks(bundle, runbook_chunk):
    model = FakeModel(make_answer([INCIDENT_EVIDENCE_ID]))
    answerer = LLMQuestionAnswerer(
        structured_model=model,
        runbook_search=lambda query: [runbook_chunk],
    )

    answerer.answer("Why?", bundle)

    system, human = model.messages
    assert system[0] == "system"
    assert INCIDENT_EVIDENCE_ID in human[1]
    assert "[runbook:7] negative_payment" in human[1]


def test_runbook_failure_still_answers(bundle):
    def broken_search(query):
        raise RuntimeError("table missing")

    answerer = LLMQuestionAnswerer(
        structured_model=FakeModel(make_answer([INCIDENT_EVIDENCE_ID])),
        runbook_search=broken_search,
    )

    response = answerer.answer("Why?", bundle)

    assert response.citations == [INCIDENT_EVIDENCE_ID]
    assert any("Runbook search unavailable" in n for n in response.limitations)


def test_runbook_query_adds_incident_context(bundle):
    query = build_runbook_query("Why?", bundle)

    assert query == "Why? data_quality raw.payments"


def test_split_sections_drops_todo_lines():
    markdown = (
        "# scenario\n\n"
        "## Symptoms\nOrders vanish.\nTODO: add more\n\n"
        "## Fix\nTODO: write this\n"
    )

    assert split_sections(markdown) == [("Symptoms", "Orders vanish.")]


def test_load_runbook_chunks_skips_readme(tmp_path):
    (tmp_path / "README.md").write_text("## Notes\nNot a runbook\n")
    (tmp_path / "negative_payment.md").write_text("## Fix\nRe-run batch\n")

    chunks = load_runbook_chunks(tmp_path)

    assert chunks == [
        {
            "scenario": "negative_payment",
            "source_file": "negative_payment.md",
            "heading": "Fix",
            "content": "negative_payment - Fix\nRe-run batch",
        }
    ]


def test_to_pgvector_formats_vector():
    assert to_pgvector([0.5, -0.25]) == "[0.500000,-0.250000]"


def test_to_evidence_builds_citable_record():
    record = to_evidence(
        {
            "chunk_id": 3,
            "scenario": "negative_payment",
            "heading": "Fix",
            "content": "Re-run batch",
            "similarity": 0.91234,
        }
    )

    assert record.evidence_id == "runbook:3"
    assert record.record["similarity"] == 0.912


def test_unknown_provider_is_rejected():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_provider_name("gpt")

    assert get_provider_name("Ollama") == "ollama"
