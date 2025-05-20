from linkml_runtime.utils.metamodelcore import URIorCURIE, XSDDateTime
from rdflib.namespace import XSD, SKOS, DCTERMS, DCAT, RDF, RDFS, OWL, SDO, PROV, DC

CLASS_TYPES = {
    RDFS.Class: {},
    OWL.Class: {},
    OWL.DeprecatedClass: {'deprecated': 'This class is noted as being deprecated, without an explicit reason given.'},
}
SLOT_TYPES = {
    RDF.Property: {},
    RDFS.ContainerMembershipProperty: {},
    OWL.DatatypeProperty: {},
    OWL.AnnotationProperty: {},
    OWL.ObjectProperty: {},
    OWL.DeprecatedProperty: {'deprecated': 'This property is noted as being deprecated, without an explicit reason given.'},
    OWL.SymmetricProperty: {'symmetric': True},
    OWL.AsymmetricProperty: {'asymmetric': True},
    OWL.IrreflexiveProperty: {'irreflexive': True},
    OWL.ReflexiveProperty: {'reflexive': True},
    OWL.TransitiveProperty: {'transitive': True},
    OWL.FunctionalProperty: {'multivalued': False},
    OWL.InverseFunctionalProperty: {'key': True},
}
TYPE_TYPES = {
    RDFS.Datatype: {}
}
METADATA_TYPES = {OWL.Ontology, OWL.AllDisjointClasses, OWL.Restriction} | set(CLASS_TYPES.keys()) | set(SLOT_TYPES.keys()) | set(TYPE_TYPES.keys()) | {RDF.List}

SLOTS_TO_PREDICATES_SINGLE = {
    DCTERMS.description: ("description", str),
    DC.description: ("description", str),
    SKOS.definition: ("description", str),
    RDFS.comment: ("description", str),
    DCTERMS.title: ("title", str),
    DC.title: ("title", str),
    RDFS.label: ("title", str),
    OWL.deprecated: ("deprecated", str),
    RDFS.isDefinedBy: ("source", URIorCURIE),
    DCTERMS.language: ("in_language", str),
    DCTERMS.isReplacedBy: ("deprecated_element_has_exact_replacement", URIorCURIE),
    DCTERMS.creator: ("created_by", URIorCURIE),
    DCTERMS.created: ("created_on", XSDDateTime),
    DCTERMS.modified: ("last_updated_on", XSDDateTime),
    DC.date: ("last_updated_on", XSDDateTime),
}
SLOTS_TO_PREDICATES_MULTIPLE_STR = {
    PROV.todo: ("todos", str),
    SKOS.note: ("notes", str),
    SKOS.changeNote: ("notes", str),
    SKOS.editorialNote: ("notes", str),
    SKOS.historyNote: ("notes", str),
    SKOS.scopeNote: ("notes", str),
    RDFS.seeAlso: ("see_also", URIorCURIE),
    SKOS.altLabel: ("aliases", str),
    SKOS.mappingRelation: ("mappings", URIorCURIE),
    SKOS.exactMatch: ("exact_mappings", URIorCURIE),
    SKOS.closeMatch: ("close_mappings", URIorCURIE),
    SKOS.relatedMatch: ("related_mappings", URIorCURIE),
    SKOS.narrowMatch: ("narrow_mappings", URIorCURIE),
    SKOS.broadMatch: ("broad_mappings", URIorCURIE),
    DCTERMS.contributor: ("contributors", URIorCURIE),
    DCAT.theme: ("categories", URIorCURIE),
    DCAT.keyword: ("keywords", str),
    SDO.keywords: ("keywords", str),
}
SLOTS_TO_PREDICATES_SINGLE_ONTOLOGY = {
    DCTERMS.hasVersion: ("version", str),
}

SINGLE_VALUE_RESTRICTIONS = {
    OWL.cardinality: 'exact_cardinality',
    OWL.minCardinality: 'minimum_cardinality',
    OWL.maxCardinality: 'maximum_cardinality',
    OWL.qualifiedCardinality: 'exact_cardinality',
    OWL.minQualifiedCardinality: 'minimum_cardinality',
    OWL.maxQualifiedCardinality: 'maximum_cardinality',
}

datatype_to_type = {
    XSD.string: 'string',
    XSD.integer: 'integer',
    XSD.int: 'integer',
    XSD.boolean: 'boolean',
    XSD.float: 'float',
    XSD.double: 'double',
    XSD.decimal: 'decimal',
    XSD.time: 'time',
    XSD.date: 'date',
    XSD.dateTime: 'datetime',
    XSD.anyUri: 'uri', # remove once no longer encountered
    XSD.anyURI: 'uri',
}

def linkml_type_mapping(object_datatype):
    """Substitutes a type with its reference from the LinkML types.yaml file."""
    return datatype_to_type.get(object_datatype, object_datatype)
