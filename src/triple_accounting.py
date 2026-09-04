from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Literal, NotRequired, TypeAlias, TypedDict, Union, get_args
from urllib.parse import urlsplit, urlunsplit

from linkml_runtime.linkml_model.meta import AnonymousSlotExpression, SchemaDefinition
from rdflib import BNode, Literal as rdfLiteral, Namespace, URIRef
from rdflib.namespace import VOID
from rdflib.term import Node

from linkml_structures import get_schema_annotations, get_schema_slots
from void_dataset import IndicatorType, PartitionType, VoidDataset, VoidDatasetDict, get_indicator_key

VOIDEXT = Namespace("http://ldf.fi/void-ext#")


def in_any_of(any_of: list[dict[str, Any] | AnonymousSlotExpression], key: str) -> bool:
    return not any(
        (
            (isinstance(entry, dict) and "range" in entry and entry["range"] == key)
            or (isinstance(entry, AnonymousSlotExpression) and entry.range == key)
        )
        for entry in any_of
    )


def add_to_range(
    schema: SchemaDefinition,
    pred_curie_key: tuple[str, str, str],
    obj_curie_key: tuple[str | None, str, str],
) -> None:
    schema_annotations = get_schema_annotations(schema)
    schema_slots = get_schema_slots(schema)
    pred_uri, pred_key, _ = pred_curie_key
    obj_uri, obj_key, _ = obj_curie_key

    if pred_uri in schema_annotations["URIs_in_ontologies"].value:
        return
    if obj_uri is not None:
        schema_annotations["domain_range_keys_to_uris"].value[obj_key] = obj_uri

    current_slot = schema_slots[pred_key]
    if current_slot.any_of is None:
        current_slot.any_of = []
    elif isinstance(current_slot.any_of, (dict, AnonymousSlotExpression)):
        current_slot.any_of = [current_slot.any_of]
    if not in_any_of(current_slot.any_of, obj_key):
        current_slot.any_of.append(AnonymousSlotExpression(range=obj_key))


def get_partition_indicator(
    indicator: str,
    example: tuple[Node, Node, Node],
    example_curie_keys: tuple[tuple[str, str, str], tuple[str, str, str], tuple[str, str, str]],
    subj_type: tuple[str | None, str, str],
    obj_type: tuple[str | None, str, str],
    pred_type: tuple[str | None, str, str] | None = None,
) -> tuple[IndicatorType, str]:
    indicator_key = get_indicator_key(indicator)
    indicator_types: tuple[IndicatorType, ...] = get_args(IndicatorType)
    if indicator_key not in indicator_types:
        raise TypeError("Somehow the indicator key is not valid?")

    match indicator:
        case "void:classPartition":
            if not isinstance(example[0], URIRef):
                raise TypeError
            indicator_str = subj_type[0] or "untyped"
        case "voidext:propertyClassPartition":
            if not isinstance(example[1], URIRef):
                raise TypeError
            if pred_type is None:
                indicator_str = "untyped"
            else:
                indicator_str = pred_type[0] or "untyped"
        case "voidext:objectClassPartition":
            if not isinstance(example[2], (BNode, URIRef)):
                raise TypeError
            indicator_str = obj_type[0] or "untyped"
        case "voidext:subjectNamespacePartition":
            if not isinstance(example[0], URIRef):
                raise TypeError
            indicator_str = example_curie_keys[0][2]
            if indicator_str == "":
                indicator_str = urlunsplit(urlsplit(str(example[0]))[:2] + ("","",""))
        case "voidext:propertyNamespacePartition":
            if not isinstance(example[1], URIRef):
                raise TypeError
            indicator_str = example_curie_keys[1][2]
            if indicator_str == "":
                indicator_str = urlunsplit(urlsplit(str(example[1]))[:2] + ("","",""))
        case "voidext:objectNamespacePartition":
            if not isinstance(example[2], URIRef):
                raise TypeError
            indicator_str = example_curie_keys[2][2]
            if indicator_str == "":
                indicator_str = urlunsplit(urlsplit(str(example[2]))[:2] + ("","",""))
        case "voidext:subjectIRILengthPartition":
            if not isinstance(example[0], URIRef):
                raise TypeError
            indicator_str = str(len(example[0]))
        case "voidext:propertyIRILengthPartition":
            if not isinstance(example[1], URIRef):
                raise TypeError
            indicator_str = str(len(example[1]))
        case "voidext:objectIRILengthPartition":
            if not isinstance(example[2], URIRef):
                raise TypeError
            indicator_str = str(len(example[2]))
        case "voidext:subjectPartition":
            indicator_str = example_curie_keys[0][0]
        case "void:propertyPartition":
            indicator_str = example_curie_keys[1][0]
        case "voidext:objectPartition":
            indicator_str = example_curie_keys[2][0]
        case "voidext:datatypePartition":
            if not isinstance(example[2], rdfLiteral):
                raise TypeError
            indicator_str = example[2].datatype or ""
        case "voidext:languagePartition":
            if not isinstance(example[2], rdfLiteral):
                raise TypeError
            indicator_str = example[2].language or ""
        case "voidext:literalLengthPartition":
            if not isinstance(example[2], rdfLiteral):
                raise TypeError
            indicator_str = str(len(example[2]))

    return indicator_key, indicator_str


def account_for_triple(
    schema: SchemaDefinition,
    base_counts: VoidDataset,
    example: tuple[Node, Node, Node],
    example_curie_keys: tuple[tuple[str, str, str], tuple[str, str, str], tuple[str, str, str]],
    subj_type_uris_keys: list[tuple[str | None, str, str]],
    obj_type_uris_keys: list[tuple[str | None, str, str]],
) -> None:
    schema_annotations = get_schema_annotations(schema)
    void_partition_order = schema_annotations["void_partition_order"].value
    if not isinstance(void_partition_order, list):
        raise TypeError("What's going on with the VoID partition order?")        

    _, pred_curie_key, _ = example_curie_keys

    for obj_type_curie_key in obj_type_uris_keys:
        add_to_range(schema, pred_curie_key, obj_type_curie_key)

    partition_indicators: defaultdict[PartitionType, set[tuple[IndicatorType, str]]] = defaultdict(lambda: set())
    for level in void_partition_order:
        for subj_type_curie_key in subj_type_uris_keys:
            for obj_type_curie_key in obj_type_uris_keys:
                try:
                    indicator_key, indicator_str = get_partition_indicator(level, example, example_curie_keys, subj_type_curie_key, obj_type_curie_key)
                    partition_indicators[level].add((indicator_key, indicator_str))
                except TypeError:
                    continue

    perform_counts(void_partition_order, partition_indicators, base_counts, example)


def perform_counts(
    void_partition_order: list[PartitionType],
    partition_indicators: dict[PartitionType, set[tuple[IndicatorType, str]]],
    base_partition: VoidDataset,
    example: tuple[Node, Node, Node],
) -> None:
    if len(void_partition_order) == 0:
        return

    level = void_partition_order[0]
    level_index = len(void_partition_order) - 1

    if len(partition_indicators) == 0:
        base_partition.level_index = 0
        base_partition.increment_counts(example)
    elif level not in partition_indicators:
        perform_counts(void_partition_order[1:], partition_indicators, base_partition, example)
    else:
        for indicator_key, partition_indicator in list(partition_indicators[level]):
            current_partition = base_partition.get_partition(level, indicator_key, partition_indicator)
            current_partition.level_index = level_index
            current_partition.increment_counts(example)
            new_partition_indicators = {k: v for k, v in partition_indicators.items() if k != level}
            perform_counts(void_partition_order[1:], new_partition_indicators, current_partition, example)
