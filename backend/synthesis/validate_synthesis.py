from pathlib import Path
import sys


REQUIRED_ANSWER_SECTIONS = [
    "## Answer",
    "## Evidence used",
    "## Uncertainty and gaps",
    "## Assumptions",
    "## Human review needed",
]

REQUIRED_REFUSAL_SECTIONS = [
    "## Refusal",
    "Reason:",
    "What a human should consult instead:",
]


def validate_answer(text):

    errors = []

    for section in REQUIRED_ANSWER_SECTIONS:
        if section not in text:
            errors.append(f"Missing section: {section}")

    if "## Refusal" in text:
        errors.append(
            "Answer output contains a Refusal section"
        )

    return errors


def validate_refusal(text):

    errors = []

    for section in REQUIRED_REFUSAL_SECTIONS:
        if section not in text:
            errors.append(
                f"Missing refusal part: {section}"
            )

    if "## Answer" in text:
        errors.append(
            "Refusal contains Answer section"
        )

    if "## Evidence used" in text:
        errors.append(
            "Refusal contains Evidence section"
        )

    return errors


def validate_synthesis(text):

    has_answer = "## Answer" in text
    has_refusal = "## Refusal" in text

    if has_answer and has_refusal:
        return (
            False,
            ["Output contains both Answer and Refusal"]
        )

    if has_answer:
        errors = validate_answer(text)
        return len(errors) == 0, errors

    if has_refusal:
        errors = validate_refusal(text)
        return len(errors) == 0, errors

    return (
        False,
        ["Output contains neither Answer nor Refusal"]
    )


def main():

    if len(sys.argv) != 2:
        print(
            "Usage: python3 validate_synthesis.py <file.md>"
        )
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    text = path.read_text()

    valid, errors = validate_synthesis(text)

    print("\n--- SYNTHESIS VALIDATION ---")

    if valid:
        print("✓ VALID SYNTHESIS OUTPUT")
        sys.exit(0)

    print("✗ INVALID SYNTHESIS OUTPUT")

    for error in errors:
        print(f"- {error}")

    sys.exit(1)


if __name__ == "__main__":
    main()
