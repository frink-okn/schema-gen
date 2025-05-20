import argparse
import logging
import os
import re
import time
import yaml
from collections import defaultdict, Counter
from sys import argv

import linkml_runtime
import rdflib
import tqdm
from linkml_runtime.utils.metamodelcore import URIorCURIE, XSDDateTime
from rdflib import URIRef, Namespace
from rdflib.namespace import XSD, SKOS, DCTERMS, DCAT, RDF, RDFS, OWL, SDO, PROV
from rdflib_hdt import HDTStore

from external_ontologies import external_ontologies_list
from linkml_structures import linkml_class, linkml_schema, linkml_slot
from predicate_mappings import *
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
            removed = replacement + ':' + removed
            node = removed
    return node, replacement, prefix

# external ontology processing

URIs_to_classes = {}
URIs_to_slots = {}
prefixes_to_ontologies = {}
for name, external_ontology in external_ontologies_list.items():
    current_schema = linkml_runtime.SchemaView(external_ontology['read_path'] + '.yaml')
    prefixes_to_ontologies.update({prefix: name for prefix in external_ontology['prefixes']})
    URIs_to_classes.update({
        find_prefix(current_class.class_uri)[0]: current_class for current_class in current_schema.all_classes().values()
    })
    URIs_to_slots.update({
        find_prefix(current_slot.slot_uri)[0]: current_slot for current_slot in current_schema.all_slots().values()
    })

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
            if any(current_file_path.endswith(suffix) for suffix in ['.ttl', '.rdf', '_RDF']):
                current_file_read = False
                for format in ['ttl', 'xml']:
                    try:
                        g.parse(current_file_path, format=format)
                        current_file_read = True
                        break
                    except rdflib.exceptions.ParserError:
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

def get_object_datatype(obj):
    if isinstance(obj, URIRef):
        object_datatype = XSD.anyURI
    else:
        object_datatype = obj.datatype
    if object_datatype is None:
        object_datatype = XSD.string
    return object_datatype

def convert_class_dict(class_key, class_dict):
    if 'notes' in class_dict and len(class_dict['notes']) == 0:
        del class_dict['notes']
    if 'slots' in class_dict:
        class_dict['slots'] = list(class_dict['slots'])
        if len(class_dict['slots']) == 0:
            del class_dict['slots']
    if 'slot_usage' in class_dict:
        if len(class_dict['slot_usage']) == 0:
            del class_dict['slot_usage']

    if 'annotations' in class_dict:
        if len(class_dict['annotations']) == 1 and class_dict['annotations']['count'] == 0:
            del class_dict['annotations']
    if 'description' in class_dict:
        class_dict["description"] = class_dict["description"].replace("\n",'␊')
    if class_dict['name'] == '':
        class_dict['name'] = class_key

    return class_dict

def convert_slot_dict(slot_dict):
    slot_dict["description"] = slot_dict["description"].replace("\n",'␊')
    if slot_dict['annotations']['count'] == 0:
        slot_dict['comments'].append('No occurrences of this slot in the graph.')

    slot_dict['any_of'] = [{'range': typename} for (_, typename) in list(slot_dict['any_of'])]
    if len(slot_dict['any_of']) == 1:
        slot_dict['range'] = slot_dict['any_of'][0]['range']
        del slot_dict['any_of']
    elif len(slot_dict['any_of']) == 0:
        del slot_dict['any_of']

    slot_dict['union_of'] = [{'domain': typename} for (_, typename) in list(slot_dict['union_of'])]
    if len(slot_dict['union_of']) == 1:
        slot_dict['domain'] = slot_dict['union_of'][0]['domain']
        del slot_dict['union_of']
    elif len(slot_dict['union_of']) == 0:
        del slot_dict['union_of']

    new_examples = []
    for (subj_type, obj_type), (ex_subj, ex_pred, ex_obj) in slot_dict['examples'].items():
        new_examples.append({
            'object': {
                'example_subject_type': f'{subj_type}',
                'example_subject': f'{ex_subj}',
                'example_predicate': f'{ex_pred}',
                'example_object_type': f'{obj_type}',
                'example_object': f'{ex_obj}',
            }
        })
    slot_dict['examples'] = new_examples
    if len(slot_dict['examples']) == 0:
        del slot_dict['examples']

    if 'comments' in slot_dict and len(slot_dict['comments']) == 0:
        del slot_dict['comments']
    if 'annotations' in slot_dict:
        if len(slot_dict['annotations']) == 1 and slot_dict['annotations']['count'] == 0:
            del slot_dict['annotations']

    return slot_dict

def value_is_valid(string_to_store, datatype, pred, obj_name):
    if datatype == str:
        return True
    if datatype.is_valid(string_to_store):
        return True
    logging.warning('Attempted to add value "%s" for predicate %s to object %s', string_to_store, pred, obj_name)
    return False

def add_str_to_single(obj_in, pred, string_to_store, source_mapping=None):
    if source_mapping is None:
        current_slot, current_datatype = SLOTS_TO_PREDICATES_SINGLE[pred]
    else:
        current_slot, current_datatype = source_mapping[pred]
    if value_is_valid(string_to_store, current_datatype, pred, obj_in['name']):
        obj_in[current_slot] = string_to_store

def add_str_to_multiple(obj_in, pred, string_to_store):
    current_slot, current_datatype = SLOTS_TO_PREDICATES_MULTIPLE_STR[pred]
    if value_is_valid(string_to_store, current_datatype, pred, obj_in['name']):
        if not current_slot in obj_in:
            obj_in[current_slot] = [string_to_store]
        elif string_to_store not in obj_in[current_slot]:
            obj_in[current_slot].append(string_to_store)

class GraphCharacterizer:
    def __init__(self, args):
        self.graph_name = args.graph_name
        self.g = get_graph(args.graph_to_read)
        self.schema = linkml_schema(args.graph_name, args.graph_title)
        self.list_untyped_entities = args.list_untyped_entities

        self.restrictions = defaultdict(dict)
        self.entities_without_type = set()
        self.multiple_typed_object_counts = defaultdict(int)
        self.prefix_list = {}

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
        for (entity, _, _) in tqdm.tqdm(self.g.triples((None, RDF.type, OWL.Ontology)), desc='Ontologies'):
            for subj, pred, obj in self.g.triples((entity, None, None)):
                string_to_store = str(obj).replace("\n",'␊')
                if pred in SLOTS_TO_PREDICATES_SINGLE:
                    add_str_to_single(self.schema, pred, string_to_store)
                elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                    add_str_to_multiple(self.schema, pred, string_to_store)
                elif pred in SLOTS_TO_PREDICATES_SINGLE_ONTOLOGY:
                    add_str_to_single(self.schema, pred, string_to_store, SLOTS_TO_PREDICATES_SINGLE_ONTOLOGY)

    def add_class(self, subj_key, subj_uri=None, subj_title=None, extra_info=None):
        """ Adds a new class to the schema. """
        self.schema['classes'][subj_key]['name'] = subj_key
        if subj_uri is not None:
            self.schema['classes'][subj_key]['class_uri'] = str(subj_uri)
        if subj_title is not None:
            self.schema['classes'][subj_key]['title'] = subj_title
        if extra_info is not None:
            self.schema['classes'][subj_key] = {**self.schema['classes'][subj_key], **extra_info}

    def add_type(self, subj_type, subj_key, subj_uri=None, subj_title=None, extra_info=None):
        """ Adds a new type to the schema. """
        if subj_type in datatype_to_type:
            return
        self.schema['types'][subj_key]['name'] = subj_key
        if subj_uri is not None:
            self.schema['types'][subj_key]['uri'] = str(subj_uri)
        if subj_title is not None:
            self.schema['types'][subj_key]['title'] = subj_title
        if extra_info is not None:
            self.schema['types'][subj_key] = {**self.schema['types'][subj_key], **extra_info}

    def add_slot(self, subj_key, subj_uri=None, subj_title=None, extra_info=None):
        """ Adds a new slot to the schema. """
        self.schema['slots'][subj_key]['name'] = subj_key
        if subj_uri is not None:
            self.schema['slots'][subj_key]['slot_uri'] = str(subj_uri)
        if subj_title is not None:
            self.schema['slots'][subj_key]['title'] = subj_title
        if extra_info is not None:
            self.schema['slots'][subj_key] = {**self.schema['slots'][subj_key], **extra_info}

    def process_classes(self):
        for class_type, extra_info in CLASS_TYPES.items():
            progress_bar = tqdm.tqdm(self.g.triples((None, RDF.type, class_type)), desc=f'Classes {str(class_type)}')
            for (entity, _, _) in progress_bar:
                subj_uri, subj_key = self.produce_curie_key(entity)

                if subj_key in self.schema['classes']:
                    continue
                self.add_class(subj_key, subj_uri, "No class (entity type) name specified", extra_info)

                progress_bar.set_postfix(ordered_dict={'num_classes': len(self.schema['classes'])}, refresh=False)

                for subj, pred, obj in self.g.triples((entity, None, None)):
                    obj_uri, obj_key = self.produce_curie_key(obj)

                    if pred in SLOTS_TO_PREDICATES_SINGLE:
                        add_str_to_single(self.schema['classes'][subj_key], pred, str(obj))
                    elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                        add_str_to_multiple(self.schema['classes'][subj_key], pred, str(obj))
                    elif pred in {RDFS.subClassOf}:
                        if obj_key != subj_key:
                            self.schema['classes'][subj_key]['is_a'] = obj_key
                        if not obj_key in self.schema['classes']:
                            self.add_class(obj_key, obj_uri, "No class (entity type) name specified -- this class is noted as a superclass of another class in this graph but has not itself been defined.")

    def process_types(self):
        for class_type, extra_info in TYPE_TYPES.items():
            progress_bar = tqdm.tqdm(self.g.triples((None, RDF.type, class_type)), desc=f'Types {str(class_type)}')
            for (entity, _, _) in progress_bar:
                subj_uri, subj_key = self.produce_curie_key(entity)

                if subj_key in self.schema['types']:
                    continue
                self.add_class(subj_key, subj_uri, "No (data)type name specified", extra_info)

                progress_bar.set_postfix(ordered_dict={'num_types': len(self.schema['types'])}, refresh=False)

                for subj, pred, obj in self.g.triples((entity, None, None)):
                    obj_uri, obj_key = self.produce_curie_key(obj)

                    if pred in SLOTS_TO_PREDICATES_SINGLE:
                        add_str_to_single(self.schema['types'][subj_key], pred, str(obj))
                    elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                        add_str_to_multiple(self.schema['types'][subj_key], pred, str(obj))
                    elif pred in {RDFS.subClassOf}:
                        if obj_key != subj_key:
                            self.schema['types'][subj_key]['is_a'] = obj_key
                        if not obj_key in self.schema['types']:
                            self.add_class(obj_key, obj_uri, "No (data)type name specified -- this type is noted as a supertype of another type in this graph but has not itself been defined.")

    def process_slots(self):
        for slot_type, extra_info in SLOT_TYPES.items():
            progress_bar = tqdm.tqdm(self.g.triples((None, RDF.type, slot_type)), desc=f'Predicates ({str(slot_type)})')
            for (entity, _, _) in progress_bar:
                subj_uri, subj_key = self.produce_curie_key(entity)

                if subj_key in self.schema['slots']:
                    continue
                self.add_slot(subj_key, subj_uri, 'No slot (predicate) name specified', extra_info)

                progress_bar.set_postfix(ordered_dict={'num_slots': len(self.schema['slots'])}, refresh=False)

                for subj, pred, obj in self.g.triples((entity, None, None)):
                    obj_uri, obj_key = self.produce_curie_key(obj)

                    if pred in SLOTS_TO_PREDICATES_SINGLE:
                        add_str_to_single(self.schema['slots'][subj_key], pred, str(obj))
                    elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                        add_str_to_multiple(self.schema['slots'][subj_key], pred, str(obj))
                    elif pred in {RDFS.domain}:
                        normalized_type = linkml_type_mapping(obj)
                        if normalized_type != obj:
                            obj_uri, obj_key = self.produce_curie_key(normalized_type)
                        self.add_to_domain(subj_key, (obj_uri, obj_key))
                    elif pred in {RDFS.range}:
                        normalized_type = linkml_type_mapping(obj)
                        if normalized_type != obj:
                            obj_uri, obj_key = self.produce_curie_key(normalized_type)
                        self.add_to_range(subj_key, (obj_uri, obj_key))
                    elif pred in {RDFS.subPropertyOf}:
                        if subj_key != obj_key:
                            self.schema['slots'][subj_key]['subproperty_of'] = obj_key
                        if not obj_key in self.schema['slots']:
                            self.add_slot(obj_key, obj_uri, "No slot (predicate) name specified -- this slot is noted as a subproperty of another slot in this graph but has not itself been defined.")

    def increment_usage_count(self, subject_type_key, pred_key, object_type_key):
        """ Increments the usage of a particular subject-type, predicate, object-type triple. """
        if subject_type_key is None:
            if object_type_key in self.schema['slots'][pred_key]['annotations']:
                self.schema['slots'][pred_key]['annotations'][object_type_key] += 1
            else:
                self.schema['slots'][pred_key]['annotations'][object_type_key] = 1
        else:
            if pred_key in self.schema['classes'][subject_type_key]['slot_usage']:
                if object_type_key in self.schema['classes'][subject_type_key]['slot_usage'][pred_key]['annotations']:
                    self.schema['classes'][subject_type_key]['slot_usage'][pred_key]['annotations'][object_type_key] += 1
                else:
                    self.schema['classes'][subject_type_key]['slot_usage'][pred_key]['annotations'][object_type_key] = 1
            else:
                self.schema['classes'][subject_type_key]['slot_usage'][pred_key] = {'annotations': {object_type_key: 1}}

    def add_example(self, subject_type_key, pred_key, object_type_key, example):
        if (subject_type_key, object_type_key) not in self.schema['slots'][pred_key]['examples']:
            self.schema['slots'][pred_key]['examples'][(subject_type_key, object_type_key)] = example

    def add_to_domain(self, pred_key, obj_curie_key):
        if not obj_curie_key in self.schema['slots'][pred_key]['union_of']:
            self.schema['slots'][pred_key]['union_of'].add(obj_curie_key)

    def add_to_range(self, pred_key, obj_curie_key):
        if not obj_curie_key in self.schema['slots'][pred_key]['any_of']:
            self.schema['slots'][pred_key]['any_of'].add(obj_curie_key)

    def account_for_triple(self, subj_type_key, pred_key, obj_type_uri, obj_type_key, example):
        self.increment_usage_count(subj_type_key, pred_key, obj_type_key)
        self.add_example(subj_type_key, pred_key, obj_type_key, example)
        self.add_to_range(pred_key, (obj_type_uri, obj_type_key))

    def add_missing_classes(self, subj_uri, object_types, object_type_uris_keys):
        if not any(obj in METADATA_TYPES for obj in list(object_types)):
            for obj_uri, obj_key in object_type_uris_keys:
                if obj_key not in self.schema['classes']:
                    self.add_class(obj_key, obj_uri, "No class name specified")
                    if 'examples' not in self.schema['classes'][obj_key]:
                        self.schema['classes'][obj_key]['examples'] = [{'value': str(subj_uri)}]

    def check_for_import(self, type_uri, type_key, prefix, ontology, schema_part):
        if type_uri.startswith(prefix):
            try:
                target_class = URIs_to_classes[type_uri]
            except KeyError:
                pass
            else:
                self.schema['imports'].add(external_ontologies_list[ontology]['from_path'])
                self.schema[schema_part][type_key]['from_schema'] = external_ontologies_list[ontology]['from_path']
                try:
                    self.schema[schema_part][type_key]['description'] = str(target_class._as_dict['comments'][0])
                except IndexError:
                    pass
                return target_class

    def add_missing_domain_range_types(self):
        new_imports_found = []
        while True:
            for _, slot_dict in self.schema['slots'].items():
                for dict_key in ['union_of', 'any_of']:
                    for set_type_uri, set_type_key in list(slot_dict[dict_key]):
                        if set_type_key not in self.schema['classes'] and set_type_key not in self.schema['types']:
                            for prefix, ontology in prefixes_to_ontologies.items():
                                if self.check_for_import(set_type_uri, set_type_key, prefix, ontology, 'classes') is not None:
                                    new_imports_found.append((set_type_uri, prefix))
                                    break
            if len(new_imports_found) == 0:
                break
            time.sleep(5)

    def characterize(self):
        self.process_restrictions()

        self.process_ontologies()

        self.process_classes()

        self.process_slots()

        # ...and starts counting!

        for subj in tqdm.tqdm(self.g.subjects(unique=True)):
            subj_uri, subj_key = self.produce_curie_key(subj)
            if subj_uri in URIs_to_classes or subj_uri in URIs_to_slots:
                continue

            subject_types = set([subject_type for subject_type in self.g.objects(subject=subj, predicate=RDF.type)])
            subject_type_uris_keys = set([self.produce_curie_key(subject_type) for subject_type in list(subject_types)])

            if any(((subject_type == OWL.Ontology) or (subject_type in CLASS_TYPES) or (subject_type in SLOT_TYPES)) for subject_type in list(subject_types)):
                continue
            elif OWL.AllDisjointClasses in subject_types:
                # TODO: handle AllDisjointClasses
                continue

            if len(subject_types) > 1:
                self.multiple_typed_object_counts[frozenset(subject_types)] += 1

            for (subject_type_uri, subject_type_key) in subject_type_uris_keys:
                for prefix, ontology in prefixes_to_ontologies.items():
                    self.check_for_import(subject_type_uri, subject_type_key, prefix, ontology, 'classes')

                # Absolute occurrence count
                if not (subject_type_key in self.schema['classes'] or subject_type_key in self.schema['types']):
                    self.add_class(subject_type_key, subject_type_uri)
                self.schema['classes'][subject_type_key]['annotations']['count'] += 1

            for pred, obj in self.g.predicate_objects(subject=subj):
                if pred == RDF.type:
                    continue

                pred_uri, pred_key = self.produce_curie_key(pred)
                obj_uri, obj_key = self.produce_curie_key(obj)
                example = (subj_uri, pred_uri, obj_uri)

                if pred in [RDF.first, RDF.rest]:
                    # TODO: handle these predicates
                    continue

                for prefix, ontology in prefixes_to_ontologies.items():
                    self.check_for_import(pred_uri, pred_key, prefix, ontology, 'slots')

                if re.match(str(RDF) + r'_\d+', str(pred)):
                    # TODO: handle these predicates
                    continue

                object_types = set()
                object_type_uris_keys = set()
                for object_type in self.g.objects(subject=obj, predicate=RDF.type):
                    object_types.add(object_type)
                    object_type_uris_keys.add(self.produce_curie_key(object_type))

                # Absolute occurrence count
                self.schema['slots'][pred_key]['slot_uri'] = str(pred_uri)
                self.schema['slots'][pred_key]['annotations']['count'] += 1

                if len(object_types) > 0:
                    if len(subject_types) > 0:
                        self.add_missing_classes(subj_uri, subject_types, subject_type_uris_keys)
                        for subject_type_uri, subject_type_key in list(subject_type_uris_keys):
                            self.add_class(subject_type_key, subject_type_uri)
                            self.schema['classes'][subject_type_key]['slots'].add(pred_key)

                            for object_type_uri, object_type_key in list(object_type_uris_keys):
                                self.account_for_triple(subject_type_key, pred_key, object_type_uri, object_type_key, example)
                    else:
                        self.entities_without_type.add(subj)
                        for object_type_uri, object_type_key in list(object_type_uris_keys):
                            self.account_for_triple(None, pred_key, object_type_uri, object_type_key, example)
                else:
                    # TODO: add object datatypes to self.schema['types']
                    object_datatype = get_object_datatype(obj)
                    object_type_mapping = linkml_type_mapping(object_datatype)
                    object_datatype_uri, object_datatype_key = self.produce_curie_key(object_type_mapping)
                    self.add_type(object_datatype, object_datatype_key, object_datatype_uri)
                    if len(subject_types) > 0:
                        self.add_missing_classes(subj_uri, subject_types, subject_type_uris_keys)
                        for subject_type_uri, subject_type_key in list(subject_type_uris_keys):
                            self.add_class(subject_type_key, subject_type_uri)
                            self.schema['classes'][subject_type_key]['slots'].add(pred_key)
                        self.account_for_triple(subject_type_key, pred_key, object_datatype_uri, object_datatype_key, example)
                    else:
                        self.entities_without_type.add(subj)
                        self.account_for_triple(None, pred_key, object_datatype_uri, object_datatype_key, example)

        self.add_missing_domain_range_types()

        for key, value in self.schema['classes'].items():
            value = convert_class_dict(key, value)
        for key, value in self.schema['types'].items():
            value = convert_class_dict(key, value)
        for key, value in self.schema["slots"].items():
            value = convert_slot_dict(value)

        self.schema["classes"] = dict(self.schema["classes"])
        self.schema["types"] = dict(self.schema["types"])
        if len(self.schema['types']) == 0:
            del self.schema['types']
        self.schema["slots"] = dict(self.schema["slots"])
        self.schema["imports"] = list(self.schema["imports"])

        yaml_file_basename = self.graph_name.replace('/','__')

        with open(yaml_file_basename + '.yaml','w') as f:
            yaml.dump(self.schema, f)

        if self.list_untyped_entities:
            with open(yaml_file_basename + '_untyped.txt','w') as f:
                for entity in list(self.entities_without_type):
                    f.write(str(entity) + '\n')

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

    args = parser.parse_args()

    GraphCharacterizer(args).characterize()
