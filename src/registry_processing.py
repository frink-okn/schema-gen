from collections import defaultdict

import frontmatter
import requests
import yaml
from linkml_runtime.linkml_model import Annotation, SchemaDefinition

from linkml_structures import linkml_schema


def read_from_registry(okn_registry_id: str) -> SchemaDefinition:
    target_url = f"https://raw.githubusercontent.com/frink-okn/okn-registry/refs/heads/main/docs/registry/kgs/{okn_registry_id}.md"
    response = requests.get(target_url)
    post = frontmatter.loads(response.text)

    if "shortname" in post:
        if isinstance(post["shortname"], str):
            shortname = post["shortname"]
        else:
            shortname = "untitled"
    else:
        shortname = "untitled"

    if "title" in post:
        if isinstance(post["title"], str):
            title = post["title"]
        else:
            title = "Untitled"
    else:
        title = "Untitled"

    if "description" in post:
        if isinstance(post["description"], str):
            description = post["description"]
        else:
            description = "No description available."
    else:
        description = "No description available."

    schema = linkml_schema(shortname, title, description)
    schema["see_also"] = []
    for metadata_key in ["stats", "funding", "sparql", "tpf"]:
        if metadata_key in post:
            schema["see_also"].append(post[metadata_key])

    if "contact" in post:
        contact_info = post["contact"]
        if hasattr(contact_info, "email"):
            schema.setdefault("contributors", []).append(
                "mailto:" + contact_info.email
            )
        elif hasattr(contact_info, "github"):
            schema.setdefault("contributors", []).append(
                "https://github.com/" + contact_info.github
            )
    elif "contacts" in post:
        if not isinstance(post["contacts"], list):
            print('Contact list is not a list')
        else:
            for contact in post["contacts"]:
                if "email" in contact:
                    schema.setdefault("contributors", []).append(
                        "mailto:" + contact["email"]
                    )
                elif "github" in contact:
                    schema.setdefault("contributors", []).append(
                        "https://github.com/" + contact["github"]
                    )

    return schema


def schema_from_existing(old_schema_path: str) -> SchemaDefinition:
    with open(old_schema_path) as f:
        old_schema = SchemaDefinition(**(yaml.safe_load(f.read())))
    old_schema.annotations = {
        "counts": Annotation("counts", {
            "classes": {}, # defaultdict(int)
            "slots": {}, # defaultdict(int)
            "pairs": {} # defaultdict(lambda: defaultdict(lambda: defaultdict(int))),
        }),
        "examples": Annotation("examples", {
            "classes": {}, # defaultdict(str),
            "pairs": {} # defaultdict(lambda: defaultdict(lambda: defaultdict(dict))),
        }),
    }
    return old_schema
