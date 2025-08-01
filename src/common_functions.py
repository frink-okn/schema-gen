import logging
from rdflib import URIRef
from rdflib.namespace import XSD, SDO

from prefix_definitions import replacements

def find_prefix(node):
    """ Replaces a URI prefix with the abbreviation as given in 'replacements' above. """
    replacement = ''
    prefix = ''
    for current_replacement, current_prefix in replacements:
        removed = node.removeprefix(str(current_prefix))
        if removed != str(node):
            replacement = current_replacement
            prefix = current_prefix

            # TODO: maintain in sync with prefix-definitions
            # TODO: see if everyone can be put on the same page regarding schema.org protocol
            # TODO: check existing schematizations of RDF protocols for use of http://schema.org
            if replacement == 'schema':
                replacement = 'sdos'
                prefix = str(SDO)

            removed = replacement + ':' + removed
            node = removed
    return node, replacement, prefix

def get_object_datatype(obj):
    if isinstance(obj, URIRef):
        object_datatype = XSD.anyURI
    else:
        object_datatype = obj.datatype
    if object_datatype is None:
        object_datatype = XSD.string
    return object_datatype

def value_is_valid(string_to_store, datatype, pred, obj_name):
    if datatype == str:
        return True
    if datatype.is_valid(string_to_store):
        return True
    logging.warning('Attempted to add value "%s" for predicate %s to object %s', string_to_store, pred, obj_name)
    return False
