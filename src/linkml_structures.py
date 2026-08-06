from collections import defaultdict

from linkml_runtime.linkml_model import SchemaDefinition, Annotation, Prefix


def linkml_schema(graph_name: str, graph_title: str | None, graph_description: str | None) -> SchemaDefinition:
    """Produces a new SchemaDefinition to be filled in.

    Args:
        graph_name: Name of the graph.
        graph_title: If present, a title for the graph.
        graph_description: If present, a description for the graph.

    Returns:
        New SchemaDefinition.
    """
    new_def = SchemaDefinition(name=graph_name, id="okns:"+graph_name, description=graph_description or "", title=graph_title or "")
    new_def.prefixes = {
        'okns': Prefix('okns', 'https://purl.org/okn/schema/'),
        'okn': Prefix('okn', 'https://purl.org/okn/')
    }
    new_def.default_prefix = 'okns'
    new_def.annotations = {
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
    return new_def
