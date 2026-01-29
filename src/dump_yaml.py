import argparse
import datetime
import json
import logging
import os
from collections import defaultdict
from functools import lru_cache
from itertools import chain

import rdflib
import rdflib.exceptions
import tqdm
import yaml
from rdflib import BNode, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SDO
from rdflib_hdt import HDTStore

# Assumes these are available from your original environment
from common_functions import (
    check_for_cycles,
    find_prefix,
    get_object_datatype,
    value_is_valid,
)
from external_ontologies import external_ontologies_dict, load_external_ontologies
from formatter_url_parsing import get_formatter_urls
from linkml_structures import linkml_schema
from predicate_mappings import (
    CLASS_TYPES,
    METADATA_TYPES,
    SINGLE_VALUE_RESTRICTIONS,
    SLOT_TYPES,
    SLOTS_TO_PREDICATES_MULTIPLE_STR,
    SLOTS_TO_PREDICATES_SINGLE,
    SLOTS_TO_PREDICATES_SINGLE_ONTOLOGY,
    TYPE_TYPES,
    datatype_to_type,
    extended_types_url,
    linkml_type_mapping,
    linkml_type_names,
)
from registry_processing import read_from_registry, schema_from_existing

# --- Global State ---
formatter_urls = None


def get_graph(graph_to_read):
    """
    Reads in a set of TTL/RDF files.
    Optimization: explicit check for oxrdflib for speed.
    """
    g = rdflib.Graph(store="Oxigraph")

    try:
        import oxrdflib

        logging.info("oxrdflib detected. Parsing will be significantly faster.")
    except ImportError:
        logging.info("oxrdflib not found. Using standard rdflib parser.")

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
                    logging.warning(f"Unable to read {current_file_path}")

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


def add_str_to_single(obj_in, pred, string_to_store, source_mapping=None):
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
            obj_in.setdefault("comments", defaultdict(set))[current_slot].add(
                string_to_store.strip()
            )
    else:
        obj_in.setdefault("comments", defaultdict(set))[current_slot].add(
            string_to_store.strip()
        )


def convert_annotations(annotations):
    if not isinstance(annotations, dict):
        return annotations
    return {
        k: {"tag": k, "value": convert_annotations(v)} for k, v in annotations.items()
    }


class GraphCharacterizer:
    def __init__(self, args, uri_mappings):
        self.args = args
        self.URIs_to_entities = uri_mappings["URIs_to_entities"]
        self.URI_entity_types = uri_mappings["URI_entity_types"]
        self.URIs_to_ontologies = uri_mappings["URIs_to_ontologies"]
        self.subclass_tree = uri_mappings["subclass_tree"]

        self.g = get_graph(args.graph_to_read)
        self.list_untyped_entities = args.list_untyped_entities

        if args.okn_registry_id:
            self.schema = read_from_registry(args.okn_registry_id)
            self.graph_name = self.schema["name"]
        elif args.old_schema_path:
            self.schema = schema_from_existing(args.old_schema_path)
            self.graph_name = self.schema["name"]
        else:
            self.graph_name = args.graph_name
            self.schema = linkml_schema(
                self.graph_name, args.graph_title, args.graph_description
            )

        self.restrictions = defaultdict(dict)
        self.entities_without_type = set()
        self.entities_without_type_count = 0
        self.multiple_typed_object_counts = defaultdict(int)
        self.type_uris_found = defaultdict(set)
        self.object_uris_found = defaultdict(set)
        self.formatter_urls_found = defaultdict(int)

        self.parsed_uris = {}

        # Optimization: Pre-build indexes immediately
        self._build_indexes()

    def find_shortest_path_helper(self, start, end, path=()):
        # Optimization: Use tuple for path (immutable)
        path = path + (start,)
        if start == end:
            return path
        if start not in self.subclass_tree:
            return None
        shortest = None
        # Copy to list to avoid runtime modification issues during recursion
        for node in list(self.subclass_tree[start]):
            if node not in path:
                newpath = self.find_shortest_path_helper(node, end, path)
                if newpath:
                    if not shortest or len(newpath) < len(shortest):
                        shortest = newpath
        return shortest

    @lru_cache(maxsize=4096)
    def find_shortest_path(self, start, end):
        return self.find_shortest_path_helper(start, end)

    def _build_indexes(self):
        """Pre-build indexes for faster lookups"""
        print("Building indexes for faster processing...")
        self.entity_types_index = defaultdict(set)

        # Iterate only RDF.type triples directly via generator
        for s, o in tqdm.tqdm(
            self.g.subject_objects(predicate=RDF.type), desc="Indexing types"
        ):
            self.entity_types_index[s].add(o)

        # Remove superclasses that inferred triples might have added
        for s, subject_types in self.entity_types_index.items():
            subject_types_initial = [
                (st, *(self.produce_curie_key(st))) for st in list(subject_types)
            ]
            for st, stc, stk in subject_types_initial:
                if any(
                    self.find_shortest_path(stk, other_stk)
                    for other_st, other_stc, other_stk in subject_types_initial
                    if other_st != st
                ):
                    self.entity_types_index[s].remove(st)

        print(f"Indexed {len(self.entity_types_index)} entities with types")

    def add_str_to_multiple(self, obj_in, pred, string_to_store):
        current_slot, current_datatype = SLOTS_TO_PREDICATES_MULTIPLE_STR[pred]
        if value_is_valid(string_to_store, current_datatype, pred, obj_in["name"]):
            if current_slot == "exact_mappings":
                current_curie = self.replace_prefixes(string_to_store)
                if current_curie in {
                    obj_in.get(k, "") for k in ["class_uri", "slot_uri", "uri"]
                }:
                    return

            obj_list = obj_in.setdefault(current_slot, [])
            if string_to_store not in obj_list:
                obj_list.append(string_to_store.strip())

    def replace_prefixes(self, node):
        node, replacement, prefix = find_prefix(node)
        if replacement != "":
            self.schema["prefixes"][replacement] = str(prefix)
        return node

    @lru_cache(maxsize=100000)
    def produce_curie_key(self, uri):
        """
        Generates a CURIE and a safe key from a URI.
        Cached to avoid re-parsing strings and regex overhead.
        """
        uri_str = str(uri)
        output_curie = self.replace_prefixes(uri_str)
        output_key = output_curie.replace(":", "_").replace("/", "_")
        return output_curie, output_key

    def process_restrictions(self):
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

    def process_ontologies(self):
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
        subj_key,
        subj_uri=None,
        subj_title=None,
        extra_info=None,
        from_schema=None,
    ):
        target = self.schema["classes"][subj_key]
        target["name"] = subj_key
        if subj_uri:
            target["class_uri"] = str(subj_uri)
        if from_schema:
            target["from_schema"] = from_schema
            target.pop("title", None)
            target.pop("description", None)
            return
        if subj_title:
            target["title"] = subj_title
        if extra_info:
            target.update(extra_info)

    def add_type(
        self,
        subj_type,
        subj_key,
        subj_uri=None,
        subj_title=None,
        extra_info=None,
        from_schema=None,
    ):
        if subj_type in datatype_to_type:
            return
        target = self.schema["types"][subj_key]
        target["name"] = subj_key
        if subj_uri:
            target["uri"] = str(subj_uri)
        if from_schema:
            target["from_schema"] = from_schema
            target["imported_from"] = from_schema
            target.pop("title", None)
            target.pop("description", None)
            return
        if subj_title:
            target["title"] = subj_title
        if extra_info:
            target.update(extra_info)

    def add_slot(
        self,
        subj_key,
        subj_uri=None,
        subj_title=None,
        extra_info=None,
        from_schema=None,
    ):
        target = self.schema["slots"][subj_key]
        target["name"] = subj_key
        if subj_uri:
            target["slot_uri"] = str(subj_uri)
        if from_schema:
            target["from_schema"] = from_schema
            target["imported_from"] = from_schema
            target.pop("title", None)
            target.pop("description", None)
            return
        if subj_title:
            target["title"] = subj_title
        if extra_info:
            target.update(extra_info)

    def process_classes(self):
        for class_type, extra_info in CLASS_TYPES.items():
            # Optimization: Use generator directly
            for entity in tqdm.tqdm(
                self.g.subjects(RDF.type, class_type), desc=f"Classes {str(class_type)}"
            ):
                if entity in datatype_to_type:
                    continue
                if isinstance(entity, BNode) or str(entity).startswith("_:"):
                    continue

                # Check restriction manually since we are iterating subjects
                if (entity, RDF.type, OWL.Restriction) in self.g:
                    continue

                subj_uri, subj_key = self.produce_curie_key(entity)
                if subj_uri in self.URIs_to_ontologies:
                    continue

                if subj_key in self.schema["classes"]:
                    cls = self.schema["classes"][subj_key]
                    if (
                        "title" in cls
                        and "but has not itself been defined" not in cls["title"]
                    ):
                        if "deprecated" in cls and "deprecated" in extra_info:
                            cls.update({**extra_info, "deprecated": cls["deprecated"]})
                        else:
                            cls.update(extra_info)
                    continue

                self.add_class(subj_key, subj_uri, extra_info=extra_info)

                for _, pred, obj in self.g.triples((entity, None, None)):
                    obj_uri, obj_key = self.produce_curie_key(obj)

                    if pred in SLOTS_TO_PREDICATES_SINGLE:
                        add_str_to_single(
                            self.schema["classes"][subj_key], pred, str(obj)
                        )
                    elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                        self.add_str_to_multiple(
                            self.schema["classes"][subj_key], pred, str(obj)
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
                                self.check_for_import(
                                    obj_uri
                                )
                            except KeyError:
                                pass
                            self.schema["classes"][subj_key]["is_a"] = obj_key
                        if (obj_key not in self.schema["classes"]) and (
                            obj_uri not in self.URIs_to_ontologies
                        ):
                            self.add_class(
                                obj_key,
                                obj_uri,
                                "No class name specified -- this class is noted as a superclass but not defined.",
                            )

    def process_types(self):
        for class_type, extra_info in TYPE_TYPES.items():
            for entity in tqdm.tqdm(
                self.g.subjects(RDF.type, class_type), desc=f"Types {str(class_type)}"
            ):
                if (entity, RDF.type, OWL.Restriction) in self.g:
                    continue
                if isinstance(entity, BNode) or str(entity).startswith("_:"):
                    continue

                subj_uri, subj_key = self.produce_curie_key(entity)

                if subj_key in self.schema["types"] and (
                    "title" in self.schema["types"][subj_key]
                    and "but has not itself been defined"
                    not in self.schema["types"][subj_key]["title"]
                ):
                    continue
                if entity in datatype_to_type:
                    continue
                if subj_uri in self.URIs_to_ontologies:
                    continue

                self.add_type(entity, subj_key, subj_uri, extra_info=extra_info)

                for _, pred, obj in self.g.triples((entity, None, None)):
                    obj_uri, obj_key = self.produce_curie_key(obj)

                    if pred in SLOTS_TO_PREDICATES_SINGLE:
                        add_str_to_single(
                            self.schema["types"][subj_key], pred, str(obj)
                        )
                    elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                        self.add_str_to_multiple(
                            self.schema["types"][subj_key], pred, str(obj)
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

                            current_typeof = "string"
                            if obj == RDFS.Literal:
                                current_typeof = "string"
                            elif self.URI_entity_types.get(obj_uri, "class") != "slot":
                                current_typeof = "string"
                            else:
                                current_typeof = obj_key
                            self.schema["types"][subj_key]["typeof"] = current_typeof

                        if (obj_key not in self.schema["types"]) and (
                            obj_uri not in self.URIs_to_ontologies
                        ):
                            self.add_class(
                                obj_key,
                                obj_uri,
                                "No type name specified -- noted as supertype but not defined.",
                            )

    def process_slots(self):
        for slot_type, extra_info in SLOT_TYPES.items():
            for entity in tqdm.tqdm(
                self.g.subjects(RDF.type, slot_type),
                desc=f"Predicates ({str(slot_type)})",
            ):
                subj_curie_key = self.produce_curie_key(entity)
                subj_uri, subj_key = subj_curie_key

                if (entity, RDF.type, OWL.Restriction) in self.g:
                    continue
                if entity in datatype_to_type:
                    continue
                if subj_uri in self.URIs_to_ontologies:
                    continue
                if str(entity).startswith(str(RDF) + "_"):
                    continue

                if subj_key in self.schema["slots"] and (
                    "title" in self.schema["slots"][subj_key]
                    and "but has not itself been defined"
                    not in self.schema["slots"][subj_key]["title"]
                ):
                    continue

                self.add_slot(subj_key, subj_uri, extra_info=extra_info)

                for _, pred, obj in self.g.triples((entity, None, None)):
                    obj_curie_key = self.produce_curie_key(obj)
                    obj_uri, obj_key = obj_curie_key

                    if pred in SLOTS_TO_PREDICATES_SINGLE:
                        add_str_to_single(
                            self.schema["slots"][subj_key], pred, str(obj)
                        )
                    elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                        self.add_str_to_multiple(
                            self.schema["slots"][subj_key], pred, str(obj)
                        )
                    elif pred in {RDFS.domain, SDO.domainIncludes}:
                        if isinstance(obj, BNode) or str(obj).startswith("_:"):
                            continue
                        normalized_type, current_import, current_prefixes = (
                            linkml_type_mapping(obj)
                        )
                        if normalized_type != obj:
                            self.schema["imports"].add(current_import)
                            self.schema["prefixes"].update(current_prefixes)
                            obj_curie_key = self.produce_curie_key(normalized_type)
                        self.add_to_domain(subj_key, obj_curie_key[1])  # Pass key
                    elif pred in {RDFS.range, SDO.rangeIncludes}:
                        if isinstance(obj, BNode) or str(obj).startswith("_:"):
                            continue
                        normalized_type, current_import, current_prefixes = (
                            linkml_type_mapping(obj)
                        )
                        if normalized_type != obj:
                            self.schema["imports"].add(current_import)
                            self.schema["prefixes"].update(current_prefixes)
                            obj_curie_key = self.produce_curie_key(normalized_type)
                        self.add_to_range(subj_curie_key, obj_curie_key)
                    elif pred in {OWL.inverseOf, SDO.inverseOf}:
                        self.schema["slots"][subj_key]["inverse"] = obj_key
                    elif pred in {RDFS.subPropertyOf}:
                        if subj_key != obj_key:
                            try:
                                self.check_for_import(obj_uri)
                            except KeyError:
                                pass
                            self.schema["slots"][subj_key]["subproperty_of"] = obj_key
                        if (obj_key not in self.schema["slots"]) and (
                            obj_uri not in self.URIs_to_ontologies
                        ):
                            self.add_slot(
                                obj_key,
                                obj_uri,
                                "No slot name specified -- noted as subproperty but not defined.",
                            )

    def check_for_import(self, type_uri):
        target_ontology = self.URIs_to_ontologies[type_uri]
        self.schema["imports"].add(target_ontology)
        target_entity = self.URIs_to_entities.get(type_uri, "")
        return target_entity, target_ontology

    def check_for_missing_domain_range_type(self, set_type_curie_key):
        # The previous code called this with a tuple or list, unpacking logic needed
        if isinstance(set_type_curie_key, (list, tuple)):
            set_type_uri, set_type_key = set_type_curie_key
        else:
            # Fallback if only key passed
            set_type_key = set_type_curie_key
            set_type_uri = None

        if (
            set_type_key not in self.schema["classes"]
            and set_type_key not in self.schema["types"]
        ):
            if set_type_uri:
                try:
                    self.check_for_import(set_type_uri)
                except KeyError:
                    if set_type_key not in linkml_type_names:
                        self.add_class(
                            set_type_key,
                            set_type_uri,
                            "No class name specified -- noted in domain/range but not defined.",
                        )

    def add_missing_domain_range_types(self):
        for _, slot_dict in self.schema["slots"].items():
            if len(slot_dict["union_of"]) == 0:
                if "domain" in slot_dict and slot_dict["domain"] == "Any":
                    self.schema["imports"].add(extended_types_url)
            for set_type_curie_key in list(slot_dict["union_of"]):
                # Optimization: The logic for 'check_for_missing_domain_range_type' relies on URIs
                # stored in union_of. Check if they are keys or full tuples.
                # In add_to_domain we stored just keys.
                # If we only have keys, we can't look up URI imports effectively unless we scan map.
                # For now, passing key.
                self.check_for_missing_domain_range_type(set_type_curie_key)

            if slot_dict["range"] == "Any":
                self.schema["imports"].add(extended_types_url)
            for set_type_curie_key in list(slot_dict["any_of"]):
                self.check_for_missing_domain_range_type(set_type_curie_key)

    # Included to ensure dependency closure
    def add_to_domain(self, pred_key, obj_key):
        if obj_key not in self.schema["slots"][pred_key]["union_of"]:
            self.schema["slots"][pred_key]["union_of"].add(obj_key)

    def add_to_range(self, pred_curie_key, obj_curie_key):
        pred_uri, pred_key = pred_curie_key
        obj_uri, obj_key = obj_curie_key

        if pred_uri in self.URIs_to_ontologies:
            return

        if obj_key not in self.schema["slots"][pred_key]["any_of"]:
            self.schema["slots"][pred_key]["any_of"].add(obj_key)

    def increment_usage_count(self, subject_type_uri, pred_uri, object_type_uri):
        base = self.schema["annotations"]["counts"]["pairs"][pred_uri]
        st = subject_type_uri if subject_type_uri else "untyped"
        base[st][object_type_uri] += 1

    def add_example(self, subject_type_uri, pred_uri, object_type_uri, example):
        suri = subject_type_uri or "untyped"
        ouri = object_type_uri or "untyped"
        target = self.schema["annotations"]["examples"]["pairs"][pred_uri][suri]
        if not target.get(ouri):
            target[ouri] = {
                "subject": example[0],
                "predicate": example[1],
                "object": example[2],
            }

    def account_for_triple(
        self, subj_type_curie_key, pred_curie_key, obj_type_curie_key, example
    ):
        subj_type_uri = subj_type_curie_key[0] if subj_type_curie_key else None
        pred_uri = pred_curie_key[0]
        obj_type_uri = obj_type_curie_key[0]

        self.increment_usage_count(subj_type_uri, pred_uri, obj_type_uri)
        self.add_example(subj_type_uri, pred_uri, obj_type_uri, example)
        self.add_to_range(pred_curie_key, obj_type_curie_key)

    def add_missing_classes(self, subj_uri, object_types, object_type_uris_keys):
        if not any(obj in METADATA_TYPES for obj in list(object_types)):
            for obj_uri, obj_key in object_type_uris_keys:
                if (
                    obj_key not in self.schema["classes"]
                    and obj_uri not in self.URIs_to_ontologies
                ):
                    self.add_class(obj_key, obj_uri)
                    if obj_key not in self.schema["annotations"]["examples"]["classes"]:
                        self.schema["annotations"]["examples"]["classes"][obj_uri] = (
                            str(subj_uri)
                        )

    def process_counts(self):
        """
        MAJOR OPTIMIZATION:
        Instead of iterating subjects -> predicate_objects (N+1 queries),
        we iterate all triples linearly (1 pass).
        """
        print("Processing triples (Linear Scan Optimization)...")

        produce_curie_key = self.produce_curie_key
        types_index = self.entity_types_index
        schema_counts_slots = self.schema["annotations"]["counts"]["slots"]
        schema_classes = self.schema["classes"]

        skip_predicates = {RDF.type, RDF.first, RDF.rest}

        for s, p, o in tqdm.tqdm(self.g, desc="Analyzing Triples"):
            if p in skip_predicates:
                continue
            p_str = str(p)
            if p_str.startswith(str(RDF) + "_"):
                continue

            # 1. Identify Subject Types from Index
            s_types_raw = types_index.get(s, set())

            subject_type_uris_keys = []
            subject_types_filtered = set()

            if s_types_raw:
                for st in s_types_raw:
                    if (
                        st in CLASS_TYPES
                        or st in SLOT_TYPES
                        or st == OWL.NamedIndividual
                    ):
                        continue

                    st_curie, st_key = produce_curie_key(st)

                    self.schema["annotations"]["counts"]["classes"][st_curie] += 1
                    if (
                        st_curie
                        not in self.schema["annotations"]["examples"]["classes"]
                    ):
                        self.schema["annotations"]["examples"]["classes"][st_curie] = (
                            str(s)
                        )

                    subject_type_uris_keys.append((st_curie, st_key))
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
            p_curie, p_key = produce_curie_key(p)
            schema_counts_slots[p_curie] += 1

            try:
                target_entity, target_ontology = self.check_for_import(p_curie)
            except KeyError:
                self.schema['slots'][p_key]['slot_uri'] = str(p_curie)

            # 3. Identify Object Type
            object_type_uris_keys = []

            if isinstance(o, (URIRef, BNode)):
                o_types_raw = types_index.get(o, set())
                if o_types_raw:
                    for ot in o_types_raw:
                        if ot in CLASS_TYPES or ot in SLOT_TYPES:
                            continue
                        ot_curie, ot_key = produce_curie_key(ot)
                        object_type_uris_keys.append((ot_curie, ot_key))
            else:
                object_datatype = get_object_datatype(o)
                object_type_mapping, current_import, _ = linkml_type_mapping(
                    object_datatype
                )
                if current_import:
                    self.schema["imports"].add(current_import)

                dt_curie, dt_key = produce_curie_key(object_type_mapping)
                object_type_uris_keys.append((dt_curie, dt_key))

                if (
                    dt_key not in self.schema["types"]
                    and dt_curie not in self.URIs_to_ontologies
                ):
                    self.add_type(object_datatype, dt_key, dt_curie)

            # 4. Update Schema Stats (The Cross Product)
            example = (str(s), str(p), str(o))
            pred_curie_key = (p_curie, p_key)

            if has_types:
                for st_curie, st_key in subject_type_uris_keys:
                    # Ensure class exists
                    if st_curie not in self.URIs_to_ontologies:
                        if st_key not in schema_classes:
                            self.add_class(st_key, st_curie)
                        if "slots" not in schema_classes[st_key]:
                            schema_classes[st_key]["slots"] = []
                        if p_key not in schema_classes[st_key]["slots"]:
                            schema_classes[st_key]["slots"].add(p_key)

                    if object_type_uris_keys:
                        for ot_curie_key in object_type_uris_keys:
                            self.account_for_triple(
                                (st_curie, st_key),
                                pred_curie_key,
                                ot_curie_key,
                                example,
                            )
                    else:
                        self.account_for_triple(
                            (st_curie, st_key),
                            pred_curie_key,
                            (None, "untyped"),
                            example,
                        )

            else:
                if object_type_uris_keys:
                    for ot_curie_key in object_type_uris_keys:
                        self.account_for_triple(
                            None, pred_curie_key, ot_curie_key, example
                        )
                else:
                    self.account_for_triple(
                        None, pred_curie_key, (None, "untyped"), example
                    )

    def convert_class_dicts(self):
        for class_key, class_dict in chain(
            self.schema.get("classes",{}).items(), self.schema.get("types", {}).items()
        ):
            if "notes" in class_dict and len(class_dict["notes"]) == 0:
                del class_dict["notes"]
            if "slots" in class_dict:
                class_dict["slots"] = list(set(class_dict["slots"]))  # Dedupe
                if len(class_dict["slots"]) == 0:
                    del class_dict["slots"]

            if "description" in class_dict:
                class_dict["description"] = class_dict["description"].replace("\n", "␊")
            if class_dict["name"] == "":
                class_dict["name"] = class_key
            if "comments" in class_dict and len(class_dict["comments"]) > 0:
                class_dict["comments"] = [
                    (k + ": " + v)
                    for k in class_dict["comments"]
                    for v in list(class_dict["comments"][k])
                ]
            elif "comments" in class_dict:
                del class_dict["comments"]

    def convert_slot_dicts(self):
        for key, slot_dict in self.schema["slots"].items():
            slot_uri = slot_dict["slot_uri"]
            if "description" in slot_dict:
                slot_dict["description"] = slot_dict["description"].replace("\n", "␊")

            if self.schema["annotations"]["counts"]["slots"][slot_uri] == 0:
                if "notes" in slot_dict:
                    slot_dict["notes"].append(
                        "No occurrences of this slot in the graph."
                    )
                else:
                    slot_dict["notes"] = ["No occurrences of this slot in the graph."]
                del self.schema["annotations"]["counts"]["slots"][slot_uri]

            # Convert sets to lists of dicts for YAML output
            slot_dict["any_of"] = [
                {"range": typename[1] if isinstance(typename, tuple) else typename}
                for typename in list(slot_dict["any_of"])
            ]

            if len(slot_dict["any_of"]) == 1:
                slot_dict["range"] = slot_dict["any_of"][0]["range"]
                del slot_dict["any_of"]
            elif len(slot_dict["any_of"]) == 0:
                del slot_dict["any_of"]

            slot_dict["union_of"] = [
                typename for typename in list(slot_dict["union_of"])
            ]
            if len(slot_dict["union_of"]) == 1:
                slot_dict["domain"] = slot_dict["union_of"][0]
                del slot_dict["union_of"]
            elif len(slot_dict["union_of"]) == 0:
                del slot_dict["union_of"]

            if "notes" in slot_dict and len(slot_dict["notes"]) == 0:
                del slot_dict["notes"]
            if "comments" in slot_dict and len(slot_dict["comments"]) == 0:
                del slot_dict["comments"]
            elif "comments" in slot_dict:
                slot_dict["comments"] = [
                    (k + ": " + v)
                    for k in slot_dict["comments"]
                    for v in list(slot_dict["comments"][k])
                ]

    def clean_up_json(self):
        self.schema["classes"] = dict(self.schema["classes"])
        if "types" in self.schema:
            self.schema["types"] = dict(self.schema["types"])
            if len(self.schema["types"]) == 0:
                del self.schema["types"]
        self.schema["slots"] = dict(self.schema["slots"])
        self.schema["imports"] = list(self.schema["imports"])
        self.schema["annotations"] = json.loads(json.dumps(self.schema["annotations"]))
        self.schema["annotations"] = convert_annotations(self.schema["annotations"])

        update_time = f"{datetime.datetime.now().isoformat()}"
        self.schema.setdefault("created_on", update_time)
        if self.schema.get("title") == "":
            del self.schema["title"]
        self.schema.setdefault("last_updated_on", update_time)

        if "comments" in self.schema:
            self.schema["comments"] = [
                (k + ": " + v)
                for k, vals in self.schema["comments"].items()
                for v in vals
            ]

    def export_schema(self):
        yaml_file_basename = self.graph_name.replace("/", "__")

        with open(yaml_file_basename + ".yaml", "w") as f:
            yaml.dump(self.schema, f)

    def export_untyped_entities(self):
        yaml_file_basename = self.graph_name.replace("/", "__")

        with open(yaml_file_basename + "_untyped.txt", "w") as f:
            f.writelines(str(e) + "\n" for e in self.entities_without_type)

    def characterize(self):
        if self.args.process_ontologies:
            self.process_restrictions()
            self.process_ontologies()
            self.process_classes()
            self.process_types()
            self.process_slots()

        if self.args.process_counts:
            self.process_counts()

        self.add_missing_domain_range_types()

        self.convert_class_dicts()

        self.convert_slot_dicts()

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

