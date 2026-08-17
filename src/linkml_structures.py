from collections import defaultdict
from typing import Any, TypeAlias, cast

from linkml_runtime.linkml_model import (
    Annotation,
    ClassDefinition,
    ClassDefinitionName,
    Prefix,
    PrefixPrefixPrefix,
    SchemaDefinition,
    SlotDefinition,
    SlotDefinitionName,
    TypeDefinition,
    TypeDefinitionName,
)
from linkml_runtime.linkml_model.annotations import AnnotationTag

from void_dataset import VoidDataset

# Redefinitions for clarity from linkml_runtime.linkml_model.meta
PrefixesFieldList: TypeAlias = list[dict[str, Any] | Prefix]
PrefixesFieldDict: TypeAlias = dict[str | PrefixPrefixPrefix, dict[str, Any] | Prefix]
ClassesFieldDict: TypeAlias = dict[
    str | ClassDefinitionName, dict[str, Any] | ClassDefinition
]
SlotsFieldDict: TypeAlias = dict[
    str | SlotDefinitionName, dict[str, Any] | SlotDefinition
]
TypesFieldDict: TypeAlias = dict[
    str | TypeDefinitionName, dict[str, Any] | TypeDefinition
]
AnnotationsFieldDict: TypeAlias = dict[str | AnnotationTag, dict[str, Any] | Annotation]

# Simplified versions of the above; TODO: can LinkML use those instead?
AnnotationsDict: TypeAlias = dict[str, Annotation]
ClassesDict: TypeAlias = dict[str, ClassDefinition]
SlotsDict: TypeAlias = dict[str, SlotDefinition]
TypesDict: TypeAlias = dict[str, TypeDefinition]


def linkml_schema(graph_name: str, graph_title: str | None, graph_description: str | None) -> SchemaDefinition:
    """Produces a new SchemaDefinition to be filled in.

    Args:
        graph_name: Name of the graph.
        graph_title: If present, a title for the graph.
        graph_description: If present, a description for the graph.

    Returns:
        New SchemaDefinition.
    """
    new_def = SchemaDefinition(name=graph_name, id="okns:"+graph_name, description=graph_description or "", title=graph_title or "")
    new_def.prefixes = {
        'okns': Prefix('okns', 'https://purl.org/okn/schema/'),
        'okn': Prefix('okn', 'https://purl.org/okn/')
    }
    new_def.default_prefix = 'okns'
    new_def.annotations = {}
    return new_def

def get_schema_classes(schema: SchemaDefinition) -> ClassesDict:
    if schema.classes is None:
        schema.classes = {}
    elif isinstance(schema.classes, list):
        new_classes: ClassesFieldDict = {}
        for entity in schema.classes:
            if isinstance(entity, dict):
                new_classes[entity["name"]] = ClassDefinition(**entity)
            else:
                new_classes[entity.name] = entity
        schema.classes = new_classes
    return cast(
        ClassesDict, schema.classes
    )  # TODO: find a way to do away with the cast


def get_schema_slots(schema: SchemaDefinition) -> SlotsDict:
    if schema.slots is None:
        schema.slots = {}
    elif isinstance(schema.slots, list):
        new_slots: SlotsFieldDict = {}
        for entity in schema.slots:
            if isinstance(entity, dict):
                new_slots[entity["name"]] = SlotDefinition(**entity)
            else:
                new_slots[entity.name] = entity
        schema.slots = new_slots
    return cast(SlotsDict, schema.slots)  # TODO: find a way to do away with the cast


def get_schema_types(schema: SchemaDefinition) -> TypesDict:
    if schema.types is None:
        schema.types = {}
    elif isinstance(schema.types, list):
        new_types: TypesFieldDict = {}
        for entity in schema.types:
            if isinstance(entity, dict):
                new_types[entity["name"]] = TypeDefinition(**entity)
            else:
                new_types[entity.name] = entity
        schema.types = new_types
    return cast(TypesDict, schema.types)  # TODO: find a way to do away with the cast


def get_schema_annotations(schema: SchemaDefinition) -> AnnotationsDict:
    if schema.annotations is None:
        schema.annotations = {}
    elif isinstance(schema.annotations, list):
        new_annotations: AnnotationsFieldDict = {}
        for entity in schema.annotations:
            if isinstance(entity, dict):
                new_annotations[entity["tag"]] = Annotation(**entity)
            else:
                new_annotations[entity.tag] = entity
        schema.annotations = new_annotations
    return cast(
        AnnotationsDict, schema.annotations
    )  # TODO: find a way to do away with the cast
