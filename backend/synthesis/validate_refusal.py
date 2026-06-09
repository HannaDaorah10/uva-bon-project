from pathlib import Path

# Lees refusal response in
answer = Path("refusal_response.md").read_text()

print(answer)

print("\n--- CHECKS ---")

# Controle 1: Refusal header
if "## Refusal" in answer:
    print("✓ Refusal format present")
else:
    print("✗ Refusal header missing")

# Controle 2: Reason aanwezig
if "Reason:" in answer:
    print("✓ Reason section present")
else:
    print("✗ Reason section missing")

# Controle 3: Human consult advies aanwezig
if "What a human should consult instead:" in answer:
    print("✓ Human consultation section present")
else:
    print("✗ Human consultation section missing")

# Controle 4: Geen answer-template gebruikt
if "## Answer" in answer:
    print("✗ Refusal should not contain Answer section")
else:
    print("✓ No Answer section present")

# Eindresultaat
if (
    "## Refusal" in answer
    and "Reason:" in answer
    and "What a human should consult instead:" in answer
    and "## Answer" not in answer
):
    print("\n v VALID REFUSAL")
else:
    print("\n x INVALID REFUSAL")

