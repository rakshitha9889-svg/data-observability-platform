import argparse
import json

from assistant.retrieval.evidence_retriever import (
    IncidentEvidenceRetriever,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an evidence bundle for an incident.",
    )

    parser.add_argument(
        "incident_id",
        help="UUID of the incident to investigate.",
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    retriever = IncidentEvidenceRetriever()

    evidence_bundle = retriever.build_evidence_bundle(arguments.incident_id)

    print(
        json.dumps(
            evidence_bundle.model_dump(),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
