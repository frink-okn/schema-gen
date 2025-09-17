from linkml_runtime.utils.metamodelcore import URIorCURIE, XSDDateTime
from rdflib import URIRef
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
    OWL.OntologyProperty: {},
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
    DCTERMS.conformsTo: ("conforms_to", str),
    DCTERMS.description: ("description", str),
    DC.description: ("description", str),
    SKOS.definition: ("description", str),
    PROV.definition: ("description", str),
    RDFS.comment: ("description", str),
    DCTERMS.title: ("title", str),
    DC.title: ("title", str),
    RDFS.label: ("title", str),
    OWL.deprecated: ("deprecated", str),
    RDFS.isDefinedBy: ("source", URIorCURIE),
    URIRef("https://schema.org/source"): ("source", URIorCURIE),
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
    OWL.sameAs: ("exact_mappings", URIorCURIE),
    SDO.sameAs: ("exact_mappings", URIorCURIE),
    OWL.equivalentProperty: ("exact_mappings", URIorCURIE),
    SKOS.closeMatch: ("close_mappings", URIorCURIE),
    SKOS.relatedMatch: ("related_mappings", URIorCURIE),
    SKOS.narrowMatch: ("narrow_mappings", URIorCURIE),
    SKOS.broadMatch: ("broad_mappings", URIorCURIE),
    DCTERMS.contributor: ("contributors", URIorCURIE),
    SDO.contributor: ("contributors", URIorCURIE),
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

types_url = 'linkml:types'
extended_types_url = 'okns:extended_types'

# Only mappings to LinkML types are listed here.
datatype_to_type = {
    XSD.string: ['string', types_url, linkml_prefixes],
    XSD.integer: ['integer', types_url, linkml_prefixes],
    XSD.boolean: ['boolean', types_url, linkml_prefixes],
    XSD.float: ['float', types_url, linkml_prefixes],
    XSD.double: ['double', types_url, linkml_prefixes],
    XSD.decimal: ['decimal', types_url, linkml_prefixes],
    XSD.time: ['time', types_url, linkml_prefixes],
    XSD.date: ['date', types_url, linkml_prefixes],
    XSD.dateTime: ['datetime', types_url, linkml_prefixes],
    XSD.anyURI: ['uri', types_url, linkml_prefixes],
    # date_or_datetime, uriorcurie, curie
    XSD.NCName: ['ncname', types_url, linkml_prefixes],
    SHEX.iri: ['objectidentifier', types_url, linkml_prefixes],
    SHEX.nonLiteral: ['nodeidentifier', types_url, linkml_prefixes],
    # jsonpointer, jsonpath, sparqlpath

    # any_number, signedInteger
    XSD.nonNegativeInteger: ['unsignedinteger', extended_types_url, linkml_prefixes],
    XSD.byte: ['int8', extended_types_url, linkml_prefixes],
    XSD.short: ['int16', extended_types_url, linkml_prefixes],
    XSD.int: ['int32', extended_types_url, linkml_prefixes],
    XSD.long: ['int64', extended_types_url, linkml_prefixes],
    XSD.unsignedByte: ['uint8', extended_types_url, linkml_prefixes],
    XSD.unsignedShort: ['uint16', extended_types_url, linkml_prefixes],
    XSD.unsignedInt: ['uint32', extended_types_url, linkml_prefixes],
    XSD.unsignedLong: ['uint64', extended_types_url, linkml_prefixes],
    XSD.positiveInteger: ['positiveinteger', extended_types_url, linkml_prefixes],
    XSD.nonPositiveInteger: ['nonpositiveinteger', extended_types_url, linkml_prefixes],
    XSD.negativeInteger: ['negativeinteger', extended_types_url, linkml_prefixes],
    XSD.token: ['token', extended_types_url, linkml_prefixes],
    XSD.normalizedString: ['normalizedstring', extended_types_url, linkml_prefixes],
    XSD.language: ['language', extended_types_url, linkml_prefixes],
    XSD.hexBinary: ['hexbinary', extended_types_url, linkml_prefixes],
    XSD.base64Binary: ['base64binary', extended_types_url, linkml_prefixes],
    XSD.Name: ['name', extended_types_url, linkml_prefixes],
    XSD.NMTOKEN: ['nmtoken', extended_types_url, linkml_prefixes],
    OWL.rational: ['rational', extended_types_url, linkml_prefixes],
    OWL.real: ['real', extended_types_url, linkml_prefixes],
    # float16, float32, float64
}
linkml_type_names = [v[0] for v in datatype_to_type.values()]

def linkml_type_mapping(object_datatype):
    """Substitutes a type with its reference from the LinkML types file."""
    return datatype_to_type.get(object_datatype, [object_datatype, '', {}])
