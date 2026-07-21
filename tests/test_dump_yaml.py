import logging

import pytest
from linkml_runtime.utils.formatutils import camelcase
from rdflib import URIRef

from dump_yaml import (
    UNPREFIXED_IRI_WARNING_LIMIT,
    GraphCharacterizer,
    sanitize_linkml_key,
)


def make_characterizer():
    characterizer = object.__new__(GraphCharacterizer)
    characterizer.schema = {"prefixes": {}}
    characterizer.unprefixed_iris = set()
    characterizer.unprefixed_iri_warnings_suppressed = False
    characterizer.linkml_key_iris = {}
    return characterizer


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("frbr:Endeavour", "frbr_Endeavour"),
        ("http://example.test/Foo.Bar#Baz", "http_example_test_Foo_Bar_Baz"),
        ("https://example.test/a-b?x=1", "https_example_test_a_b_x_1"),
        ("123", "iri_123"),
        ("///", "iri"),
    ],
)
def test_sanitize_linkml_key(value, expected):
    assert sanitize_linkml_key(value) == expected


def test_produce_curie_key_preserves_unprefixed_iri(caplog):
    characterizer = make_characterizer()
    iri = URIRef("https://unregistered.example.test/Foo.Bar#Baz")

    with caplog.at_level(logging.WARNING):
        output_curie, output_key = characterizer.produce_curie_key(iri)

    assert output_curie == str(iri)
    assert output_key == "https_unregistered_example_test_Foo_Bar_Baz"
    assert "IRI could not be converted to a CURIE" in caplog.text


def test_frbr_regression_produces_safe_mermaid_entity_name():
    characterizer = make_characterizer()
    iri = URIRef("http://purl.org/vocab/frbr/core/Endeavour")

    output_curie, output_key = characterizer.produce_curie_key(iri)

    assert output_curie == str(iri)
    assert output_key == "http_purl_org_vocab_frbr_core_Endeavour"
    assert camelcase(output_key) == "HttpPurlOrgVocabFrbrCoreEndeavour"


def test_produce_curie_key_preserves_existing_curie_key_format(caplog):
    characterizer = make_characterizer()
    iri = URIRef("http://gnis-ld.org/lod/gnis/ontology/County")

    with caplog.at_level(logging.WARNING):
        output_curie, output_key = characterizer.produce_curie_key(iri)

    assert output_curie == "gnis-ld-gnis:County"
    assert output_key == "gnis-ld-gnis_County"
    assert "IRI could not be converted to a CURIE" not in caplog.text


def test_produce_curie_key_deduplicates_unprefixed_iri_warning(caplog):
    characterizer = make_characterizer()
    iri = URIRef("https://unregistered.example.test/Foo")

    with caplog.at_level(logging.WARNING):
        characterizer.produce_curie_key(iri)
        characterizer.produce_curie_key.cache_clear()
        characterizer.produce_curie_key(iri)

    messages = [
        record.message
        for record in caplog.records
        if record.message.startswith("IRI could not be converted to a CURIE")
    ]
    assert len(messages) == 1


def test_unprefixed_iri_warnings_are_capped(caplog):
    characterizer = make_characterizer()

    with caplog.at_level(logging.WARNING):
        for index in range(UNPREFIXED_IRI_WARNING_LIMIT + 2):
            characterizer.produce_curie_key(
                URIRef(f"https://unregistered.example.test/term/{index}")
            )

    iri_warnings = [
        record
        for record in caplog.records
        if record.message.startswith("IRI could not be converted to a CURIE")
    ]
    suppression_warnings = [
        record
        for record in caplog.records
        if record.message.startswith("Suppressing warnings for additional IRIs")
    ]
    assert len(iri_warnings) == UNPREFIXED_IRI_WARNING_LIMIT
    assert len(suppression_warnings) == 1
    assert len(characterizer.unprefixed_iris) == UNPREFIXED_IRI_WARNING_LIMIT


def test_linkml_key_collision_fails_fast():
    characterizer = make_characterizer()
    characterizer.produce_curie_key(URIRef("https://unregistered.example.test/a-b"))

    with pytest.raises(ValueError, match="produce the same LinkML key"):
        characterizer.produce_curie_key(URIRef("https://unregistered.example.test/a_b"))
