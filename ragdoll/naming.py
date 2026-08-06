import re


def to_title_case(name):
    parts = name.split(" ")
    titled_parts = []
    for part in parts:
        if part:
            titled_parts.append(part[0].upper() + part[1:] if len(part) > 1 else part.upper())
    return " ".join(titled_parts)


def canonicalize_bone_name(name):
    tokens = name.replace("_", " ").lower().split()
    canonical_tokens = []
    for token in tokens:
        if token == "ragdoll":
            continue
        if token.startswith("ragdoll"):
            token = token[len("ragdoll") :]
            if not token:
                continue
        if token != "bip01":
            token = re.sub(r"\d+$", "", token)
        canonical_tokens.append(token)
    return " ".join(canonical_tokens)