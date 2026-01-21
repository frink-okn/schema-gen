# This is a list of LinkML schemas representing external ontologies
# (i.e. those not defined by LinkML itself or by a Proto-OKN graph).
#
# Most of these were generated in order by excluding it and all entries below it
# from the external ontologies list
# and then rerunning the generation scripts
#
# python3 dump_yaml.py $graph /path/to/$graph
# gen-jsonld-context $graph.yaml >$graph".context.jsonld"
# gen-rdf $graph.yaml >$graph".ttl"
# python3 docgen-frink.py -v $graph".yaml" --diagram-type mermaid_class_diagram --directory ~/graph-descriptions/$graph --no-mergeimports --subfolder-type-separation --include-top-level-diagram --template-directory docgen-frink
#
# for each graph $graph .

import logging
from collections import defaultdict
from copy import deepcopy

import linkml_runtime

from common_functions import check_for_cycles

external_ontologies_dict = {
    "owl-rdf-rdfs": {
        "read_path": "https://purl.org/okn/schema/owl-rdf-rdfs",
        "from_path": "okns:owl-rdf-rdfs",
    },
    "prov": {"read_path": "https://purl.org/okn/schema/prov", "from_path": "okns:prov"},
    "vcard": {
        "read_path": "https://purl.org/okn/schema/vcard",
        "from_path": "okns:vcard",
    },
    "skos": {"read_path": "https://purl.org/okn/schema/skos", "from_path": "okns:skos"},
    "dc": {"read_path": "https://purl.org/okn/schema/dc", "from_path": "okns:dc"},
    "time": {"read_path": "https://purl.org/okn/schema/time", "from_path": "okns:time"},
    "daml": {"read_path": "https://purl.org/okn/schema/daml", "from_path": "okns:daml"},
    "wfb": {"read_path": "https://purl.org/okn/schema/wfb", "from_path": "okns:wfb"},
    "vaem": {"read_path": "https://purl.org/okn/schema/vaem", "from_path": "okns:vaem"},
    "dtype": {
        "read_path": "https://purl.org/okn/schema/dtype",
        "from_path": "okns:dtype",
    },
    "swvs": {"read_path": "https://purl.org/okn/schema/swvs", "from_path": "okns:swvs"},
    "wgs": {"read_path": "https://purl.org/okn/schema/wgs", "from_path": "okns:wgs"},
    "ical": {"read_path": "https://purl.org/okn/schema/ical", "from_path": "okns:ical"},
    "wot": {"read_path": "https://purl.org/okn/schema/wot", "from_path": "okns:wot"},
    "xhv": {"read_path": "https://purl.org/okn/schema/xhv", "from_path": "okns:xhv"},
    "foaf": {"read_path": "https://purl.org/okn/schema/foaf", "from_path": "okns:foaf"},
    "cc": {"read_path": "https://purl.org/okn/schema/cc", "from_path": "okns:cc"},
    "frbr": {"read_path": "https://purl.org/okn/schema/frbr", "from_path": "okns:frbr"},
    "vann": {"read_path": "https://purl.org/okn/schema/vann", "from_path": "okns:vann"},
    "event": {
        "read_path": "https://purl.org/okn/schema/event",
        "from_path": "okns:event",
    },
    "address": {
        "read_path": "https://purl.org/okn/schema/address",
        "from_path": "okns:address",
    },
    "bibo": {"read_path": "https://purl.org/okn/schema/bibo", "from_path": "okns:bibo"},
    "frbroo": {
        "read_path": "https://purl.org/okn/schema/frbroo",
        "from_path": "okns:frbroo",
    },
    "cidoc-crm": {
        "read_path": "https://purl.org/okn/schema/cidoc-crm",
        "from_path": "okns:cidoc-crm",
    },
    "eli": {"read_path": "https://purl.org/okn/schema/eli", "from_path": "okns:eli"},
    "org": {"read_path": "https://purl.org/okn/schema/org", "from_path": "okns:org"},
    "sim": {"read_path": "https://purl.org/okn/schema/sim", "from_path": "okns:sim"},
    "rev": {"read_path": "https://purl.org/okn/schema/rev", "from_path": "okns:rev"},
    "ao": {"read_path": "https://purl.org/okn/schema/ao", "from_path": "okns:ao"},
    "mo": {"read_path": "https://purl.org/okn/schema/mo", "from_path": "okns:mo"},
    "sdo": {"read_path": "https://purl.org/okn/schema/sdo", "from_path": "okns:sdo"},
    "gr": {"read_path": "https://purl.org/okn/schema/gr", "from_path": "okns:gr"},
    "adms": {"read_path": "https://purl.org/okn/schema/adms", "from_path": "okns:adms"},
    "regorg": {
        "read_path": "https://purl.org/okn/schema/regorg",
        "from_path": "okns:regorg",
    },
    "void": {"read_path": "https://purl.org/okn/schema/void", "from_path": "okns:void"},
    "voag": {"read_path": "https://purl.org/okn/schema/voag", "from_path": "okns:voag"},
    "voaf": {"read_path": "https://purl.org/okn/schema/voaf", "from_path": "okns:voaf"},
    "qudt": {"read_path": "https://purl.org/okn/schema/qudt", "from_path": "okns:qudt"},
    "swrl": {"read_path": "https://purl.org/okn/schema/swrl", "from_path": "okns:swrl"},
    "biro": {"read_path": "https://purl.org/okn/schema/biro", "from_path": "okns:biro"},
    "c4o": {"read_path": "https://purl.org/okn/schema/c4o", "from_path": "okns:c4o"},
    "geo": {"read_path": "https://purl.org/okn/schema/geo", "from_path": "okns:geo"},
    "iospress": {
        "read_path": "https://purl.org/okn/schema/iospress",
        "from_path": "okns:iospress",
    },
    "gnis-ld-usgs": {
        "read_path": "https://purl.org/okn/schema/gnis-ld-usgs",
        "from_path": "okns:gnis-ld-usgs",
    },
    "gnis-ld-gnis": {
        "read_path": "https://purl.org/okn/schema/gnis-ld-gnis",
        "from_path": "okns:gnis-ld-gnis",
    },
    "sf": {"read_path": "https://purl.org/okn/schema/sf", "from_path": "okns:sf"},
    "kwg": {"read_path": "https://purl.org/okn/schema/kwg", "from_path": "okns:kwg"},
    "creativecommons": {
        "read_path": "https://purl.org/okn/schema/creativecommons",
        "from_path": "okns:creativecommons",
    },
    "spinrdf": {
        "read_path": "https://purl.org/okn/schema/spinrdf",
        "from_path": "okns:spinrdf",
    },
    "seegrid-iso19115": {
        "read_path": "https://purl.org/okn/schema/seegrid-iso19115",
        "from_path": "okns:seegrid-iso19115",
    },
    "sc": {"read_path": "https://purl.org/okn/schema/sc", "from_path": "okns:sc"},
    "hyf": {"read_path": "https://purl.org/okn/schema/hyf", "from_path": "okns:hyf"},
    # iof
    # bfo
    # ro
    # obi
    # sio
    # bao
    # cheminf
}


# --- External Ontology Loading ---
def load_external_ontologies(
    source=external_ontologies_dict,
    external_ontology_path=None,
):
    URIs_to_entities = {}
    URIs_to_ontologies = {
        "xsd:length": "okns:extended_types",
        "xsd:minLength": "okns:extended_types",
        "xsd:maxLength": "okns:extended_types",
        "xsd:minExclusive": "okns:extended_types",
        "xsd:maxExclusive": "okns:extended_types",
        "rdf:langRange": "okns:extended_types",
    }
    URI_entity_types = {}
    subclass_tree = defaultdict(set)

    for name, external_ontology in source.items():
        current_from_path = external_ontology["from_path"]
        current_read_path = external_ontology["read_path"]
        if external_ontology_path:
            current_read_path = current_read_path.replace(
                "https://purl.org/okn/schema/", external_ontology_path
            )

        try:
            current_schema = linkml_runtime.SchemaView(current_read_path + ".yaml")
        except (FileNotFoundError, OSError) as e:
            logging.warning(f"Could not load external ontology {name}: {e}")
            continue

        # Optimization: Localize lookups within loop
        for current_type in current_schema.schema.types.values():
            if (
                "uri" in current_type
                and (current_type["uri"] not in URIs_to_ontologies)
                and (current_type["from_schema"] != current_from_path)
            ):
                current_uri = current_type["uri"]
                URIs_to_entities[current_uri] = current_type
                URI_entity_types[current_uri] = "type"
                URIs_to_ontologies[current_uri] = deepcopy(current_from_path)

        for current_class in current_schema.schema.classes.values():
            if (
                "class_uri" in current_class
                and (current_class["class_uri"] not in URIs_to_ontologies)
                and (current_class["from_schema"] != current_from_path)
            ):
                current_uri = current_class["class_uri"]
                URIs_to_entities[current_uri] = current_class
                URI_entity_types[current_uri] = "class"
                URIs_to_ontologies[current_uri] = deepcopy(current_from_path)
                if current_class.is_a is not None:
                    if not check_for_cycles(
                        subclass_tree, current_class.name, current_class.is_a
                    ):
                        subclass_tree[current_class.is_a].add(current_class.name)

        for current_slot in current_schema.schema.slots.values():
            if (
                "slot_uri" in current_slot
                and (current_slot["slot_uri"] not in URIs_to_ontologies)
                and (current_slot["from_schema"] != current_from_path)
            ):
                current_uri = current_slot["slot_uri"]
                URIs_to_entities[current_uri] = current_slot
                URI_entity_types[current_uri] = "slot"
                URIs_to_ontologies[current_uri] = deepcopy(current_from_path)

    return {
        "URIs_to_entities": URIs_to_entities,
        "URI_entity_types": URI_entity_types,
        "URIs_to_ontologies": URIs_to_ontologies,
        "subclass_tree": subclass_tree,
    }
