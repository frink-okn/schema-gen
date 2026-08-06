import logging
from graphlib import CycleError, TopologicalSorter
from typing import Any, TypeAlias

from linkml_runtime.utils.metamodelcore import URIorCURIE, XSDDateTime
from rdflib import URIRef
from rdflib.namespace import SDO, XSD
from rdflib.term import Node

from prefix_definitions import replacements

logger = logging.getLogger()

def find_prefix(node: str) -> tuple[str, str, str]:
    """Replaces a URI prefix with the abbreviation as given in 'replacements' above."""
    replacement = ""
    prefix = ""
    for current_replacement, current_prefix in replacements:
        removed = node.removeprefix(str(current_prefix))
        if removed != str(node):
            replacement = current_replacement
            prefix = current_prefix

            # TODO: maintain in sync with prefix-definitions
            # TODO: see if everyone can be put on the same page regarding schema.org protocol
            # TODO: check existing schematizations of RDF protocols for use of http://schema.org
            if replacement == "schema":
                replacement = "sdos"
                prefix = str(SDO)

            removed = replacement + ":" + removed
            node = removed
    return node, replacement, prefix


def get_object_datatype(obj: Any) -> URIRef:
    if isinstance(obj, URIRef):
        object_datatype = XSD.anyURI
    else:
        object_datatype = obj.datatype
    if object_datatype is None:
        object_datatype = XSD.string
    return object_datatype


def value_is_valid(string_to_store: str, datatype: Any, pred: Node, obj_name: str) -> bool:
    if datatype == str:
        return True
    if datatype in {URIorCURIE, XSDDateTime}:
        if datatype.is_valid(string_to_store):
            return True
    logger.warning(
        'Attempted to add value "%s" for predicate %s to object %s',
        string_to_store,
        pred,
        obj_name,
    )
    return False

SubclassTree: TypeAlias = dict[str, set[str]]

def check_for_cycles(subclass_tree: SubclassTree, subj_key: str, obj_key: str) -> Any:
    try:
        TopologicalSorter({**subclass_tree, obj_key: set([subj_key])}).prepare()
    except CycleError as e:
        logger.warning(
            "Found a cycle in the subclass tree, which is being disregarded: %s",
            e.args[1],
        )
        return e.args[1]
    return None
