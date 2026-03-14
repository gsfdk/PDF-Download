import re


def classify(filename: str, classifications: list) -> dict:
    """
    Match a PDF filename against the ordered classification rules in config.json.
    Returns the first matching classification dict.
    The last rule should have pattern ".*" to act as a catch-all.
    """
    for rule in classifications:
        pattern = rule.get("pattern", ".*")
        if pattern == "CHANGE_ME":
            continue
        if re.search(pattern, filename, re.IGNORECASE):
            return rule
    # Fallback: return last rule if nothing matched
    return classifications[-1]
