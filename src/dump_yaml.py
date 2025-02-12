import os
import re
import yaml
from collections import defaultdict
from sys import argv

import rdflib
import tqdm
from rdflib import URIRef, Namespace
from rdflib.namespace import XSD, SKOS, DCTERMS, DCAT, RDF, RDFS, OWL, SDO, PROV
from rdflib_hdt import HDTStore

from linkml_structures import linkml_class, linkml_schema, linkml_slot
from prefix_definitions import replacements

# Schema.org processing
SDO_graph = rdflib.Graph()
SDO_graph.parse('schemaorg-current-https.jsonld')
HSDO = Namespace("http://schema.org/")

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

replaced_prefixes = set()

def replace_prefixes(node, prefix_list):
    """ Replaces a URI prefix with the abbreviation as given in 'replacements' above. """
    for replacement, prefix in replacements:
        removed = node.removeprefix(str(prefix))
        if removed != str(node):
            removed = replacement + ':' + removed
            node = removed
            prefix_list[replacement] = str(prefix)
    return node

def linkml_type_mapping(object_datatype):
    """Substitutes a type with its reference from the LinkML types.yaml file."""
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
    return datatype_to_type.get(object_datatype, object_datatype)

def get_object_datatype(obj):
    if isinstance(obj, URIRef):
        object_datatype = XSD.anyURI
    else:
        object_datatype = obj.datatype
    if object_datatype is None:
        object_datatype = XSD.string
    return linkml_type_mapping(object_datatype)

def convert_class_dict(class_dict):
    if 'notes' in class_dict and len(class_dict['notes']) == 0:
        del class_dict['notes']
    if 'slots' in class_dict:
        class_dict['slots'] = list(class_dict['slots'])

    if 'description' in class_dict:
        class_dict["description"] = class_dict["description"].replace("\n",'␊')

    return class_dict

def convert_slot_dict(slot_dict):
    slot_dict["description"] = slot_dict["description"].replace("\n",'␊')
    if slot_dict['annotations']['count'] == 0:
        slot_dict['comments'].append('No occurrences of this slot in the graph.')

    slot_dict['any_of'] = [{'range': typename} for typename in list(slot_dict['any_of'])]
    if len(slot_dict['any_of']) == 1:
        slot_dict['range'] = slot_dict['any_of'][0]['range']
        del slot_dict['any_of']
    elif len(slot_dict['any_of']) == 0:
        del slot_dict['any_of']

    slot_dict['union_of'] = [{'domain': typename} for typename in list(slot_dict['union_of'])]
    if len(slot_dict['union_of']) == 1:
        slot_dict['domain'] = slot_dict['union_of'][0]['domain']
        del slot_dict['union_of']
    elif len(slot_dict['union_of']) == 0:
        del slot_dict['union_of']

    new_examples = []
    for (subj_type, obj_type), (ex_subj, ex_pred, ex_obj) in slot_dict['examples'].items():
        new_examples.append({
            'description': f'{subj_type}→{obj_type}',
            'object': {
                'example_subject_type': f'{subj_type}',
                'example_subject': f'{ex_subj}',
                'example_predicate': f'{ex_pred}',
                'example_object_type': f'{obj_type}',
                'example_object': f'{ex_obj}',
            }
        })
    slot_dict['examples'] = new_examples

    if 'comments' in slot_dict and len(slot_dict['comments']) == 0:
        del slot_dict['comments']

    return slot_dict

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
METADATA_TYPES = {OWL.Ontology, OWL.AllDisjointClasses, OWL.Restriction} | set(CLASS_TYPES.keys()) | set(SLOT_TYPES.keys())

SLOTS_TO_PREDICATES_SINGLE = {
    DCTERMS.description: "description",
    SKOS.definition: "description",
    DCTERMS.title: "title",
    RDFS.label: "title",
    OWL.deprecated: "deprecated",
    RDFS.isDefinedBy: "source",
    DCTERMS.language: "in_language",
    DCTERMS.isReplacedBy: "deprecated_element_has_exact_replacement",
    DCTERMS.creator: "created_by",
    DCTERMS.created: "created_on",
    DCTERMS.modified: "last_updated_on",
}
SLOTS_TO_PREDICATES_MULTIPLE_STR = {
    PROV.todo: "todos",
    SKOS.note: "notes",
    SKOS.changeNote: "notes",
    SKOS.editorialNote: "notes",
    SKOS.historyNote: "notes",
    SKOS.scopeNote: "notes",
    RDFS.comment: "comments",
    RDFS.seeAlso: "see_also",
    SKOS.altLabel: "aliases",
    SKOS.mappingRelation: "mappings",
    SKOS.exactMatch: "exact_mappings",
    SKOS.closeMatch: "close_mappings",
    SKOS.relatedMatch: "related_mappings",
    SKOS.narrowMatch: "narrow_mappings",
    SKOS.broadMatch: "broad_mappings",
    DCTERMS.contributor: "contributors",
    DCAT.theme: "categories",
    DCAT.keyword: "keywords",
    SDO.keywords: "keywords",
}
SLOTS_TO_PREDICATES_SINGLE_ONTOLOGY = {
    DCTERMS.hasVersion: "version",
}

def process_ontologies(graph, schema):
    for (entity, _, _) in tqdm.tqdm(graph.triples((None, RDF.type, OWL.Ontology)), desc='Ontologies'):
        for subj, pred, obj in tqdm.tqdm(graph.triples((entity, None, None)), leave=False):
            if pred in SLOTS_TO_PREDICATES_SINGLE:
                schema[SLOTS_TO_PREDICATES_SINGLE[pred]] = str(obj)
            elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                current_slot = SLOTS_TO_PREDICATES_MULTIPLE_STR[pred]
                if not current_slot in schema:
                    schema[current_slot] = [str(obj)]
                elif str(obj) not in schema[current_slot]:
                    schema[current_slot].append(str(obj))
            elif pred in SLOTS_TO_PREDICATES_SINGLE_ONTOLOGY:
                schema[SLOTS_TO_PREDICATES_SINGLE_ONTOLOGY[pred]] = str(obj)

def process_classes(graph, schema):
    subjects_seen = set()
    for class_type, extra_info in CLASS_TYPES.items():
        for (entity, _, _) in tqdm.tqdm(graph.triples((None, RDF.type, class_type)), desc='Classes'):
            subjects_seen.add(entity)
            subj_uri = replace_prefixes(entity, schema['prefixes'])
            subj_key = subj_uri.replace(':','_').replace('/','_')
            schema['classes'][subj_key] = {**schema['classes'][subj_key], **extra_info}

            for subj, pred, obj in tqdm.tqdm(graph.triples((entity, None, None)), leave=False):
                obj_uri = replace_prefixes(obj, schema['prefixes'])
                obj_key = obj_uri.replace(':','_').replace('/','_')

                print(subj, pred, obj)
                schema['classes'][subj_key]['name'] = subj_key
                schema['classes'][subj_key]['class_uri'] = str(subj_uri)
                schema['classes'][subj_key]['title'] = "No class (type) name specified"
                if pred in SLOTS_TO_PREDICATES_SINGLE:
                    schema['classes'][subj_key][SLOTS_TO_PREDICATES_SINGLE[pred]] = str(obj)
                elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                    current_slot = SLOTS_TO_PREDICATES_MULTIPLE_STR[pred]
                    if not current_slot in schema['classes'][subj_key]:
                        schema['classes'][subj_key][current_slot] = [str(obj)]
                    elif str(obj) not in schema['classes'][subj_key][current_slot]:
                        schema['classes'][subj_key][current_slot].append(str(obj))
                elif pred in {RDFS.subClassOf}:
                    if obj_key != subj_key:
                        schema['classes'][subj_key]['is_a'] = obj_key
                    if not obj_key in schema['classes']:
                        schema['classes'][obj_key]['name'] = obj_key
                        schema['classes'][obj_key]['class_uri'] = str(obj_uri)
                        schema['classes'][obj_key]['title'] = "No class (type) name specified -- this class is noted as a superclass of another class in this graph but has not itself been defined."

def process_slots(graph, schema, restrictions):
    for class_type, extra_info in CLASS_TYPES.items():
        for (entity, _, _) in tqdm.tqdm(graph.triples((None, RDF.type, class_type)), desc='Predicates'):
            subjects_seen.add(entity)
            subj_uri = replace_prefixes(entity, schema['prefixes'])
            subj_key = subj_uri.replace(':','_').replace('/','_')
            schema['slots'][subj_key] = {**schema['slots'][subj_key], **extra_info}

            for subj, pred, obj in tqdm.tqdm(graph.triples((entity, None, None)), leave=False):
                print(subj, pred, obj)
                schema['slots'][subj_key]['slot_uri'] = str(subj_uri)
                schema['slots'][subj_key]['title'] = 'No slot (predicate) name specified'
                if pred in SLOTS_TO_PREDICATES_SINGLE:
                    schema['slots'][subj_key][SLOTS_TO_PREDICATES_SINGLE[pred]] = str(obj)
                elif pred in SLOTS_TO_PREDICATES_MULTIPLE_STR:
                    current_slot = SLOTS_TO_PREDICATES_MULTIPLE_STR[pred]
                    if not current_slot in schema['slots'][subj_key][current_slot]:
                        schema['slots'][subj_key][current_slot] = [str(obj)]
                    elif str(obj) not in schema['slots'][subj_key][current_slot]:
                        schema['slots'][subj_key][current_slot].append(str(obj))
                elif pred in {RDFS.domain}:
                    schema['slots'][subj_key]['union_of'].add(obj_key)
                elif pred in {RDFS.range}:
                    object_datatype = get_object_datatype(obj)
                    object_datatype_key = replace_prefixes(object_datatype, schema['prefixes']).replace(':','_').replace('/','_')
                    schema['slots'][subj_key]['any_of'].add(object_datatype_key)
                elif pred in {RDFS.subPropertyOf}:
                    if subj_key != obj_key:
                        schema['slots'][subj_key]['subproperty_of'] = obj_key
                    if not obj_key in schema['slots']:
                        schema['slots'][obj_key]['name'] = obj_key
                        schema['slots'][obj_key]['slot_uri'] = str(obj_uri)
                        schema['slots'][obj_key]['title'] = "No slot (predicate) name specified -- this slot is noted as a subproperty of another slot in this graph but has not itself been defined."

SINGLE_VALUE_RESTRICTIONS = {
    OWL.cardinality: 'exact_cardinality',
    OWL.minCardinality: 'minimum_cardinality',
    OWL.maxCardinality: 'maximum_cardinality',
    OWL.qualifiedCardinality: 'exact_cardinality',
    OWL.minQualifiedCardinality: 'minimum_cardinality',
    OWL.maxQualifiedCardinality: 'maximum_cardinality',
}

def process_restrictions(graph):
    restrictions = defaultdict(dict)
    for (entity, _, _) in tqdm.tqdm(graph.triples((None, RDF.type, OWL.Restriction)), desc='Restrictions'):
        target_properties = {}
        target_classes = {}
        for (_, _, obj) in tqdm.tqdm(graph.triples((entity, OWL.onProperty, None)), leave=False):
            target_properties.add(obj)

        for (_, _, obj) in tqdm.tqdm(graph.triples((entity, OWL.onClass, None)), leave=False):
            target_classes.add(obj)

        for subj, pred, obj in tqdm.tqdm(graph.triples((entity, None, None)), leave=False):
            if pred in SINGLE_VALUE_RESTRICTIONS:
                for target_property in list(target_properties):
                    restrictions[target_property][SINGLE_VALUE_RESTRICTIONS[pred]] = obj
    return restrictions

sdo_objects_processed = set()

def get_stats(graph_name, graph_to_read, graph_title=None):
    g = get_graph(graph_to_read)

    entities_without_type = set()
    unseen_types = set()

    schema = linkml_schema(graph_name, graph_title)
    schema['classes']['Any'] = {'name': 'Any', 'class_uri': 'linkml:Any'}

    restrictions = process_restrictions(g)

    process_ontologies(g, schema)

    process_classes(g, schema)

    process_slots(g, schema, restrictions)

    # ...and starts counting!

    for subj in g.subjects(unique=True):
        subj_uri = replace_prefixes(subj, schema['prefixes'])
        subj_key = subj_uri.replace(':','_').replace('/','_')

        subject_types = set()
        subject_type_uris_keys = set()
        for subject_type in g.objects(subject=subj, predicate=RDF.type):
            subject_types.add(subject_type)
            subject_type_uri = replace_prefixes(subject_type, schema['prefixes'])
            subject_type_key = subject_type_uri.replace(':','_').replace('/','_')
            subject_type_uris_keys.add((subject_type_uri, subject_type_key))

            if subject_type.startswith(str(SDO)) or subject_type.startswith(str(HSDO)):
                if subject_type not in sdo_objects_processed:
                    sdo_objects_processed.add(subject_type)
                    sdo_graph_key = URIRef(str(subject_type).replace('http:','https:'))
                    try:
                        schema['classes'][subject_type_key]['name'] = subject_type_key
                        schema['classes'][subject_type_key]['class_uri'] = str(subject_type_uri)
                        schema['classes'][subject_type_key]['title'] = str(next(object for object in SDO_graph.objects(sdo_graph_key, RDFS.label)))
                        schema['classes'][subject_type_key]['description'] = str(next(object for object in SDO_graph.objects(sdo_graph_key, RDFS.comment))).replace('\n','␊')
                    except StopIteration:
                        pass

            # Absolute occurrence count
            schema['classes'][subject_type_key]['annotations']['count'] += 1

            if subject_type == OWL.Ontology:
                continue
            elif subject_type in CLASS_TYPES:
                continue
            elif subject_type in SLOT_TYPES:
                continue
            elif subject_type in [OWL.AllDisjointClasses]:
                print(subj, pred, obj)
                # TODO: handle AllDisjointClasses
                continue

        for pred, obj in g.predicate_objects(subject=subj):
            if pred == RDF.type:
                continue

            pred_uri = replace_prefixes(pred, schema['prefixes'])
            pred_key = pred_uri.replace(':','_').replace('/','_')
            obj_uri = replace_prefixes(obj, schema['prefixes'])
            obj_key = obj_uri.replace(':','_').replace('/','_')

            if pred == RDF.type and obj not in METADATA_TYPES:
                if obj_key not in schema['classes']:
                    schema['classes'][obj_key]['name'] = obj_key
                    schema['classes'][obj_key]['class_uri'] = str(obj_uri)
                    schema['classes'][obj_key]['title'] = "No class name specified"
                    if 'examples' not in schema['classes'][obj_key]:
                        schema['classes'][obj_key]['examples'] = [{'value': str(subj_uri)}]
                continue

            if pred in [RDF.first, RDF.rest]:
                # TODO: handle these predicates
                continue

            if pred.startswith(str(SDO)) or pred.startswith(str(HSDO)):
                if pred not in sdo_objects_processed:
                    sdo_objects_processed.add(pred)
                    sdo_graph_key = URIRef(str(pred).replace('http:','https:'))
                    try:
                        schema['slots'][pred_key]['title'] = str(next(object for object in SDO_graph.objects(sdo_graph_key, RDFS.label)))
                        schema['slots'][pred_key]['description'] = str(next(object for object in SDO_graph.objects(sdo_graph_key, RDFS.comment))).replace('\n','␊')
                    except StopIteration:
                        pass

            if re.match(str(RDF) + r'_\d+', str(pred)):
                # TODO: handle these predicates
                continue

            object_types = set()
            object_type_uris_keys = set()
            for object_type in g.objects(subject=obj, predicate=RDF.type):
                object_types.add(object_type)
                object_type_uri = replace_prefixes(object_type, schema['prefixes'])
                object_type_key = object_type_uri.replace(':','_').replace('/','_')
                object_type_uris_keys.add((object_type_uri, object_type_key))

            # Absolute occurrence count
            schema['slots'][pred_key]['slot_uri'] = str(pred_uri)
            schema['slots'][pred_key]['annotations']['count'] += 1

            if len(subject_types) > 0:
                for subject_type_uri, subject_type_key in list(subject_type_uris_keys):
                    schema['classes'][subject_type_key]['name'] = subject_type_key
                    schema['classes'][subject_type_key]['class_uri'] = str(subject_type_uri)
                    schema['classes'][subject_type_key]['slots'].add(pred_key)

                    if len(object_types) > 0:
                        for object_type_uri, object_type_key in list(object_type_uris_keys):
                            if pred_key in schema['classes'][subject_type_key]['slot_usage']:
                                if object_type_key in schema['classes'][subject_type_key]['slot_usage'][pred_key]['annotations']:
                                    schema['classes'][subject_type_key]['slot_usage'][pred_key]['annotations'][object_type_key] += 1
                                else:
                                    schema['classes'][subject_type_key]['slot_usage'][pred_key]['annotations'][object_type_key] = 1
                            else:
                                schema['classes'][subject_type_key]['slot_usage'][pred_key] = {'annotations': {object_type_key: 1}}

                            if (subject_type_key, object_type_key) not in schema['slots'][pred_key]['examples']:
                                schema['slots'][pred_key]['examples'][(subject_type_key, object_type_key)] = (subj_uri, pred_uri, obj_uri)
                            if not object_type_key in schema['slots'][pred_key]['any_of']:
                                schema['slots'][pred_key]['any_of'].add(object_type_key)

                    else:
                        object_datatype = get_object_datatype(obj)
                        object_datatype_uri = replace_prefixes(object_datatype, schema['prefixes'])
                        object_datatype_key = object_datatype_uri.replace(':','_').replace('/','_')

                        if pred_key in schema['classes'][subject_type_key]['slot_usage']:
                            if object_datatype_key in schema['classes'][subject_type_key]['slot_usage'][pred_key]['annotations']:
                                schema['classes'][subject_type_key]['slot_usage'][pred_key]['annotations'][object_datatype_key] += 1
                            else:
                                schema['classes'][subject_type_key]['slot_usage'][pred_key]['annotations'][object_datatype_key] = 1
                        else:
                            schema['classes'][subject_type_key]['slot_usage'][pred_key] = {'annotations': {object_datatype_key: 1}}

                        if (subject_type_key, object_datatype_key) not in schema['slots'][pred_key]['examples']:
                            schema['slots'][pred_key]['examples'][(subject_type_key, object_datatype_key)] = (subj_uri, pred_uri, obj_uri)
                        if not object_datatype_key in schema['slots'][pred_key]['any_of']:
                            schema['slots'][pred_key]['any_of'].add(object_datatype_key)

            else:
                entities_without_type.add(subj)
                if len(object_types) > 0:
                    for object_type_uri, object_type_key in list(object_type_uris_keys):
                        if counts_key in schema['slots'][pred_key]['annotations']:
                            schema['slots'][pred_key]['annotations'][object_type_key] += 1
                        else:
                            schema['slots'][pred_key]['annotations'][object_type_key] = 1

                        if (pred, object_type_key) not in schema['slots'][pred_key]['examples']:
                            schema['slots'][pred_key]['examples'][(None, object_type_key)] = (subj_uri, pred_uri, obj_uri)

                        if not object_type_key in schema['slots'][pred_key]['any_of']:
                            schema['slots'][pred_key]['any_of'].add(object_type_key)

                else:
                    object_datatype = get_object_datatype(obj)
                    object_datatype_uri = replace_prefixes(object_datatype, schema['prefixes'])
                    object_datatype_key = object_datatype_uri.replace(':','_').replace('/','_')

                    if object_datatype_key in schema['slots'][pred_key]['annotations']:
                        schema['slots'][pred_key]['annotations']['counts'][object_datatype_key] += 1
                    else:
                        schema['slots'][pred_key]['annotations']['counts'][object_datatype_key] = 1

                    if (None, object_datatype_key) not in schema['slots'][pred_key]['examples']:
                        schema['slots'][pred_key]['examples'][(None, object_datatype_key)] = (subj_uri, pred_uri, obj_uri)

                    if not object_datatype_key in schema['slots'][pred_key]['any_of']:
                        schema['slots'][pred_key]['any_of'].add(object_datatype_key)

    for key, value in schema['classes'].items():
        value = convert_class_dict(value)

    for key, value in schema["slots"].items():
        value = convert_slot_dict(value)

    schema['classes'] = dict(schema['classes'])
    schema["slots"] = dict(schema["slots"])

    yaml_file_basename = graph_name.replace('/','__')

    with open(yaml_file_basename + '.yaml','w') as f:
        yaml.dump(schema, f)

    with open(yaml_file_basename + '_untyped.txt','w') as f:
        for entity in list(entities_without_type):
            f.write(str(entity) + '\n')

if __name__ == '__main__':
    # Reads the graphs...
    graph_name = argv[1]
    graph_to_read = argv[2]
    try:
        graph_title = argv[3]
    except IndexError:
        graph_title = None

    get_stats(graph_name, graph_to_read, graph_title)
