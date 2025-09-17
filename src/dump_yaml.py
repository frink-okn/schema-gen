import argparse
import datetime
import json
import logging
import os
import re
import time
import yaml
from collections import defaultdict, Counter
from copy import deepcopy
from functools import lru_cache
from graphlib import TopologicalSorter, CycleError
from itertools import chain
from sys import argv

import frontmatter
import linkml_runtime
import rdflib
import requests
import tqdm
from linkml_runtime.utils.metamodelcore import URIorCURIE, XSDDateTime
from rdflib import URIRef, Namespace, BNode
from rdflib.namespace import XSD, SKOS, DCTERMS, DCAT, RDF, RDFS, OWL, SDO, PROV
from rdflib.plugins.parsers import notation3
from rdflib_hdt import HDTStore

from common_functions import *
from external_ontologies import external_ontologies_dict
from linkml_structures import linkml_class, linkml_schema, linkml_slot
from predicate_mappings import *

# external ontology processing

URIs_to_entities = {}
URIs_to_ontologies = { # slots from extended_types
    "xsd:length": "okns:extended_types",
    "xsd:minLength": "okns:extended_types",
    "xsd:maxLength": "okns:extended_types",
    "xsd:minExclusive": "okns:extended_types",
    "xsd:maxExclusive": "okns:extended_types",
    "rdf:langRange": "okns:extended_types",
}
URI_entity_types = {}
subclass_tree = defaultdict(set)

def load_external_ontologies(source=external_ontologies_dict, external_ontology_path=None):
    for name, external_ontology in source.items():
        current_from_path = external_ontology['from_path']
        current_read_path = external_ontology['read_path']
        if external_ontology_path:
            current_read_path = current_read_path.replace('https://purl.org/okn/schema/',external_ontology_path)
        current_schema = linkml_runtime.SchemaView(current_read_path + '.yaml')
        new_classes = {}
        new_slots = {}
        for current_type in current_schema.schema.types.values():
            if 'uri' in current_type and (current_type['uri'] not in URIs_to_ontologies) and (current_type['from_schema'] != current_from_path):
                current_uri = current_type['uri']
                URIs_to_entities[current_uri] = current_type
                URI_entity_types[current_uri] = 'type'
                URIs_to_ontologies[current_uri] = deepcopy(current_from_path)
        for current_class in current_schema.schema.classes.values():
            if 'class_uri' in current_class and (current_class['class_uri'] not in URIs_to_ontologies) and (current_class['from_schema'] != current_from_path):
                current_uri = current_class['class_uri']
                URIs_to_entities[current_uri] = current_class
                URI_entity_types[current_uri] = 'class'
                URIs_to_ontologies[current_uri] = deepcopy(current_from_path)
                if current_class.is_a is not None:
                    if not check_for_cycles(current_class.name, current_class.is_a):
                        subclass_tree[current_class.is_a].add(current_class.name)
        for current_slot in current_schema.schema.slots.values():
            if 'slot_uri' in current_slot and (current_slot['slot_uri'] not in URIs_to_ontologies) and (current_slot['from_schema'] != current_from_path):
                current_uri = current_slot['slot_uri']
                URIs_to_entities[current_uri] = current_slot
                URI_entity_types[current_uri] = 'slot'
                URIs_to_ontologies[current_uri] = deepcopy(current_from_path)

def get_graph(graph_to_read):
    """ Reads in a set of TTL files from a folder.
        May be modified as needed to crawl files in other places.
    """
    g = rdflib.Graph()

    if graph_to_read[0] == '/':
        folder_to_visit = graph_to_read
    else:
        folder_to_visit = os.path.join('..','frink-data-lakefs','lakefs',graph_to_read)
    for root, _, files in os.walk(folder_to_visit):
        for name in files:
            current_file_path = os.path.join(root, name)
            if any(current_file_path.endswith(suffix) for suffix in ['.ttl', '.rdf', '_RDF', '.n3', '.nt', '.owl']):
                current_file_read = False
                for file_format in ['xml', 'ttl', 'n3', 'nt']:
                    try:
                        g.parse(current_file_path, format=file_format)
                        print('Read', current_file_path, 'as', file_format)
                        current_file_read = True
                        break
                    except Exception as e:
                        logging.debug('Tried to read %s as %s but could not' % (current_file_path, file_format))
                        continue
                if not current_file_read:
                    raise RuntimeError('Unable to read ' + current_file_path)
            elif any(current_file_path.endswith(suffix) for suffix in ['.nq']):
                g = rdflib.Dataset()
                current_file_read = False
                for format in ['trig', 'trix', 'nquads']:
                    try:
                        g.parse(current_file_path, format=format)
                        current_file_read = True
                        break
                    except rdflib.exceptions.ParserError:
                        continue
                if not current_file_read:
                    raise RuntimeError('Unable to read ' + current_file_path)                
            elif current_file_path.endswith('.hdt'):
                g = rdflib.Graph(store=HDTStore(current_file_path))
                break

    return g

def add_str_to_single(obj_in, pred, string_to_store, source_mapping=None):
    if source_mapping is None:
        current_slot, current_datatype = SLOTS_TO_PREDICATES_SINGLE[pred]
    else:
        current_slot, current_datatype = source_mapping[pred]
    if value_is_valid(string_to_store, current_datatype, pred, obj_in['name']):
        if current_slot not in obj_in or (current_slot in obj_in and obj_in[current_slot].endswith("but has not itself been defined.")): # TODO: is this phrase likely to occur at the end of strings in actual schemas?
            obj_in[current_slot] = string_to_store.strip()
        else:
            if "comments" not in obj_in:
                obj_in["comments"] = defaultdict(set)
            obj_in["comments"][current_slot].add(string_to_store.strip())
    else:
        if "comments" not in obj_in:
            obj_in["comments"] = defaultdict(set)
        obj_in["comments"][current_slot].add(string_to_store.strip())

def convert_annotations(annotations):
    if not isinstance(annotations, dict):
        return annotations

    new_annotations = {}
    for k, v in annotations.items():
        new_annotations[k] = {'tag': k, 'value': convert_annotations(v)}

    return new_annotations

def find_shortest_path_helper(start, end, path=[]):
    path = path + [start]
    if start == end:
        return path
    if start not in subclass_tree:
        return None
    shortest = None
    for node in list(subclass_tree[start]):
        newpath = find_shortest_path_helper(node, end, path)
        if newpath:
            if not shortest or len(newpath) < len(shortest):
                shortest = newpath
    return shortest

@lru_cache(maxsize=None)
def find_shortest_path(start, end):
    """ Ripped and modified from https://www.python.org/doc/essays/graphs/ """
    return find_shortest_path_helper(start, end)
    
def check_for_cycles(subj_key, obj_key):
    try:
        TopologicalSorter({**subclass_tree, obj_key: set([subj_key])}).prepare()
    except CycleError as e:
        logging.warning('Found a cycle in the subclass tree, which is being disregarded: %s', e.args[1])
        return e.args[1]

class GraphCharacterizer:
    def __init__(self, args):
        self.g = get_graph(args.graph_to_read)
        self.list_untyped_entities = args.list_untyped_entities

        if(args.okn_registry_id):
            target_url = f'https://raw.githubusercontent.com/frink-okn/okn-registry/refs/heads/main/docs/registry/kgs/{args.okn_registry_id}.md'
            response = requests.get(target_url)
            post = frontmatter.loads(response.content)
            self.graph_name = post['shortname']
            self.schema = linkml_schema(self.graph_name, post['title'])
            self.schema['description'] = post['description']
            self.schema['see_also'] = []
            for metadata_key in ['stats', 'funding', 'sparql', 'tpf']:
                if metadata_key in post:
                    self.schema['see_also'].append(post[metadata_key])
            current_url = None
            if post['contact']['email']:
                current_url = 'mailto:' + post['contact']['email']
            elif post['contact']['github']:
                current_url = post['contact']['github']
            if current_url:
                if 'contributors' in self.schema:
                    self.schema['contributors'].append(current_url)
                else:
                    self.schema['contributors'] = [current_url]
        else:
            self.graph_name = args.graph_name
            self.schema = linkml_schema(self.graph_name, args.graph_title)

        self.restrictions = defaultdict(dict)
        self.entities_without_type = set()
        self.entities_without_type_count = 0
        self.multiple_typed_object_counts = defaultdict(int)

    def add_str_to_multiple(self, obj_in, pred, string_to_store):
        current_slot, current_datatype = SLOTS_TO_PREDICATES_MULTIPLE_STR[pred]
        if value_is_valid(string_to_store, current_datatype, pred, obj_in['name']):
            if current_slot == 'exact_mappings':
                current_curie = self.replace_prefixes(string_to_store)
                if current_curie in [obj_in.get(key,'') for key in ['class_uri','slot_uri','uri']]:
                    return
            if not current_slot in obj_in:
                obj_in[current_slot] = [string_to_store]
            elif string_to_store not in obj_in[current_slot]:
                obj_in[current_slot].append(string_to_store.strip())

    def replace_prefixes(self, node):
        """ Replaces a URI prefix with the abbreviation as given in 'replacements' above. """
        node, replacement, prefix = find_prefix(node)
        if replacement != '':
            self.schema['prefixes'][replacement] = str(prefix)
        return node

    def produce_curie_key(self, uri):
        output_curie = self.replace_prefixes(uri)
        output_key = output_curie.replace(':','_').replace('/','_')
        return output_curie, output_key

    def process_restrictions(self):
        for (entity, _, _) in tqdm.tqdm(self.g.triples((None, RDF.type, OWL.Restriction)), desc='Restrictions'):
            target_properties = set()
            target_classes = set()
            for (_, _, obj) in self.g.triples((entity, OWL.onProperty, None)):
                target_properties.add(obj)

            for (_, _, obj) in self.g.triples((entity, OWL.onClass, None)):
                target_classes.add(obj)

            for subj, pred, obj in self.g.triples((entity, None, None)):
                if pred in SINGLE_VALUE_RESTRICTIONS:
                    for target_property in list(target_properties):
                        self.restrictions[target_property][SINGLE_VALUE_RESTRICTIONS[pred]] = obj

    def process_ontologies(self):
        ontologies = [entity for (entity, _, _) in tqdm.tqdm(self.g.triples((None, RDF.type, OWL.Ontology)), desc='Ontologies')]
        for entity in ontologies:
            for subj, pred, obj in self.g.triples((entity, None, None)):
                string_to_store = str(obj).replace("\n",'␊')
                if pred in SLOTS_TO_PREDICATES_SINGLE:
                    add_str_to_single(self.schema, pred, string_to_store)
                elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                    self.add_str_to_multiple(self.schema, pred, string_to_store)
                elif pred in SLOTS_TO_PREDICATES_SINGLE_ONTOLOGY:
                    self.add_str_to_single(self.schema, pred, string_to_store, SLOTS_TO_PREDICATES_SINGLE_ONTOLOGY)

    def add_class(self, subj_key, subj_uri=None, subj_title=None, extra_info=None, from_schema=None):
        """ Adds a new class to the schema. """
        self.schema['classes'][subj_key]['name'] = subj_key
        if subj_uri is not None:
            self.schema['classes'][subj_key]['class_uri'] = str(subj_uri)
        if from_schema is not None:
            self.schema['classes'][subj_key]['from_schema'] = from_schema
            del self.schema['classes'][subj_key]['title']
            del self.schema['classes'][subj_key]['description']
            return
        if subj_title is not None:
            self.schema['classes'][subj_key]['title'] = subj_title
        if extra_info is not None:
            self.schema['classes'][subj_key] = {**self.schema['classes'][subj_key], **extra_info}

    def add_type(self, subj_type, subj_key, subj_uri=None, subj_title=None, extra_info=None, from_schema=None):
        """ Adds a new type to the schema. """
        if subj_type in datatype_to_type:
            return
        self.schema['types'][subj_key]['name'] = subj_key
        if subj_uri is not None:
            self.schema['types'][subj_key]['uri'] = str(subj_uri)
        if from_schema is not None:
            self.schema['types'][subj_key]['from_schema'] = from_schema
            self.schema['types'][subj_key]['imported_from'] = from_schema
            del self.schema['types'][subj_key]['title']
            del self.schema['types'][subj_key]['description']
            return
        if subj_title is not None:
            self.schema['types'][subj_key]['title'] = subj_title
        if extra_info is not None:
            self.schema['types'][subj_key] = {**self.schema['types'][subj_key], **extra_info}

    def add_slot(self, subj_key, subj_uri=None, subj_title=None, extra_info=None, from_schema=None):
        """ Adds a new slot to the schema. """
        self.schema['slots'][subj_key]['name'] = subj_key
        if subj_uri is not None:
            self.schema['slots'][subj_key]['slot_uri'] = str(subj_uri)
        if from_schema is not None:
            self.schema['slots'][subj_key]['from_schema'] = from_schema
            self.schema['slots'][subj_key]['imported_from'] = from_schema
            del self.schema['slots'][subj_key]['title']
            del self.schema['slots'][subj_key]['description']
            return
        if subj_title is not None:
            self.schema['slots'][subj_key]['title'] = subj_title
        if extra_info is not None:
            self.schema['slots'][subj_key] = {**self.schema['slots'][subj_key], **extra_info}

    def process_classes(self):
        for class_type, extra_info in CLASS_TYPES.items():
            current_classes = [entity for (entity, _, _) in self.g.triples((None, RDF.type, class_type))]
            if len(current_classes) == 0:
                continue
            progress_bar = tqdm.tqdm(current_classes, desc=f'Classes {str(class_type)}')
            for entity in progress_bar:
                if entity in datatype_to_type:
                    continue
                if isinstance(entity, BNode) or str(entity).startswith('_:'): # TODO: handle these
                    continue
                if (entity, RDF.type, OWL.Restriction) in self.g:
                    continue
                subj_uri, subj_key = self.produce_curie_key(entity)
                if subj_uri in URIs_to_ontologies:
                    continue

                if subj_key in self.schema['classes'] and ("title" in self.schema['classes'][subj_key] and "but has not itself been defined" not in self.schema['classes'][subj_key]['title']):
                    if 'deprecated' in self.schema['classes'][subj_key] and 'deprecated' in extra_info:
                        self.schema['classes'][subj_key].update({**extra_info, 'deprecated': self.schema['classes'][subj_key]['deprecated']})
                    else:
                        self.schema['classes'][subj_key].update(extra_info)
                    continue
                self.add_class(subj_key, subj_uri, extra_info=extra_info)

                for subj, pred, obj in self.g.triples((entity, None, None)):
                    obj_uri, obj_key = self.produce_curie_key(obj)

                    if pred in SLOTS_TO_PREDICATES_SINGLE:
                        add_str_to_single(self.schema['classes'][subj_key], pred, str(obj))
                    elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                        self.add_str_to_multiple(self.schema['classes'][subj_key], pred, str(obj))
                    elif pred in {RDFS.subClassOf}:
                        if isinstance(obj, BNode) or str(obj).startswith('_:'): # TODO: handle these
                            continue
                        if obj_key != subj_key:
                            if not check_for_cycles(subj_key, obj_key):
                                subclass_tree[obj_key].add(subj_key)
                            try:
                                target_entity, target_ontology = self.check_for_import(obj_uri)
                            except KeyError:
                                pass
                            self.schema['classes'][subj_key]['is_a'] = obj_key
                        if (obj_key not in self.schema['classes']) and (obj_uri not in URIs_to_ontologies):
                            self.add_class(obj_key, obj_uri, "No class (entity type) name specified -- this class is noted as a superclass of another class in this graph but has not itself been defined.")

    def process_types(self):
        for class_type, extra_info in TYPE_TYPES.items():
            current_types = [entity for (entity, _, _) in self.g.triples((None, RDF.type, class_type))]
            if len(current_types) == 0:
                continue
            progress_bar = tqdm.tqdm(current_types, desc=f'Types {str(class_type)}')
            for entity in progress_bar:
                if (entity, RDF.type, OWL.Restriction) in self.g:
                    continue
                if isinstance(entity, BNode) or str(entity).startswith('_:'): # TODO: handle these
                    continue
                subj_uri, subj_key = self.produce_curie_key(entity)

                if subj_key in self.schema['types'] and ("title" in self.schema['types'][subj_key] and "but has not itself been defined" not in self.schema['types'][subj_key]['title']):
                    continue
                if entity in datatype_to_type:
                    continue
                if subj_uri in URIs_to_ontologies:
                    continue
                self.add_type(entity, subj_key, subj_uri, extra_info=extra_info)

                for subj, pred, obj in self.g.triples((entity, None, None)):
                    obj_uri, obj_key = self.produce_curie_key(obj)

                    if pred in SLOTS_TO_PREDICATES_SINGLE:
                        add_str_to_single(self.schema['types'][subj_key], pred, str(obj))
                    elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                        self.add_str_to_multiple(self.schema['types'][subj_key], pred, str(obj))
                    elif pred in {RDFS.subClassOf}:
                        if isinstance(obj, BNode) or str(obj).startswith('_:'): # TODO: handle these
                            continue
                        if obj_key != subj_key:
                            if not check_for_cycles(subj_key, obj_key):
                                subclass_tree[obj_key].add(subj_key)
                            try:
                                target_entity, target_ontology = self.check_for_import(obj_uri)
                            except KeyError:
                                pass
                            if obj == RDFS.Literal:
                                current_typeof = 'string'
                            elif URI_entity_types.get(obj_uri, 'class') != 'slot':
                                current_typeof = 'string'
                            else:
                                current_typeof = obj_key
                            self.schema['types'][subj_key]['typeof'] = current_typeof
                        if (obj_key not in self.schema['types']) and (obj_uri not in URIs_to_ontologies):
                            self.add_class(obj_key, obj_uri, "No (data)type name specified -- this type is noted as a supertype of another type in this graph but has not itself been defined.")

    def process_slots(self):
        for slot_type, extra_info in SLOT_TYPES.items():
            current_predicates = [entity for (entity, _, _) in self.g.triples((None, RDF.type, slot_type))]
            if len(current_predicates) == 0:
                continue
            progress_bar = tqdm.tqdm(current_predicates, desc=f'Predicates ({str(slot_type)})')
            for entity in progress_bar:
                subj_curie_key = self.produce_curie_key(entity)
                subj_uri, subj_key = subj_curie_key
                if (entity, RDF.type, OWL.Restriction) in self.g:
                    continue
                if entity in datatype_to_type:
                    continue
                if subj_uri in URIs_to_ontologies:
                    continue
                if re.match(str(RDF) + r'_\d+', str(entity)):
                    # TODO: handle these predicates
                    continue

                if subj_key in self.schema['slots'] and ("title" in self.schema['slots'][subj_key] and "but has not itself been defined" not in self.schema['slots'][subj_key]['title']):
                    continue
                self.add_slot(subj_key, subj_uri, extra_info=extra_info)

                for subj, pred, obj in self.g.triples((entity, None, None)):
                    obj_curie_key = self.produce_curie_key(obj)
                    obj_uri, obj_key = obj_curie_key

                    if pred in SLOTS_TO_PREDICATES_SINGLE:
                        add_str_to_single(self.schema['slots'][subj_key], pred, str(obj))
                    elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                        self.add_str_to_multiple(self.schema['slots'][subj_key], pred, str(obj))
                    elif pred in {RDFS.domain, SDO.domainIncludes}:
                        if isinstance(obj, BNode) or str(obj).startswith('_:'): # TODO: handle these
                            continue
                        normalized_type, current_import, current_prefixes = linkml_type_mapping(obj)
                        if normalized_type != obj:
                            self.schema['imports'].add(current_import)
                            self.schema['prefixes'].update(current_prefixes)
                            obj_curie_key = self.produce_curie_key(normalized_type)
                        self.add_to_domain(subj_key, obj_curie_key)
                    elif pred in {RDFS.range, SDO.rangeIncludes}:
                        if isinstance(obj, BNode) or str(obj).startswith('_:'): # TODO: handle these
                            continue
                        normalized_type, current_import, current_prefixes = linkml_type_mapping(obj)
                        if normalized_type != obj:
                            self.schema['imports'].add(current_import)
                            self.schema['prefixes'].update(current_prefixes)
                            obj_curie_key = self.produce_curie_key(normalized_type)
                        self.add_to_range(subj_curie_key, obj_curie_key)
                    elif pred in {OWL.inverseOf, SDO.inverseOf}:
                        self.schema['slots'][subj_key]['inverse'] = obj_key
                    elif pred in {RDFS.subPropertyOf}:
                        if subj_key != obj_key:
                            try:
                                target_entity, target_ontology = self.check_for_import(obj_uri)
                            except KeyError:
                                pass
                            self.schema['slots'][subj_key]['subproperty_of'] = obj_key
                        if (obj_key not in self.schema['slots']) and (obj_uri not in URIs_to_ontologies):
                            self.add_slot(obj_key, obj_uri, "No slot (predicate) name specified -- this slot is noted as a subproperty of another slot in this graph but has not itself been defined.")

    def increment_usage_count(self, subject_type_uri, pred_uri, object_type_uri):
        """ Increments the usage of a particular subject-type, predicate, object-type triple. """
        if subject_type_uri is None:
            self.schema['annotations']['counts']['pairs'][pred_uri]['untyped'][object_type_uri] += 1
        else:
            self.schema['annotations']['counts']['pairs'][pred_uri][subject_type_uri][object_type_uri] += 1

    def add_example(self, subject_type_uri, pred_uri, object_type_uri, example):
        suri = subject_type_uri or 'untyped'
        ouri = object_type_uri or 'untyped'
        if self.schema['annotations']['examples']["pairs"][pred_uri][suri][ouri] == {}:
            self.schema['annotations']['examples']["pairs"][pred_uri][suri][ouri] = {
                'subject': example[0],
                'predicate': example[1],
                'object': example[2]
            }

    def add_to_domain(self, pred_key, obj_curie_key):
        if not obj_curie_key in self.schema['slots'][pred_key]['union_of']:
            self.schema['slots'][pred_key]['union_of'].add(obj_curie_key)

    def add_to_range(self, pred_curie_key, obj_curie_key):
        pred_uri, pred_key = pred_curie_key
        obj_uri, obj_key = obj_curie_key
        try:
            target_entity, target_ontology = self.check_for_import(pred_uri)
        except KeyError:
            if not obj_curie_key in self.schema['slots'][pred_key]['any_of']:
                self.schema['slots'][pred_key]['any_of'].add(obj_curie_key)
        else:
            # TODO: do something here?
            current_predicate = URIs_to_entities[pred_uri]
            try:
                if current_predicate.range == obj_key or any(z.range == obj_key for z in current_predicate.any_of):
                    pass
            except AttributeError:
                pass

    def account_for_triple(self, subj_type_curie_key, pred_curie_key, obj_type_curie_key, example):
        if subj_type_curie_key is None:
            subj_type_uri, subj_type_key = None, None
        else:
            subj_type_uri, subj_type_key = subj_type_curie_key
        pred_uri, pred_key = pred_curie_key
        obj_type_uri, obj_type_key = obj_type_curie_key

        self.increment_usage_count(subj_type_uri, pred_uri, obj_type_uri)
        self.add_example(subj_type_uri, pred_uri, obj_type_uri, example)
        self.add_to_range(pred_curie_key, obj_type_curie_key)

    def add_missing_classes(self, subj_uri, object_types, object_type_uris_keys):
        if not any(obj in METADATA_TYPES for obj in list(object_types)):
            for obj_uri, obj_key in object_type_uris_keys:
                if obj_key not in self.schema['classes'] and obj_uri not in URIs_to_ontologies:
                    self.add_class(obj_key, obj_uri)
                    if obj_key not in self.schema['annotations']['examples']['classes']:
                        self.schema['annotations']['examples']['classes'][obj_uri] = str(subj_uri)

    def check_for_import(self, type_uri):
        target_ontology = URIs_to_ontologies[type_uri]
        self.schema['imports'].add(target_ontology)

        # TODO: revise target_entity out
        try:
            target_entity = URIs_to_entities[type_uri]
        except KeyError:
            target_entity = ""

        return target_entity, target_ontology

    def check_for_missing_domain_range_type(self, set_type_curie_key):
        set_type_uri, set_type_key = set_type_curie_key
        if set_type_key not in self.schema['classes'] and set_type_key not in self.schema['types']:
            try:
                target_entity, target_ontology = self.check_for_import(set_type_uri)
            except KeyError:
                if set_type_key not in linkml_type_names:
                    self.add_class(set_type_key, set_type_uri, "No class (entity type) name specified -- this class is noted as being in the domain or range of a slot in this graph but has not itself been defined.")

    def add_missing_domain_range_types(self):
        for _, slot_dict in self.schema['slots'].items():
            if len(slot_dict['union_of']) == 0:
                if 'domain' in slot_dict and slot_dict['domain'] == 'Any':
                    self.schema['imports'].add(extended_types_url)
            for set_type_curie_key in list(slot_dict['union_of']):
                self.check_for_missing_domain_range_type(set_type_curie_key)
            if len(slot_dict['any_of']) == 0:
                if slot_dict['range'] == 'Any':
                    self.schema['imports'].add(extended_types_url)
            for set_type_curie_key in list(slot_dict['any_of']):
                self.check_for_missing_domain_range_type(set_type_curie_key)

    def convert_class_dicts(self):
        for class_key, class_dict in chain(self.schema['classes'].items(), self.schema['types'].items()):
            if 'notes' in class_dict and len(class_dict['notes']) == 0:
                del class_dict['notes']
            if 'slots' in class_dict:
                class_dict['slots'] = list(class_dict['slots'])
                if len(class_dict['slots']) == 0:
                    del class_dict['slots']

            if 'description' in class_dict:
                class_dict["description"] = class_dict["description"].replace("\n",'␊')
            if class_dict['name'] == '':
                class_dict['name'] = class_key
            if 'comments' in class_dict and len(class_dict['comments']) > 0:
                class_dict['comments'] = [
                    (k + ': ' + v) for k in class_dict['comments'] for v in list(class_dict['comments'][k])
                ]
            elif 'comments' in class_dict:
                del class_dict['comments']

    def convert_slot_dicts(self):
        for key, slot_dict in self.schema["slots"].items():
            slot_uri = slot_dict['slot_uri']
            if 'description' in slot_dict:
                slot_dict["description"] = slot_dict["description"].replace("\n",'␊')
            if self.schema['annotations']['counts']['slots'][slot_uri] == 0:
                if 'notes' in slot_dict:
                    slot_dict['notes'].append('No occurrences of this slot in the graph.')
                else:
                    slot_dict['notes'] = ['No occurrences of this slot in the graph.']
                del self.schema['annotations']['counts']['slots'][slot_uri]

            slot_dict['any_of'] = [{'range': typename} for (_, typename) in list(slot_dict['any_of'])]
            if len(slot_dict['any_of']) == 1:
                slot_dict['range'] = slot_dict['any_of'][0]['range']
                del slot_dict['any_of']
            elif len(slot_dict['any_of']) == 0:
                del slot_dict['any_of']

            slot_dict['union_of'] = [typename for (_, typename) in list(slot_dict['union_of'])]
            if len(slot_dict['union_of']) == 1:
                slot_dict['domain'] = slot_dict['union_of'][0]
                del slot_dict['union_of']
            elif len(slot_dict['union_of']) == 0:
                del slot_dict['union_of']

            if 'notes' in slot_dict and len(slot_dict['notes']) == 0:
                del slot_dict['notes']
            if 'comments' in slot_dict and len(slot_dict['comments']) == 0:
                del slot_dict['comments']
            elif 'comments' in slot_dict:
                slot_dict['comments'] = [
                    (k + ': ' + v) for k in slot_dict['comments'] for v in list(slot_dict['comments'][k])
                ]

    def assemble_counts(self):
        for subj in tqdm.tqdm(self.g.subjects(unique=True)):
            subj_uri, subj_key = self.produce_curie_key(subj)
            if subj_uri in URIs_to_ontologies:
                continue

            subject_types_initial = list(set([(subject_type, *(self.produce_curie_key(subject_type))) for subject_type in self.g.objects(subject=subj, predicate=RDF.type)]))
            subject_types = set()
            subject_type_uris_keys = set()
            for st, stc, stk in subject_types_initial:
                if not any(find_shortest_path(stk, other_stk) for other_st, other_stc, other_stk in subject_types_initial if other_st != st):
                    if (st, RDF.type, OWL.Restriction) not in self.g:
                        subject_types.add(st)
                        subject_type_uris_keys.add((stc, stk))

            if any(((subject_type in [OWL.Ontology, OWL.Restriction]) or (subject_type in CLASS_TYPES) or (subject_type in SLOT_TYPES)) for subject_type in list(subject_types)):
                continue
            elif OWL.AllDisjointClasses in subject_types:
                # TODO: handle AllDisjointClasses
                continue

            if len(subject_types) > 1:
                self.multiple_typed_object_counts[frozenset(subject_types)] += 1
            elif len(subject_types) == 0:
                self.entities_without_type_count += 1

            for (subject_type_uri, subject_type_key) in subject_type_uris_keys:
                try:
                    target_entity, target_ontology = self.check_for_import(subject_type_uri)
#                    self.add_class(subject_type_key, subject_type_uri, from_schema=target_ontology)
                except KeyError:
                    if not (subject_type_key in self.schema['classes'] or subject_type_key in self.schema['types'] or subject_type_uri in URIs_to_ontologies):
                        self.add_class(subject_type_key, subject_type_uri)

                # Absolute occurrence count
                self.schema['annotations']['counts']['classes'][subject_type_uri] += 1
                if subject_type_key not in self.schema['annotations']['examples']['classes']:
                    self.schema['annotations']['examples']['classes'][subject_type_uri] = str(subj_uri)

            for pred, obj in self.g.predicate_objects(subject=subj):
                if pred == RDF.type:
                    continue

                pred_curie_key = self.produce_curie_key(pred)
                pred_uri, pred_key = pred_curie_key
                obj_curie_key = self.produce_curie_key(obj)
                obj_uri, obj_key = obj_curie_key
                example = (subj_uri, pred_uri, obj_uri)

                if pred in [RDF.first, RDF.rest]:
                    # TODO: handle these predicates
                    continue

                if re.match(str(RDF) + r'_\d+', str(pred)):
                    # TODO: handle these predicates
                    continue

                try:
                    target_entity, target_ontology = self.check_for_import(pred_uri)
#                    self.add_slot(pred_key, pred_uri, from_schema=target_ontology)
                except KeyError:
                    self.schema['slots'][pred_key]['slot_uri'] = str(pred_uri)

                object_types_initial = list(set([(object_type, *(self.produce_curie_key(object_type))) for object_type in self.g.objects(subject=obj, predicate=RDF.type)]))
                object_types = set()
                object_type_uris_keys = set()
                for ot, otc, otk in object_types_initial:
                    if not any(find_shortest_path(otk, other_otk) for other_ot, other_otc, other_otk in object_types_initial if other_ot != ot):
                        if (ot, RDF.type, OWL.Restriction) not in self.g:
                            object_types.add(ot)
                            object_type_uris_keys.add((otc, otk))

                # Absolute occurrence count
                self.schema['annotations']['counts']['slots'][str(pred_uri)] += 1

                if len(object_types) > 0:
                    if len(subject_types) > 0:
                        self.add_missing_classes(subj_uri, subject_types, subject_type_uris_keys)
                        for subject_type_curie_key in list(subject_type_uris_keys):
                            subject_type_uri, subject_type_key = subject_type_curie_key
                            if subject_type_uri not in URIs_to_ontologies:
                                if subject_type_key not in self.schema['classes']:
                                    self.add_class(subject_type_key, subject_type_uri)
                                self.schema['classes'][subject_type_key]['slots'].add(pred_key)

                            for object_type_curie_key in list(object_type_uris_keys):
                                self.account_for_triple(subject_type_curie_key, pred_curie_key, object_type_curie_key, example)
                    else:
                        if self.list_untyped_entities:
                            self.entities_without_type.add(subj)
                        for object_type_curie_key in list(object_type_uris_keys):
                            self.account_for_triple(None, pred_curie_key, object_type_curie_key, example)
                else:
                    # TODO: add object datatypes to self.schema['types']
                    if isinstance(obj, BNode) or str(obj).startswith('_:'): # skip blank nodes for now, revisit restrictions in QUDT TTL
                        continue
                    object_datatype = get_object_datatype(obj)
                    object_type_mapping, current_import, current_prefixes = linkml_type_mapping(object_datatype)
                    if current_import != '':
                        self.schema['imports'].add(current_import)
                        self.schema['prefixes'].update(current_prefixes)
                    object_datatype_curie_key = self.produce_curie_key(object_type_mapping)
                    object_datatype_uri, object_datatype_key = object_datatype_curie_key
                    if object_datatype_uri not in URIs_to_ontologies:
                        self.add_type(object_datatype, object_datatype_key, object_datatype_uri)
                    if len(subject_types) > 0:
                        self.add_missing_classes(subj_uri, subject_types, subject_type_uris_keys)
                        for subject_type_curie_key in list(subject_type_uris_keys):
                            subject_type_uri, subject_type_key = subject_type_curie_key
                            if subject_type_uri not in URIs_to_ontologies:
                                if subject_type_key not in self.schema['classes']:
                                    self.add_class(subject_type_key, subject_type_uri)
                                self.schema['classes'][subject_type_key]['slots'].add(pred_key)
                            self.account_for_triple(subject_type_curie_key, pred_curie_key, object_datatype_curie_key, example)
                    else:
                        if self.list_untyped_entities:
                            self.entities_without_type.add(subj)
                        self.account_for_triple(None, pred_curie_key, object_datatype_curie_key, example)

    def clean_up_json(self):
        self.schema["classes"] = dict(self.schema["classes"])
        self.schema["types"] = dict(self.schema["types"])
        if len(self.schema['types']) == 0:
            del self.schema['types']
        self.schema["slots"] = dict(self.schema["slots"])
        self.schema["imports"] = list(self.schema["imports"])
        self.schema["annotations"] = json.loads(json.dumps(self.schema["annotations"]))
        self.schema["annotations"] = convert_annotations(self.schema["annotations"])
        update_time = f"{datetime.datetime.now().isoformat()}"
        if "created_on" not in self.schema:
            self.schema['created_on'] = update_time
        if self.schema['title'] == "":
            del self.schema['title']
        if "last_updated_on" not in self.schema:
            self.schema['last_updated_on'] = update_time
        if 'comments' in self.schema:
            self.schema['comments'] = [
                (k + ': ' + v) for k in self.schema['comments'] for v in list(self.schema['comments'][k])
            ]

    def export_results(self):
        yaml_file_basename = self.graph_name.replace('/','__')

        with open(yaml_file_basename + '.yaml','w') as f:
            yaml.dump(self.schema, f)

        if self.list_untyped_entities:
            with open(yaml_file_basename + '_untyped.txt','w') as f:
                for entity in list(self.entities_without_type):
                    f.write(str(entity) + '\n')
        else:
            print('Found', self.entities_without_type_count, 'untyped entities')

    def characterize(self):
        self.process_restrictions()

        self.process_ontologies()

        self.process_classes()

        self.process_types()

        self.process_slots()

        self.assemble_counts()

        self.add_missing_domain_range_types()

        self.convert_class_dicts()

        self.convert_slot_dicts()

        self.clean_up_json()

        self.export_results()

if __name__ == '__main__':
    # Reads the graphs...
    parser = argparse.ArgumentParser(
        prog='LinkML Schema Generator',
        description='Produces LinkML schemas from RDF data'
    )
    
    parser.add_argument('graph_name')
    parser.add_argument('graph_to_read')
    parser.add_argument('graph_title', nargs='?', default=None)
    parser.add_argument('--list-untyped-entities', action='store_true', help='Provides a list of untyped subject entities in the graph.')
    parser.add_argument('--generate-base-schemas', type=int, help='Of the ontologies listed in external_ontologies.py, which (1-indexed) to generate while leaving the others above it intact.')
    parser.add_argument('--okn-registry-id', help='Name of the graph in the OKN registry.')
    parser.add_argument('--external-ontology-path', help='Path to where external ontologies are stored: the prefix "https://purl.org/okn/schema/" will be substituted with the value of this argument.')

    args = parser.parse_args()
    if args.generate_base_schemas is not None:
        external_ontologies_list = list(external_ontologies_dict.items())
        previous_entries = external_ontologies_list[:args.generate_base_schemas]
        source = dict(previous_entries)
    else:
        source = external_ontologies_dict
    load_external_ontologies(source, args.external_ontology_path)

    GraphCharacterizer(args).characterize()
