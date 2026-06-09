from pathlib import Path

answer = Path("test_response.md").read_text()

print(answer)

print("\n--- CHECKS ---")

if "## Evidence used" in answer:
    print("✓ Evidence table present")
else:
    print("✗ Missing Evidence table")

if "## Uncertainty and gaps" in answer:
    print("✓ Uncertainty section present")
else:
    print("✗ Missing Uncertainty section")

if "## Human review needed" in answer:
    print("✓ Human review section present")
else:
    print("✗ Missing Human review section")

if "(Source:" in answer:
    print("✓ Citations present")
else:
    print("✗ Missing citations")

if "## Refusal" in answer:
    print("✓ Refusal format used")
