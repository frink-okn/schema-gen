import re


INVALID_IDENTIFIER_CHARACTERS = re.compile(r"[^A-Za-z0-9_-]+")
REPEATED_UNDERSCORES = re.compile(r"_+")


def sanitize_identifier(value):
    """Create an identifier safe for LinkML keys and Mermaid ER diagrams."""
    identifier = INVALID_IDENTIFIER_CHARACTERS.sub("_", value)
    identifier = REPEATED_UNDERSCORES.sub("_", identifier).strip("_")
    if not identifier:
        identifier = "iri"
    if not (identifier[0].isalpha() or identifier[0] == "_"):
        identifier = f"iri_{identifier}"
    return identifier
