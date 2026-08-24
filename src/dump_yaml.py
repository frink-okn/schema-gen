import argparse
import datetime
import logging
import os
import os.path
from argparse import Namespace
from collections import defaultdict
from functools import lru_cache
from typing import Any

import rdflib
import rdflib.exceptions
import tqdm
from linkml_runtime.dumpers import yaml_dumper
from linkml_runtime.linkml_model import (
    Annotation,
    ClassDefinition,
    Element,
    Prefix,
    SlotDefinition,
    SlotDefinitionName,
    TypeDefinition,
)
from linkml_runtime.linkml_model.meta import AnonymousSlotExpression
from linkml_runtime.utils.metamodelcore import URIorCURIE
from rdflib import BNode, Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SDO
from rdflib.term import Node
from rdflib_hdt import HDTStore

# Assumes these are available from your original environment
from common_functions import (
    check_for_cycles,
    find_prefix,
    get_object_datatype,
    value_is_valid,
)
from external_ontologies import (
    ExternalOntologyInfo,
    external_ontologies_dict,
    load_external_ontologies,
)
from formatter_url_parsing import get_formatter_urls
from linkml_structures import (
    PrefixesFieldDict,
    PrefixesFieldList,
    get_schema_annotations,
    get_schema_classes,
    get_schema_slots,
    get_schema_types,
    linkml_schema,
)
from predicate_mappings import (
    CLASS_TYPES,
    SINGLE_VALUE_RESTRICTIONS,
    SLOT_TYPES,
    SLOTS_TO_PREDICATES_MULTIPLE_STR,
    SLOTS_TO_PREDICATES_SINGLE,
    SLOTS_TO_PREDICATES_SINGLE_ONTOLOGY,
    TYPE_TYPES,
    SlotMapping,
    datatype_to_type,
    extended_types_url,
    linkml_type_mapping,
    linkml_type_names,
)
from registry_processing import read_from_registry, schema_from_existing
from triple_accounting import account_for_triple, add_to_range
from void_dataset import VoidDataset

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- Global State ---
formatter_urls = None


def get_graph(graph_to_read: str) -> Graph:
    """
    Reads in a set of TTL/RDF files.
    Optimization: explicit check for oxrdflib for speed.
    """
    g = rdflib.Graph(store="Oxigraph")

    try:
        import oxrdflib

        logger.info("oxrdflib detected. Parsing will be significantly faster.")
    except ImportError:
        logger.info("oxrdflib not found. Using standard rdflib parser.")

    if graph_to_read[0] == "/":
        folder_to_visit = graph_to_read
    else:
        folder_to_visit = os.path.join(
            "..", "frink-data-lakefs", "lakefs", graph_to_read
        )

    for root, _, files in os.walk(folder_to_visit):
        for name in files:
            current_file_path = os.path.join(root, name)
            # Optimization: Check most common extensions first
            if any(
                current_file_path.endswith(suffix)
                for suffix in [".ttl", ".nt", ".rdf", ".owl", ".n3", "_RDF"]
            ):
                current_file_read = False
                # Optimization: Prioritize faster parsers (nt, ttl)
                for file_format in ["nt", "ttl", "n3", "xml"]:
                    try:
                        g.parse(current_file_path, format=file_format)
                        print("Read", current_file_path, "as", file_format)
                        current_file_read = True
                        break
                    except Exception:
                        continue
                if not current_file_read:
                    logger.warning(f"Unable to read {current_file_path}")

            elif any(current_file_path.endswith(suffix) for suffix in [".nq"]):
                g = rdflib.Dataset()
                current_file_read = False
                for format in ["nquads", "trig", "trix"]:
                    try:
                        g.parse(current_file_path, format=format)
                        current_file_read = True
                        break
                    except rdflib.exceptions.ParserError:
                        continue
            elif current_file_path.endswith(".hdt"):
                g = rdflib.Graph(store=HDTStore(current_file_path))
                break

    return g


def add_comment(entity: Element, comment: str) -> None:
    if entity.comments is None:
        entity.comments = []
    elif isinstance(entity.comments, str):
        entity.comments = [entity.comments]
    entity.comments.append(comment)


def add_str_to_single(
    obj_in: Element,
    pred: Node,
    string_to_store: str,
    source_mapping: SlotMapping | None = None,
) -> None:
    mapping = source_mapping if source_mapping else SLOTS_TO_PREDICATES_SINGLE
    current_slot, current_datatype = mapping[pred]

    if value_is_valid(string_to_store, current_datatype, pred, obj_in["name"]):
        if current_slot not in obj_in or (
            current_slot in obj_in
            and isinstance(obj_in[current_slot], str)
            and obj_in[current_slot].endswith("defined.")
        ):
            obj_in[current_slot] = string_to_store.strip()
        else:
            add_comment(obj_in, f"{current_slot}: {string_to_store.strip()}")
    else:
        add_comment(obj_in, f"{current_slot}: {string_to_store.strip()}")


def convert_prefixes_to_dict(prefix_list: PrefixesFieldList) -> PrefixesFieldDict:
    new_prefix_dict: PrefixesFieldDict = {}
    for prefix in prefix_list:
        if isinstance(prefix, dict):
            new_prefix_dict[prefix["prefix_prefix"]] = Prefix(**prefix)
        else:
            new_prefix_dict[prefix.prefix_prefix] = prefix
    return new_prefix_dict


class GraphCharacterizer:
    def __init__(self, args: Namespace, uri_mappings: ExternalOntologyInfo):
        self.args = args

        self.g = get_graph(args.graph_to_read)
        self.generate_base_schemas = args.generate_base_schemas
        self.list_untyped_entities = args.list_untyped_entities
        self.deduplicate_types = args.deduplicate_types
        self.output_path = args.output_path

        if args.okn_registry_id:
            self.schema = read_from_registry(args.okn_registry_id)
            self.graph_name = self.schema.name
        elif args.old_schema_path:
            self.schema = schema_from_existing(args.old_schema_path)
            self.graph_name = self.schema.name
        else:
            self.graph_name = args.graph_name
            self.schema = linkml_schema(
                self.graph_name, args.graph_title, args.graph_description
            )

        schema_annotations = get_schema_annotations(self.schema)
        schema_annotations["URIs_in_ontologies"] = Annotation(tag="URIs_in_ontologies", value=uri_mappings.URIs_in_ontologies)
        schema_annotations["domain_range_keys_to_uris"] = Annotation(tag="domain_range_keys_to_uris", value={})
        schema_annotations["void_partition_order"] = Annotation(tag="void_partition_order", value=args.void_partition_order.split(','))
        self.subclass_tree = uri_mappings.subclass_tree

        self.counts = VoidDataset()
        self.restrictions: defaultdict[Node, dict[str, Any]] = defaultdict(dict)
        self.entities_without_type: set[Node] = set()
        self.entities_without_type_count = 0
        self.multiple_typed_object_counts: defaultdict[frozenset[Node], int] = (
            defaultdict(int)
        )

        if self.args.type_index_size:
            self.get_entity_types = lru_cache(maxsize=self.args.type_index_size)(self.get_entity_types_uncached)
        else:
            self.entity_types_index: defaultdict[Node, set[Node]] = defaultdict(set)
            # Optimization: Pre-build indexes immediately
            self._build_indexes()
            self.get_entity_types = lambda x: self.entity_types_index.get(x, set())

    def get_entity_types_uncached(self, entity: Node) -> set[Node]:
        """Finds types for a given entity in the graph."""
        return {o for o in self.g.objects(subject=entity, predicate=RDF.type)}

    def find_shortest_path_helper(
        self, start: str, end: str, path: tuple[str, ...] = ()
    ) -> tuple[str, ...]:
        # Optimization: Use tuple for path (immutable)
        path = path + (start,)
        if start == end:
            return path
        if start not in self.subclass_tree:
            return ()
        shortest: tuple[str, ...] = ()
        # Copy to list to avoid runtime modification issues during recursion
        for node in list(self.subclass_tree[start]):
            if node not in path:
                newpath = self.find_shortest_path_helper(node, end, path)
                if newpath:
                    if not shortest or len(newpath) < len(shortest):
                        shortest = newpath
        return shortest

    @lru_cache(maxsize=4096)
    def find_shortest_path(self, start: str, end: str) -> tuple[str, ...]:
        return self.find_shortest_path_helper(start, end)

    def _build_indexes(self) -> None:
        """Pre-build indexes for faster lookups"""
        print("Building indexes for faster processing...")

        # Iterate only RDF.type triples directly via generator
        for s, o in tqdm.tqdm(
            self.g.subject_objects(predicate=RDF.type), desc="Indexing types"
        ):
            self.entity_types_index[s].add(o)

        # Remove superclasses that inferred triples might have added
        if self.deduplicate_types:
            for s, subject_types in self.entity_types_index.items():
                subject_types_initial = [
                    (st, *(self.produce_curie_key(st))) for st in list(subject_types)
                ]
                for st, stc, stk, _ in subject_types_initial:
                    if any(
                        (self.find_shortest_path(stk, other_stk) != ())
                        for other_st, other_stc, other_stk, _ in subject_types_initial
                        if other_st != st
                    ):
                        self.entity_types_index[s].remove(st)

        print(f"Indexed {len(self.entity_types_index)} entities with types")

    def add_str_to_multiple(
        self, obj_in: Element, pred: Node, string_to_store: str
    ) -> None:
        current_slot, current_datatype = SLOTS_TO_PREDICATES_MULTIPLE_STR[pred]
        if value_is_valid(string_to_store, current_datatype, pred, obj_in["name"]):
            if current_slot == "exact_mappings":
                current_curie, _, _ = self.replace_prefixes(string_to_store)
                if current_curie in {
                    obj_in.get(k, "") for k in ["class_uri", "slot_uri", "uri"]
                }:
                    return

            if not isinstance(getattr(obj_in, current_slot), list):
                setattr(obj_in, current_slot, [])
            obj_list = getattr(obj_in, current_slot)
            if string_to_store not in obj_list:
                obj_list.append(string_to_store.strip())

    def replace_prefixes(self, node: str) -> tuple[str, str, str]:
        replaced, replacement, prefix = find_prefix(node)
        if replacement != "":
            if self.schema.prefixes is None:
                self.schema.prefixes = {}
            elif isinstance(self.schema.prefixes, list):
                self.schema.prefixes = convert_prefixes_to_dict(self.schema.prefixes)
            self.schema.prefixes[replacement] = Prefix(
                prefix_prefix=replacement, prefix_reference=str(prefix)
            )
        return replaced, replacement, prefix

    @lru_cache(maxsize=100000)
    def produce_curie_key(self, uri: URIRef) -> tuple[str, str, str]:
        """Generates a CURIE and a safe key from a URI.

        Cached to avoid re-parsing strings and regex overhead.
        """
        uri_str = str(uri)
        output_curie, _, output_prefix = self.replace_prefixes(uri_str)
        output_key = output_curie.replace(":", "_").replace("/", "_")
        return output_curie, output_key, output_prefix

    def process_restrictions(self) -> None:
        # Optimization: Generator based iteration
        for entity, _, _ in tqdm.tqdm(
            self.g.triples((None, RDF.type, OWL.Restriction)), desc="Restrictions"
        ):
            target_properties = set(self.g.objects(entity, OWL.onProperty))
            # Target classes logic omitted for brevity/speed unless explicitly needed

            for subj, pred, obj in self.g.triples((entity, None, None)):
                if pred in SINGLE_VALUE_RESTRICTIONS:
                    for target_property in target_properties:
                        self.restrictions[target_property][
                            SINGLE_VALUE_RESTRICTIONS[pred]
                        ] = obj

    def process_ontologies(self) -> None:
        for entity in tqdm.tqdm(
            self.g.subjects(RDF.type, OWL.Ontology), desc="Ontologies"
        ):
            for subj, pred, obj in self.g.triples((entity, None, None)):
                string_to_store = str(obj).replace("\n", "␊")
                if pred in SLOTS_TO_PREDICATES_SINGLE:
                    add_str_to_single(self.schema, pred, string_to_store)
                elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                    self.add_str_to_multiple(self.schema, pred, string_to_store)
                elif pred in SLOTS_TO_PREDICATES_SINGLE_ONTOLOGY:
                    add_str_to_single(
                        self.schema,
                        pred,
                        string_to_store,
                        SLOTS_TO_PREDICATES_SINGLE_ONTOLOGY,
                    )

    def add_class(
        self,
        subj_key: str,
        subj_uri: str | None = None,
        subj_title: str | None = None,
        extra_info: dict[str, Any] | None = None,
        from_schema: str | None = None,
    ) -> None:
        if self.schema.classes is None:
            raise ValueError("No classes in newly created schema?")
        if isinstance(self.schema.classes, list):
            target = ClassDefinition(name=subj_key)
            self.schema.classes.append(target)
        else:
            try:
                target_possible = self.schema.classes[subj_key]
            except KeyError:
                target = ClassDefinition(name=subj_key)
                self.schema.classes[subj_key] = target
            else:
                if isinstance(target_possible, dict):
                    target = ClassDefinition(**target_possible)
                else:
                    target = target_possible
                target.name = subj_key

        if subj_uri:
            target.class_uri = str(subj_uri)
        if from_schema:
            target.from_schema = from_schema
            target.title = None
            target.description = None
            return
        if subj_title:
            target.title = subj_title
        if extra_info:
            target.update(extra_info)

    def add_type(
        self,
        subj_type: Node,
        subj_key: str,
        subj_uri: str | None = None,
        subj_title: str | None = None,
        extra_info: dict[str, Any] | None = None,
        from_schema: str | None = None,
    ) -> None:
        if subj_type in datatype_to_type:
            return

        if self.schema.types is None:
            raise ValueError("No types in newly created schema?")
        if isinstance(self.schema.types, list):
            target = TypeDefinition(name=subj_key)
            self.schema.types.append(target)
        else:
            try:
                target_possible = self.schema.types[subj_key]
            except KeyError:
                target = TypeDefinition(name=subj_key)
                self.schema.types[subj_key] = target
            else:
                if isinstance(target_possible, dict):
                    target = TypeDefinition(**target_possible)
                else:
                    target = target_possible
                target.name = subj_key

        if subj_uri:
            target.uri = str(subj_uri)
        if from_schema:
            target.from_schema = from_schema
            target.imported_from = from_schema
            target.title = None
            target.description = None
            return
        if subj_title:
            target.title = subj_title
        if extra_info:
            target.update(extra_info)

    def add_slot(
        self,
        subj_key: str,
        subj_uri: str | Node | None = None,
        subj_title: str | None = None,
        extra_info: dict[str, Any] | None = None,
        from_schema: str | None = None,
    ) -> None:
        if self.schema.slots is None:
            raise ValueError("No slots in newly created schema?")
        if isinstance(self.schema.slots, list):
            target = SlotDefinition(name=subj_key)
            self.schema.slots.append(target)
        else:
            try:
                target_possible = self.schema.slots[subj_key]
            except KeyError:
                target = SlotDefinition(name=subj_key)
                self.schema.slots[subj_key] = target
            else:
                if isinstance(target_possible, dict):
                    target = SlotDefinition(**target_possible)
                else:
                    target = target_possible
                target.name = subj_key

        if subj_uri:
            target.slot_uri = str(subj_uri)
        if from_schema:
            target.from_schema = from_schema
            target.imported_from = from_schema
            target.title = None
            target.description = None
            return
        if subj_title:
            target.title = subj_title
        if extra_info:
            target.update(extra_info)

    def process_classes(self) -> None:
        schema_annotations = get_schema_annotations(self.schema)
        schema_classes = get_schema_classes(self.schema)
        for class_type, extra_info in CLASS_TYPES.items():
            # Optimization: Use generator directly
            for entity in tqdm.tqdm(
                self.g.subjects(RDF.type, class_type), desc=f"Classes {class_type}"
            ):
                if entity in datatype_to_type:
                    continue
                if isinstance(entity, BNode) or str(entity).startswith("_:"):
                    continue

                # Check restriction manually since we are iterating subjects
                if (entity, RDF.type, OWL.Restriction) in self.g:
                    continue

                subj_uri, subj_key, _ = self.produce_curie_key(entity)
                if subj_uri in schema_annotations["URIs_in_ontologies"].value:
                    continue

                if subj_key in schema_classes:
                    cls = schema_classes[subj_key]
                    if "title" in cls and "but not defined" not in cls["title"]:
                        if "deprecated" in cls and "deprecated" in extra_info:
                            cls.update({**extra_info, "deprecated": cls["deprecated"]})
                        else:
                            cls.update(extra_info)
                    continue

                self.add_class(subj_key, subj_uri, extra_info=extra_info)

                for _, pred, obj in self.g.triples((entity, None, None)):
                    obj_uri, obj_key, _ = self.produce_curie_key(obj)

                    if pred in SLOTS_TO_PREDICATES_SINGLE:
                        add_str_to_single(schema_classes[subj_key], pred, str(obj))
                    elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                        self.add_str_to_multiple(
                            schema_classes[subj_key], pred, str(obj)
                        )
                    elif pred in {RDFS.subClassOf}:
                        if isinstance(obj, BNode) or str(obj).startswith("_:"):
                            continue
                        if obj_key != subj_key:
                            if not check_for_cycles(
                                self.subclass_tree, subj_key, obj_key
                            ):
                                self.subclass_tree[obj_key].add(subj_key)
                            try:
                                self.check_for_import(obj_uri)
                            except KeyError:
                                pass
                            schema_classes[subj_key].is_a = obj_key
                        if (obj_key not in schema_classes) and (
                            obj_uri not in schema_annotations["URIs_in_ontologies"].value
                        ):
                            self.add_class(
                                obj_key,
                                obj_uri,
                                "No class name specified -- this class is noted as a superclass but not defined.",
                            )

    def type_previously_defined(self, subj_key: str) -> bool:
        schema_types = get_schema_types(self.schema)
        if subj_key in schema_types:
            current_type = schema_types[subj_key]
            if (
                current_type.title is not None
                and "but not defined" not in current_type.title
            ):
                return True
        return False

    def process_types(self) -> None:
        schema_annotations = get_schema_annotations(self.schema)
        schema_types = get_schema_types(self.schema)
        for class_type, extra_info in TYPE_TYPES.items():
            for entity in tqdm.tqdm(
                self.g.subjects(RDF.type, class_type), desc=f"Types {class_type}"
            ):
                if (entity, RDF.type, OWL.Restriction) in self.g:
                    continue
                if isinstance(entity, BNode) or str(entity).startswith("_:"):
                    continue

                subj_uri, subj_key, _ = self.produce_curie_key(entity)

                if self.type_previously_defined(subj_key):
                    continue
                if entity in datatype_to_type:
                    continue
                if subj_uri in schema_annotations["URIs_in_ontologies"].value:
                    continue

                self.add_type(entity, subj_key, subj_uri, extra_info=extra_info)

                for _, pred, obj in self.g.triples((entity, None, None)):
                    obj_uri, obj_key, _ = self.produce_curie_key(obj)

                    if pred in SLOTS_TO_PREDICATES_SINGLE:
                        add_str_to_single(schema_types[subj_key], pred, str(obj))
                    elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                        self.add_str_to_multiple(schema_types[subj_key], pred, str(obj))
                    elif pred in {RDFS.subClassOf}:
                        if isinstance(obj, BNode) or str(obj).startswith("_:"):
                            continue
                        if obj_key != subj_key:
                            if not check_for_cycles(
                                self.subclass_tree, subj_key, obj_key
                            ):
                                self.subclass_tree[obj_key].add(subj_key)
                            try:
                                self.check_for_import(obj_uri)
                            except KeyError:
                                pass

                            current_typeof = "string"
                            try:
                                _, _, target_type = schema_annotations["URIs_in_ontologies"].value[obj_uri]
                            except KeyError:
                                target_type = "class"
                            if obj == RDFS.Literal:
                                current_typeof = "string"
                            elif target_type != "slot":
                                current_typeof = "string"
                            else:
                                current_typeof = obj_key
                            schema_types[subj_key].typeof = current_typeof

                        if (obj_key not in schema_types) and (
                            obj_uri not in schema_annotations["URIs_in_ontologies"].value
                        ):
                            self.add_class(
                                obj_key,
                                obj_uri,
                                "No type name specified -- noted as supertype but not defined.",
                            )

    def slot_previously_defined(self, subj_key: str) -> bool:
        schema_slots = get_schema_slots(self.schema)
        if subj_key in schema_slots:
            current_slot = schema_slots[subj_key]
            if (current_slot.title is not None) and (
                "but not defined" not in current_slot.title
            ):
                return True
        return False

    def add_import(self, current_import: str) -> None:
        if self.schema.imports is None:
            self.schema.imports = []
        elif isinstance(self.schema.imports, (str, URIorCURIE)):
            self.schema.imports = [self.schema.imports]
        if current_import not in self.schema.imports:
            self.schema.imports.append(current_import)

    def update_prefixes(self, current_prefixes: dict[str, str]) -> None:
        if self.schema.prefixes is None:
            self.schema.prefixes = {}
        elif isinstance(self.schema.prefixes, list):
            self.schema.prefixes = convert_prefixes_to_dict(self.schema.prefixes)
        for replacement, prefix in current_prefixes.items():
            self.schema.prefixes[replacement] = Prefix(
                prefix_prefix=replacement, prefix_reference=str(prefix)
            )

    def process_slots(self) -> None:
        schema_annotations = get_schema_annotations(self.schema)
        schema_slots = get_schema_slots(self.schema)
        for slot_type, extra_info in SLOT_TYPES.items():
            for entity in tqdm.tqdm(
                self.g.subjects(RDF.type, slot_type),
                desc=f"Predicates ({slot_type})",
            ):
                subj_curie_key = self.produce_curie_key(entity)
                subj_uri, subj_key, _ = subj_curie_key

                if (entity, RDF.type, OWL.Restriction) in self.g:
                    continue
                if entity in datatype_to_type:
                    continue
                if subj_uri in schema_annotations["URIs_in_ontologies"].value:
                    continue
                if str(entity).startswith(str(RDF) + "_"):
                    continue

                if self.slot_previously_defined(subj_key):
                    continue

                self.add_slot(subj_key, subj_uri, extra_info=extra_info)

                for _, pred, obj in self.g.triples((entity, None, None)):
                    obj_curie_key = self.produce_curie_key(obj)
                    obj_uri, obj_key, _ = obj_curie_key

                    if pred in SLOTS_TO_PREDICATES_SINGLE:
                        add_str_to_single(schema_slots[subj_key], pred, str(obj))
                    elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                        self.add_str_to_multiple(schema_slots[subj_key], pred, str(obj))
                    elif pred in {RDFS.domain, SDO.domainIncludes}:
                        if isinstance(obj, BNode) or str(obj).startswith("_:"):
                            continue
                        normalized_type, current_import, current_prefixes = (
                            linkml_type_mapping(obj)
                        )
                        if normalized_type != obj:
                            self.add_import(current_import)
                            self.update_prefixes(current_prefixes)
                            obj_curie_key = self.produce_curie_key(normalized_type)
                        self.add_to_domain(subj_curie_key, obj_curie_key)
                    elif pred in {RDFS.range, SDO.rangeIncludes}:
                        if isinstance(obj, BNode) or str(obj).startswith("_:"):
                            continue
                        normalized_type, current_import, current_prefixes = (
                            linkml_type_mapping(obj)
                        )
                        if normalized_type != obj:
                            self.add_import(current_import)
                            self.update_prefixes(current_prefixes)
                            obj_curie_key = self.produce_curie_key(normalized_type)
                        add_to_range(self.schema, subj_curie_key, obj_curie_key)
                    elif pred in {OWL.inverseOf, SDO.inverseOf}:
                        schema_slots[subj_key].inverse = obj_key
                    elif pred in {RDFS.subPropertyOf}:
                        if subj_key != obj_key:
                            try:
                                self.check_for_import(obj_uri)
                            except KeyError:
                                pass
                            schema_slots[subj_key].subproperty_of = obj_key
                        if (obj_key not in schema_slots) and (
                            obj_uri not in schema_annotations["URIs_in_ontologies"].value
                        ):
                            self.add_slot(
                                obj_key,
                                obj_uri,
                                "No slot name specified -- noted as subproperty but not defined.",
                            )

    def check_for_import(self, type_uri: str) -> tuple[Element, str]:
        schema_annotations = get_schema_annotations(self.schema)
        target_ontology, target_entity, _ = schema_annotations["URIs_in_ontologies"].value[type_uri]
        self.add_import(target_ontology)
        return target_entity, target_ontology

    def check_for_missing_domain_range_type(self, set_type_key: str) -> None:
        schema_annotations = get_schema_annotations(self.schema)
        schema_classes = get_schema_classes(self.schema)
        schema_types = get_schema_types(self.schema)

        if set_type_key not in schema_classes and set_type_key not in schema_types:
            try:
                set_type_uri = schema_annotations["domain_range_keys_to_uris"].value[set_type_key]
            except KeyError:
                pass
            else:
                try:
                    self.check_for_import(set_type_uri)
                except KeyError:
                    if set_type_key not in linkml_type_names:
                        self.add_class(
                            set_type_key,
                            set_type_uri,
                            "No class name specified -- noted in domain/range but not defined.",
                        )

    def add_missing_domain_range_types(self) -> None:
        schema_slots = get_schema_slots(self.schema)
        for _, slot in schema_slots.items():
            if slot.union_of is None:
                slot.union_of = []
            elif isinstance(slot.union_of, (str, SlotDefinitionName)):
                slot.union_of = [slot.union_of]
            if len(slot.union_of) == 0:
                if slot.domain == "Any":
                    self.add_import(extended_types_url)
            for union_set_type_key in slot.union_of:
                self.check_for_missing_domain_range_type(union_set_type_key)

            if slot.range == "Any":
                self.add_import(extended_types_url)
            if slot.any_of is None:
                slot.any_of = []
            elif isinstance(slot.any_of, (dict, AnonymousSlotExpression)):
                slot.any_of = [slot.any_of]
            for any_set_type_curie_key in slot.any_of:
                if isinstance(any_set_type_curie_key, dict):
                    self.check_for_missing_domain_range_type(
                        any_set_type_curie_key["range"]
                    )
                elif any_set_type_curie_key.range is not None:
                    self.check_for_missing_domain_range_type(
                        any_set_type_curie_key.range
                    )

    # Included to ensure dependency closure
    def add_to_domain(
        self, pred_curie_key: tuple[str, str, str], obj_curie_key: tuple[str, str, str]
    ) -> None:
        schema_annotations = get_schema_annotations(self.schema)
        schema_slots = get_schema_slots(self.schema)
        _, pred_key, _ = pred_curie_key
        obj_uri, obj_key, _ = obj_curie_key
        schema_annotations["domain_range_keys_to_uris"].value[obj_key] = obj_uri
        current_slot = schema_slots[pred_key]
        if current_slot.union_of is None:
            current_slot.union_of = []
        elif isinstance(current_slot.union_of, (str, SlotDefinitionName)):
            current_slot.union_of = [current_slot.union_of]
        if obj_key not in current_slot.union_of:
            current_slot.union_of.append(obj_key)

    def process_counts(self) -> None:
        """Actually counts triples in the graph.

        Triples pertaining to a restriction, ontology, class, datatype, or property are excluded.

        All triples are iterated linearly, meaning only one pass over the graph is taken.
        """
        print("Processing triples (Linear Scan Optimization)...")

        produce_curie_key = self.produce_curie_key
        schema_annotations = get_schema_annotations(self.schema)
        schema_classes = get_schema_classes(self.schema)
        schema_slots = get_schema_slots(self.schema)
        schema_types = get_schema_types(self.schema)

        skip_predicates = {RDF.type, RDF.first, RDF.rest}

        for triple in tqdm.tqdm(self.g, desc="Analyzing Triples"):
            s, p, o = triple
            # Skip anything related to RDF lists
            if p in skip_predicates:
                continue
            p_str = str(p)
            if p_str.startswith(str(RDF) + "_"):
                continue

            # 0. Break down triple
            s_curie_key = produce_curie_key(s)
            p_curie_key = produce_curie_key(p)
            p_curie, p_key, _ = p_curie_key
            o_curie_key = produce_curie_key(o)

            # 1. Identify Subject Types from Index
            s_types_raw = self.get_entity_types(s)

            subject_type_uris_keys: list[tuple[str | None, str, str]] = []
            subject_types_filtered: set[Node] = set()

            if len(s_types_raw) > 0:
                for st in list(s_types_raw):
                    if (
                        st in CLASS_TYPES
                        or st in SLOT_TYPES
                        or st == OWL.NamedIndividual
                    ):
                        continue
                    subject_type_uris_keys.append(produce_curie_key(st))
                    subject_types_filtered.add(st)

            has_types = len(subject_types_filtered) > 0

            if not has_types and self.list_untyped_entities:
                self.entities_without_type.add(s)

            if len(subject_types_filtered) > 1:
                self.multiple_typed_object_counts[
                    frozenset(subject_types_filtered)
                ] += 1
            elif len(subject_types_filtered) == 0:
                self.entities_without_type_count += 1

            # 2. Process Predicate
            try:
                self.check_for_import(p_curie)
            except KeyError:
                if p_key not in schema_slots:
                    self.add_slot(p_key)
                schema_slots[p_key].slot_uri = str(p_curie)

            # 3. Identify Object Type
            object_type_uris_keys: list[tuple[str | None, str, str]] = []

            if isinstance(o, (URIRef, BNode)):
                o_types_raw = self.get_entity_types(o)
                if len(o_types_raw) > 0:
                    for ot in list(o_types_raw):
                        if ot in CLASS_TYPES or ot in SLOT_TYPES:
                            continue
                        object_type_uris_keys.append(produce_curie_key(ot))
            else:
                object_datatype = get_object_datatype(o)
                object_type_mapping, current_import, _ = linkml_type_mapping(
                    object_datatype
                )
                if current_import:
                    self.add_import(current_import)

                dt_curie_key = produce_curie_key(object_type_mapping)
                dt_curie, dt_key, _ = dt_curie_key
                object_type_uris_keys.append(dt_curie_key)

                if (
                    dt_key not in schema_types
                    and dt_curie not in schema_annotations["URIs_in_ontologies"].value
                ):
                    self.add_type(object_datatype, dt_key, dt_curie)

            if len(subject_type_uris_keys) == 0:
                subject_type_uris_keys.append((None, "untyped", ""))
            if len(object_type_uris_keys) == 0:
                object_type_uris_keys.append((None, "untyped", ""))

            # 4. Update Schema Stats (The Cross Product)
            if has_types:
                for st_curie_key in subject_type_uris_keys:
                    st_curie_new, st_key_new, _ = st_curie_key
                    # Ensure class exists
                    # TODO: move this block someplace else?
                    if st_curie_new not in schema_annotations["URIs_in_ontologies"].value:
                        if st_key_new not in schema_classes:
                            self.add_class(st_key_new, st_curie_new)
                        current_class = schema_classes[st_key_new]
                        if current_class.slots is None:
                            current_class.slots = []
                        elif isinstance(current_class.slots, (str, SlotDefinitionName)):
                            current_class.slots = [current_class.slots]
                        if p_key not in current_class.slots:
                            current_class.slots.append(p_key)

            account_for_triple(
                self.schema, self.counts, triple, (s_curie_key, p_curie_key, o_curie_key), subject_type_uris_keys, object_type_uris_keys
            )

    def clean_up_json(self) -> None:
        update_time = f"{datetime.datetime.now().isoformat()}"
        if self.schema.created_on is None:
            self.schema.created_on = update_time
        if self.schema.last_updated_on is None:
            self.schema.last_updated_on = update_time

        schema_annotations = get_schema_annotations(self.schema)
        if not self.generate_base_schemas:
            schema_annotations["counts"] = Annotation(
                tag="counts",
                value = self.counts.__jsonout__()
            )
        del schema_annotations["URIs_in_ontologies"]
        del schema_annotations["domain_range_keys_to_uris"]
        del schema_annotations["void_partition_order"]

    def export_schema(self) -> None:
        yaml_file_basename = self.graph_name.replace("/", "__")
        output_file_path = os.path.join(self.output_path, yaml_file_basename + ".yaml")

        yaml_dumper.dump(self.schema, output_file_path)

    def export_untyped_entities(self) -> None:
        yaml_file_basename = self.graph_name.replace("/", "__")
        output_file_path = os.path.join(
            self.output_path, yaml_file_basename + "_untyped.txt"
        )

        with open(output_file_path, "w") as f:
            f.writelines(str(e) + "\n" for e in self.entities_without_type)

    def characterize(self) -> None:
        if self.args.process_ontologies:
            self.process_restrictions()
            self.process_ontologies()
            self.process_classes()
            self.process_types()
            self.process_slots()

        if self.args.process_counts:
            self.process_counts()

        self.add_missing_domain_range_types()

        self.clean_up_json()

        self.export_schema()

        if self.list_untyped_entities:
            self.export_untyped_entities()
        else:
            print("Found", self.entities_without_type_count, "untyped entities")


if __name__ == "__main__":
    # Reads the graphs...
    parser = argparse.ArgumentParser(
        prog="LinkML Schema Generator",
        description="Produces LinkML schemas from RDF data",
    )

    parser.add_argument("graph_name")
    parser.add_argument("graph_to_read")
    parser.add_argument("graph_title", nargs="?", default=None)
    parser.add_argument(
        "--graph_description", help="(Short) description of the graph.", default=None
    )
    parser.add_argument(
        "--formatter-url-list",
        help="Location of TSV results from running a query (https://w.wiki/Ff7j) of different formatter URLs and their origins.",
        default=".",
    )
    parser.add_argument(
        "--list-untyped-entities",
        action="store_true",
        help="Provides a list of untyped subject entities in the graph.",
    )
    parser.add_argument(
        "--output-path",
        default=".",
        help="Path into which any outputs from the characterization (schemas, untyped entity lists, etc.) should be saved.",
    )
    parser.add_argument(
        "--generate-base-schemas",
        type=int,
        help="Of the ontologies listed in external_ontologies.py, which (1-indexed) to generate while leaving the others above it intact.",
    )
    parser.add_argument(
        "--okn-registry-id", help="Name of the graph in the OKN registry."
    )
    parser.add_argument(
        "--external-ontology-path",
        help='Path to where external ontologies are stored: the prefix "https://purl.org/okn/schema/" will be substituted with the value of this argument.',
    )
    parser.add_argument(
        "--old-schema-path",
        help="Path to a schema representing an older version of the graph, from which general metadata about it will be retrieved.",
    )
    parser.add_argument(
        "--process-counts",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Assembles exhaustive counts of occurrences of particular entity types and predicates.",
    )
    parser.add_argument(
        "--process-ontologies",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Processes ontologies, classes, types, slots, (and restrictions) present in the data.",
    )
    parser.add_argument(
        "--void-partition-order",
        default="void:classPartition,void:propertyPartition,voidext:objectClassPartition",
        help="Partitions to be used for separating triple counts.",
    )
    parser.add_argument(
        "--deduplicate-types",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="If an entity has both a class and one of its superclasses as types, disregard the superclass for statistical purposes.",
    )
    parser.add_argument(
        "--type-index-size",
        type=int,
        help="Size of the index of entity types. If not specified, all entity types are computed and cached; otherwise types will be obtained on the fly.",
    )

    args = parser.parse_args()
    if args.generate_base_schemas is not None:
        external_ontologies_list = list(external_ontologies_dict.items())
        source = dict(external_ontologies_list[: args.generate_base_schemas])
    else:
        source = external_ontologies_dict
    formatter_urls = get_formatter_urls(args.formatter_url_list)
    uri_mappings = load_external_ontologies(
        source,
        args.external_ontology_path,
    )

    GraphCharacterizer(args, uri_mappings).characterize()
