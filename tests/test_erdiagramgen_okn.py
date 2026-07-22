from linkml_runtime.linkml_model.meta import (
    ClassDefinition,
    SchemaDefinition,
    SlotDefinition,
)

from erdiagramgen_okn import ERDiagramGenerator


def test_mermaid_identifiers_are_sanitized():
    schema = SchemaDefinition(
        id="https://example.test/schema",
        name="test",
        classes={
            "3DModel": ClassDefinition(
                name="3DModel",
                slots=["property.with#punctuation"],
            ),
            "fio-epa-frs_Agency.Agriculture": ClassDefinition(
                name="fio-epa-frs_Agency.Agriculture"
            ),
            "kwgos_#S2Cell": ClassDefinition(name="kwgos_#S2Cell"),
        },
        slots={
            "property.with#punctuation": SlotDefinition(
                name="property.with#punctuation",
                range="type.with#punctuation",
            )
        },
    )

    diagram = ERDiagramGenerator(schema, format="mermaid").serialize()

    assert "iri_3DModel {" in diagram
    assert "Fio-epa-frsAgency_Agriculture {" in diagram
    assert "Kwgos_S2Cell {" in diagram
    assert "type_with_punctuation property_with_punctuation" in diagram
