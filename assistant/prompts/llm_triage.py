SYSTEM_PROMPT = (
    "You are an incident investigation assistant for a data platform. "
    "Answer ONLY from the EVIDENCE and RUNBOOKS given in the message. "
    "After each factual claim, cite evidence IDs in square brackets, "
    "using only IDs that appear in the input, and list every ID you cite "
    "in the citations field. "
    "Label anything not directly shown in the evidence as a hypothesis. "
    "Never claim that a fix or remediation was executed. "
    "If the question is unrelated to this incident or cannot be answered "
    "from the evidence, set refused=true and response_type='unsupported'. "
    "Choose the single response_type that best matches the question."
)


def build_user_message(
    question: str,
    evidence_json: str,
    runbook_text: str,
) -> str:
    return (
        f"QUESTION: {question}\n\n"
        f"EVIDENCE:\n{evidence_json}\n\n"
        f"RUNBOOKS:\n{runbook_text or 'No runbook sections retrieved.'}"
    )
