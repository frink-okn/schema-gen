from linkml_runtime.utils.metamodelcore import URIorCURIE, XSDDateTime
from rdflib.namespace import Namespace, XSD, SKOS, DCTERMS, DCAT, RDF, RDFS, OWL, SDO, PROV, DC

SHEX = Namespace("http://www.w3.org/ns/shex#")

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

linkml_prefixes = {"linkml": "https://w3id.org/linkml/"}

# Only mappings to LinkML types are listed here.
datatype_to_type = {
    XSD.string: ['string', 'linkml:types', linkml_prefixes],
    XSD.integer: ['integer', 'linkml:types', linkml_prefixes],
    XSD.boolean: ['boolean', 'linkml:types', linkml_prefixes],
    XSD.float: ['float', 'linkml:types', linkml_prefixes],
    XSD.double: ['double', 'linkml:types', linkml_prefixes],
    XSD.decimal: ['decimal', 'linkml:types', linkml_prefixes],
    XSD.time: ['time', 'linkml:types', linkml_prefixes],
    XSD.date: ['date', 'linkml:types', linkml_prefixes],
    XSD.dateTime: ['datetime', 'linkml:types', linkml_prefixes],
    XSD.anyURI: ['uri', 'linkml:types', linkml_prefixes],
    # date_or_datetime, uriorcurie, curie
    XSD.NCName: ['ncname', 'linkml:types', linkml_prefixes],
    SHEX.iri: ['objectidentifier', 'linkml:types', linkml_prefixes],
    SHEX.nonLiteral: ['nodeidentifier', 'linkml:types', linkml_prefixes],
    # jsonpointer, jsonpath, sparqlpath

    # any_number, signedInteger
    XSD.nonNegativeInteger: ['unsignedInteger', 'linkml:extended_types', linkml_prefixes],
    XSD.byte: ['int8', 'linkml:extended_types', linkml_prefixes],
    XSD.short: ['int16', 'linkml:extended_types', linkml_prefixes],
    XSD.int: ['int32', 'linkml:extended_types', linkml_prefixes],
    XSD.long: ['int64', 'linkml:extended_types', linkml_prefixes],
    XSD.unsignedByte: ['uint8', 'linkml:extended_types', linkml_prefixes],
    XSD.unsignedShort: ['uint16', 'linkml:extended_types', linkml_prefixes],
    XSD.unsignedInt: ['uint32', 'linkml:extended_types', linkml_prefixes],
    XSD.unsignedLong: ['uint64', 'linkml:extended_types', linkml_prefixes],
    # float16, float32, float64
}
linkml_type_names = [v[0] for v in datatype_to_type.values()]

def linkml_type_mapping(object_datatype):
    """Substitutes a type with its reference from the LinkML types.yaml file."""
    return datatype_to_type.get(object_datatype, [object_datatype, '', {}])
