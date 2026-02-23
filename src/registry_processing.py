from collections import defaultdict

import frontmatter
import requests
import yaml

from linkml_structures import empty_annotations, linkml_schema, linkml_class, linkml_slot, linkml_type


def read_from_registry(okn_registry_id):
    target_url = f"https://raw.githubusercontent.com/frink-okn/okn-registry/refs/heads/main/docs/registry/kgs/{okn_registry_id}.md"
    response = requests.get(target_url)
    post = frontmatter.loads(response.content)

    schema = linkml_schema(
        post["shortname"],
        post["title"],
        post.get("description", "No description available."),
    )
    schema["description"] = post.get("description", "")
    schema["see_also"] = []
    for metadata_key in ["stats", "funding", "sparql", "tpf"]:
        if metadata_key in post:
            schema["see_also"].append(post[metadata_key])

    if "contact" in post:
        contact_info = post.get("contact")
        if contact_info.get("email"):
            schema.setdefault("contributors", []).append(
                "mailto:" + post["contact"]["email"]
            )
        elif contact_info.get("github"):
            schema.setdefault("contributors", []).append(
                "https://github.com/" + post["contact"]["github"]
            )
    elif "contacts" in post:
        for contact in post.get("contacts"):
            if contact.get("email"):
                schema.setdefault("contributors", []).append(
                    "mailto:" + contact["email"]
                )
            elif contact.get("github"):
                schema.setdefault("contributors", []).append(
                    "https://github.com/" + contact["github"]
                )

    return schema


def schema_from_existing(old_schema_path):
    with open(old_schema_path) as f:
        old_schema = yaml.safe_load(f.read())
    old_schema["annotations"] = empty_annotations()
    old_schema["imports"] = set(old_schema["imports"])
    old_schema["classes"] = defaultdict(linkml_class, old_schema["classes"])
    old_schema["slots"] = defaultdict(linkml_slot, old_schema["slots"])
    if "types" not in old_schema:
        old_schema["types"] = defaultdict(linkml_type)
    return old_schema

