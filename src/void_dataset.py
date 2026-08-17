from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal, NotRequired, TypeAlias, TypedDict, Union, get_args

from linkml_runtime.linkml_model.meta import AnonymousSlotExpression, SchemaDefinition
from rdflib import Literal as rdfLiteral, Namespace, URIRef
from rdflib.namespace import VOID
from rdflib.term import Identifier, Node

VOIDEXT = Namespace("http://ldf.fi/void-ext#")

partition_indicators = {
    # subject
    "void:classPartition": (VOID.classPartition, VOID["class"]),  # subject class
    # A class-based partition with rdfs:Resource as its void:class is defined to also contain all resources that have no explicit rdf:type statement.
    "voidext:subjectNamespacePartition": (
        VOIDEXT.subjectNamespacePartition,
        VOIDEXT.namespace,
    ),  # subject namespace
    "voidext:subjectIRILengthPartition": (
        VOIDEXT.subjectIRILengthPartition,
        VOIDEXT.length,
    ),  # subject IRI length
    "voidext:subjectPartition": (VOIDEXT.subjectPartition, VOIDEXT.subject),  # certain subject
    # predicate
    "voidext:propertyClassPartition": (
        VOIDEXT.propertyClassPartition,
        VOID["class"],
    ),  # property class
    "voidext:propertyNamespacePartition": (
        VOIDEXT.propertyNamespacePartition,
        VOIDEXT.namespace,
    ),  # property namespace
    "voidext:propertyIRILengthPartition": (
        VOIDEXT.propertyIRILengthPartition,
        VOIDEXT.length,
    ),  # property IRI length
    "void:propertyPartition": (VOID.propertyPartition, VOID.property),  # certain property
    # object (IRI)
    "voidext:objectClassPartition": (
        VOIDEXT.objectClassPartition,
        VOID["class"],
    ),  # object class
    "voidext:objectNamespacePartition": (
        VOIDEXT.objectNamespacePartition,
        VOIDEXT.namespace,
    ),  # object namespace
    "voidext:objectIRILengthPartition": (
        VOIDEXT.objectIRILengthPartition,
        VOIDEXT.length,
    ),  # object IRI length
    "voidext:objectPartition": (VOIDEXT.objectPartition, VOIDEXT.object),  # certain object
    # object (literal)
    "voidext:datatypePartition": (
        VOIDEXT.datatypePartition,
        VOIDEXT.datatype,
    ),  # literal datatype
    "voidext:languagePartition": (
        VOIDEXT.languagePartition,
        VOIDEXT.language,
    ),  # literal language
    "voidext:literalLengthPartition": (
        VOIDEXT.literalLengthPartition,
        VOIDEXT.length,
    ),  # literal length
    # other
    "voidext:iriLengthPartition": (VOIDEXT.iriLengthPartition, VOIDEXT.length),  # IRI length
    # VOIDEXT.minLength: A minimum length (inclusive) that is required for an object to be included in a length-based partition.
}

@lru_cache
def get_indicator_key(level: str) -> str:
    _, indicator_predicate = partition_indicators[level]
    return {
        VOID["class"]: "void:class",
        VOID.property: "void:property",
        VOIDEXT.datatype: "voidext:datatype",
        VOIDEXT.language: "voidext:language",
        VOIDEXT.length: "voidext:length",
        VOIDEXT.namespace: "voidext:namespace",
        VOIDEXT.object: "voidext:object",
        VOIDEXT.subject: "voidext:subject",
    }[indicator_predicate]

all_partition_types = {v[0] for v in partition_indicators.values()}
iri_length_partition_types = {
    VOIDEXT.subjectIRILengthPartition,
    VOIDEXT.propertyIRILengthPartition,
    VOIDEXT.objectIRILengthPartition,
    VOIDEXT.iriLengthPartition,
}
literal_partition_types = {
    VOIDEXT.datatypePartition,
    VOIDEXT.languagePartition,
    VOIDEXT.literalLengthPartition,
}
nonblank_subject_partition_types = {
    VOIDEXT.subjectNamespacePartition,
    VOIDEXT.subjectIRILengthPartition,
    VOIDEXT.subjectPartition,
}
nonblank_object_partition_types = {
    VOIDEXT.objectClassPartition,
    VOIDEXT.objectNamespacePartition,
    VOIDEXT.objectIRILengthPartition,
    VOIDEXT.objectPartition,
}
applicable_statistics = {
    VOID.triples: all_partition_types,
    VOID.classes: all_partition_types,
    VOID.properties: all_partition_types,
    VOID.distinctSubjects: all_partition_types,
    VOID.distinctObjects: all_partition_types,
    VOIDEXT.averageIRILength: all_partition_types - iri_length_partition_types,
    VOIDEXT.averageLiteralLength: all_partition_types
    - {VOIDEXT.literalLengthPartition},
    VOIDEXT.averageObjectIRILength: all_partition_types
    - {VOIDEXT.objectIRILengthPartition},
    VOIDEXT.averagePropertyIRILength: all_partition_types
    - {VOIDEXT.propertyIRILengthPartition},
    VOIDEXT.averageSubjectIRILength: all_partition_types
    - {VOIDEXT.subjectIRILengthPartition},
    VOIDEXT.datatypes: all_partition_types - {VOIDEXT.datatypePartition},
    VOIDEXT.distinctBlankNodeObjects: all_partition_types - literal_partition_types,
    VOIDEXT.distinctBlankNodeSubjects: all_partition_types
    - nonblank_subject_partition_types,
    VOIDEXT.distinctBlankNodes: all_partition_types,
    VOIDEXT.distinctIRIReferenceObjects: all_partition_types - literal_partition_types,
    VOIDEXT.distinctIRIReferenceSubjects: all_partition_types,
    VOIDEXT.distinctIRIReferences: all_partition_types,
    VOIDEXT.distinctLiterals: all_partition_types - nonblank_object_partition_types,
    VOIDEXT.distinctRDFNodes: all_partition_types,
    VOIDEXT.languages: all_partition_types
    - (nonblank_object_partition_types | {VOIDEXT.languagePartition}),
    VOIDEXT.objectClasses: all_partition_types - {VOIDEXT.objectClassPartition},
    VOIDEXT.propertyClasses: all_partition_types - {VOIDEXT.propertyClassPartition},
    VOIDEXT.subjectClasses: all_partition_types - {VOID.classPartition},
}
type_to_stats = defaultdict(set)
for k, v in applicable_statistics.items():
    for q in list(v):
        type_to_stats[q].add(k)


ExampleDict = TypedDict(
    "ExampleDict",
    {
        "@type": Literal["rdf:Statement"],
        "subject": str,
        "predicate": str,
        "object": str
    }
)


VoidDatasetDict = TypedDict(
    "VoidDatasetDict",
    {
        "@type": Literal["void:Dataset"],
        "skos:example": NotRequired[ExampleDict],
        "void:triples": NotRequired[int],
        "void:classes": NotRequired[int],
        "void:properties": NotRequired[int],
        "void:distinctObjects": NotRequired[int],
        "void:distinctSubjects": NotRequired[int],
        "voidext:averageIRILength": NotRequired[int],
        "voidext:averageLiteralLength": NotRequired[int],
        "voidext:averageObjectIRILength": NotRequired[int],
        "voidext:averagePropertyIRILength": NotRequired[int],
        "voidext:averageSubjectIRILength": NotRequired[int],
        "voidext:datatypes": NotRequired[int],
        "voidext:distinctBlankNodeObjects": NotRequired[int],
        "voidext:distinctBlankNodes": NotRequired[int],
        "voidext:distinctBlankNodeSubjects": NotRequired[int],
        "voidext:distinctIRIReferenceObjects": NotRequired[int],
        "voidext:distinctIRIReferences": NotRequired[int],
        "voidext:distinctIRIReferenceSubjects": NotRequired[int],
        "voidext:distinctLiterals": NotRequired[int],
        "voidext:distinctRDFNodes": NotRequired[int],
        "voidext:languages": NotRequired[int],
        "voidext:objectClasses": NotRequired[int],
        "voidext:propertyClasses": NotRequired[int],
        "voidext:subjectClasses": NotRequired[int],
        "void:class": NotRequired[str],
        "void:property": NotRequired[str],
        "voidext:datatype": NotRequired[str],
        "voidext:language": NotRequired[str],
        "voidext:length": NotRequired[int],
        "voidext:namespace": NotRequired[str],
        "voidext:object": NotRequired[str],
        "voidext:subject": NotRequired[str],
        "void:classPartition": NotRequired[list["VoidDatasetDict"]],
        "void:propertyPartition": NotRequired[list["VoidDatasetDict"]],
        "voidext:datatypePartition": NotRequired[list["VoidDatasetDict"]],
        "voidext:iriLengthPartition": NotRequired[list["VoidDatasetDict"]],
        "voidext:languagePartition": NotRequired[list["VoidDatasetDict"]],
        "voidext:literalLengthPartition": NotRequired[list["VoidDatasetDict"]],
        "voidext:objectClassPartition": NotRequired[list["VoidDatasetDict"]],
        "voidext:objectIRILengthPartition": NotRequired[list["VoidDatasetDict"]],
        "voidext:objectNamespacePartition": NotRequired[list["VoidDatasetDict"]],
        "voidext:objectPartition": NotRequired[list["VoidDatasetDict"]],
        "voidext:propertyClassPartition": NotRequired[list["VoidDatasetDict"]],
        "voidext:propertyIRILengthPartition": NotRequired[list["VoidDatasetDict"]],
        "voidext:propertyNamespacePartition": NotRequired[list["VoidDatasetDict"]],
        "voidext:subjectIRILengthPartition": NotRequired[list["VoidDatasetDict"]],
        "voidext:subjectNamespacePartition": NotRequired[list["VoidDatasetDict"]],
        "voidext:subjectPartition": NotRequired[list["VoidDatasetDict"]],
    },
)


PartitionsDict = TypedDict(
    "PartitionsDict",
    {
        "void:classPartition": NotRequired[dict[str, "VoidDataset"]],
        "void:propertyPartition": NotRequired[dict[str, "VoidDataset"]],
        "voidext:datatypePartition": NotRequired[dict[str, "VoidDataset"]],
        "voidext:iriLengthPartition": NotRequired[dict[str, "VoidDataset"]],
        "voidext:languagePartition": NotRequired[dict[str, "VoidDataset"]],
        "voidext:literalLengthPartition": NotRequired[dict[str, "VoidDataset"]],
        "voidext:objectClassPartition": NotRequired[dict[str, "VoidDataset"]],
        "voidext:objectIRILengthPartition": NotRequired[dict[str, "VoidDataset"]],
        "voidext:objectNamespacePartition": NotRequired[dict[str, "VoidDataset"]],
        "voidext:objectPartition": NotRequired[dict[str, "VoidDataset"]],
        "voidext:propertyClassPartition": NotRequired[dict[str, "VoidDataset"]],
        "voidext:propertyIRILengthPartition": NotRequired[dict[str, "VoidDataset"]],
        "voidext:propertyNamespacePartition": NotRequired[dict[str, "VoidDataset"]],
        "voidext:subjectIRILengthPartition": NotRequired[dict[str, "VoidDataset"]],
        "voidext:subjectNamespacePartition": NotRequired[dict[str, "VoidDataset"]],
        "voidext:subjectPartition": NotRequired[dict[str, "VoidDataset"]],
    },
)


StatsDict = TypedDict(
    "StatsDict",
    {
        "void:classes": NotRequired[int],
        "void:distinctObjects": NotRequired[int],
        "void:distinctSubjects": NotRequired[int],
        "void:properties": NotRequired[int],
        "void:triples": NotRequired[int],
        "voidext:averageIRILength": NotRequired[int],
        "voidext:averageLiteralLength": NotRequired[int],
        "voidext:averageObjectIRILength": NotRequired[int],
        "voidext:averagePropertyIRILength": NotRequired[int],
        "voidext:averageSubjectIRILength": NotRequired[int],
        "voidext:datatypes": NotRequired[int],
        "voidext:distinctBlankNodeObjects": NotRequired[int],
        "voidext:distinctBlankNodes": NotRequired[int],
        "voidext:distinctBlankNodeSubjects": NotRequired[int],
        "voidext:distinctIRIReferenceObjects": NotRequired[int],
        "voidext:distinctIRIReferences": NotRequired[int],
        "voidext:distinctIRIReferenceSubjects": NotRequired[int],
        "voidext:distinctLiterals": NotRequired[int],
        "voidext:distinctRDFNodes": NotRequired[int],
        "voidext:languages": NotRequired[int],
        "voidext:objectClasses": NotRequired[int],
        "voidext:propertyClasses": NotRequired[int],
        "voidext:subjectClasses": NotRequired[int],
    }
)


IndicatorType: TypeAlias = Literal["void:class", "void:property", "voidext:datatype", "voidext:language", "voidext:length", "voidext:namespace", "voidext:object", "voidext:subject"]
PartitionType: TypeAlias = Literal["void:classPartition", "void:propertyPartition", "voidext:datatypePartition", "voidext:iriLengthPartition", "voidext:languagePartition", "voidext:literalLengthPartition", "voidext:objectClassPartition", "voidext:objectIRILengthPartition", "voidext:objectNamespacePartition", "voidext:objectPartition", "voidext:propertyClassPartition", "voidext:propertyIRILengthPartition", "voidext:propertyNamespacePartition", "voidext:subjectIRILengthPartition", "voidext:subjectNamespacePartition", "voidext:subjectPartition"]
StatType: TypeAlias = Literal["void:classes", "void:distinctObjects", "void:distinctSubjects", "void:properties", "void:triples", "voidext:averageIRILength", "voidext:averageLiteralLength", "voidext:averageObjectIRILength", "voidext:averagePropertyIRILength", "voidext:averageSubjectIRILength", "voidext:datatypes", "voidext:distinctBlankNodeObjects", "voidext:distinctBlankNodes", "voidext:distinctBlankNodeSubjects", "voidext:distinctIRIReferenceObjects", "voidext:distinctIRIReferences", "voidext:distinctIRIReferenceSubjects", "voidext:distinctLiterals", "voidext:distinctRDFNodes", "voidext:languages", "voidext:objectClasses", "voidext:propertyClasses", "voidext:subjectClasses"]



@dataclass
class VoidDataset:
    indicator_type: IndicatorType = "void:class"
    indicator_value: str = ""
    example: tuple[Node, Node, Node] = (Identifier(""), Identifier(""), Identifier(""))
    stats: StatsDict = field(default_factory=StatsDict)
    partitions: PartitionsDict = field(default_factory=PartitionsDict)

    def __jsonout__(self) -> VoidDatasetDict:
        base_dict: VoidDatasetDict = {
            "@type": "void:Dataset"
        }

        # Indicator
        if self.indicator_value != "":
            base_dict[self.indicator_type] = self.indicator_value

        # Example
        if self.example[0] != Identifier(""):
            base_dict["skos:example"] = {
                "@type": "rdf:Statement",
                "subject": str(self.example[0]),
                "predicate": str(self.example[1]),
                "object": str(self.example[2]),
            }

        # Statistics
        stat_types: tuple[StatType, ...] = get_args(StatType)
        for stat_type in stat_types:
            if stat_type in self.stats and self.stats[stat_type] > 0:
                base_dict[stat_type] = self.stats[stat_type]

        # Partitions
        partition_types: tuple[PartitionType, ...] = get_args(PartitionType)
        for partition_type in partition_types:
            if partition_type in self.partitions and len(self.partitions[partition_type]) > 0:
                base_dict[partition_type] = [v.__jsonout__() for v in self.partitions[partition_type].values()]

        return base_dict

    def get_partition(
        self,
        level: PartitionType,
        indicator_type: IndicatorType,
        indicator_value: str,
    ) -> "VoidDataset":
        try:
            existing_dataset = self.partitions[level][indicator_value]
            return existing_dataset
        except KeyError:
            new_dataset = VoidDataset()
            new_dataset.indicator_type = indicator_type
            new_dataset.indicator_value = indicator_value
            if level not in self.partitions:
                self.partitions[level] = {}
            self.partitions[level][indicator_value] = new_dataset
            return new_dataset

    def increment_counts(
        self,
        example: tuple[Node, Node, Node],
        example_curie_keys: tuple[tuple[str, str, str], tuple[str, str, str], tuple[str, str, str]],
        subj_type_uris_keys: tuple[str | None, str, str],
        obj_type_uris_keys: tuple[str | None, str, str],
    ) -> None:
        if "void:triples" not in self.stats:
            self.stats["void:triples"] = 0
        self.stats["void:triples"] += 1
        self.example = example
