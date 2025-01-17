from rdflib.namespace import Namespace, DCAT, DCTERMS, GEO, OWL, RDF, PROV, SDO, SOSA, SKOS, RDFS, XSD, DC

replacement_prefixes = {
    'dc': DC, # from rdflib.namespace
    'dct': DCTERMS, # from rdflib.namespace
    'geo': GEO, # from rdflib.namespace
    'owl': OWL, # from rdflib.namespace
    'prov': PROV, # from rdflib.namespace
    'rdf': RDF, # from rdflib.namespace
    'rdfs': RDFS, # from rdflib.namespace
    'schema': SDO, # from rdflib.namespace
    'skos': SKOS, # from rdflib.namespace
    'sosa': SOSA, # from rdflib.namespace
    'xsd': XSD, # from rdflib.namespace
    'kwg': Namespace('https://stko-kwg.geog.ucsb.edu/lod/ontology'), # KnowWhereGraph
    'niem50': Namespace('http://release.niem.gov/niem/niem-core/5.0/'), # NIEM Core 5.0
    'jxdm72': Namespace('http://release.niem.gov/niem/domains/jxdm/7.2/#'), # NIEM Justice 7.2
    'obo': Namespace('http://purl.obolibrary.org/obo/'), # OBO Foundry (general)
    'cheminf': Namespace('http://purl.obolibrary.org/obo/CHEMINF_'), # Chemical Information Ontology
    'bao': Namespace('http://www.bioassayontology.org/bao#BAO_'), # Bioassay Ontology
    'edam': Namespace('http://edamontology.org/'), # EDAM ontology
    'semsci': Namespace('http://semanticscience.org/resource/SIO_'), # Semanticscience Integrated Ontology
    'niehs': Namespace('https://ice.ntp.niehs.nih.gov/property/'), # Integrated Chemical Environment
    'umls': Namespace('https://identifiers.org/umls:'), # Unified Medical Language System
    'hyf': Namespace('https://www.opengis.net/def/schema/hy_features/hyf'), # OGC ontology
    'sf': Namespace('http://www.opengis.net/ont/sf'), # OGC ontology
    'gwml22': Namespace('http://www.opengis.net/gwml-main/2.2/'), # OGC ontology
    'hyfo': Namespace('https://www.opengis.net/def/hy_features/ontology/hyf/'), # OGC ontology
    'hyfa': Namespace('https://www.opengis.net/def/appschema/hy_features/hyf/'), # OGC ontology
    'phila': Namespace('https://metadata.phila.gov/'), # City of Philadelphia
    'qudt': Namespace('http://qudt.org/schema/qudt/'), # QUDT ontology
    'wdp': Namespace('http://www.wikidata.org/prop/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wdpq': Namespace('http://www.wikidata.org/prop/qualifier/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wdpqn': Namespace('http://www.wikidata.org/prop/qualifier/value-normalized/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wdpqv': Namespace('http://www.wikidata.org/prop/qualifier/value/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wdpr': Namespace('http://www.wikidata.org/prop/reference/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wdprn': Namespace('http://www.wikidata.org/prop/reference/value-normalized/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wdprv': Namespace('http://www.wikidata.org/prop/reference/value/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wdpsv': Namespace('http://www.wikidata.org/prop/statement/value/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wdps': Namespace('http://www.wikidata.org/prop/statement/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wdpsn': Namespace('http://www.wikidata.org/prop/statement/value-normalized/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wd': Namespace('http://www.wikidata.org/entity/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wdata': Namespace('http://www.wikidata.org/wiki/Special:EntityData/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wdno': Namespace('http://www.wikidata.org/prop/novalue/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wdref': Namespace('http://www.wikidata.org/reference/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wds': Namespace('http://www.wikidata.org/entity/statement/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wdt': Namespace('http://www.wikidata.org/prop/direct/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wdtn': Namespace('http://www.wikidata.org/prop/direct-normalized/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wdv': Namespace('http://www.wikidata.org/value/'), # Wikidata-related (from https://w.wiki/4Byv)
    'wikibase': Namespace('http://wikiba.se/ontology#'), # Wikidata-related (from https://w.wiki/4Byv)
    'hsdo': Namespace('http://schema.org/'), # This prefix should be substituted with schema: wherever it occurs.
    'neo4j': Namespace('neo4j://graph.schema#'), # Not a real prefix; should be substituted wherever it occurs.
    'example': Namespace('http://example.org/'), # Not a real prefix; should be substituted wherever it occurs.
    'attribute': Namespace('http://attribute.org/'), # Not a real prefix; should be substituted wherever it occurs.
    'relation': Namespace('http://relation.org/'), # Not a real prefix; should be substituted wherever it occurs.
    'badwdt': Namespace('https://www.wikidata.org/wiki/Property:'), # Not a real RDF prefix; should be substituted wherever it occurs.
    'dreamkg': Namespace('http://www.semanticweb.org/dreamkg/ijcai/'), # from DREAM-KG; should be substituted with a working IRI prefix.
    'scales': Namespace('http://schemas.scales-okn.org/rdf/scales#'), # from SCALES; should be substituted with a working IRI prefix.
    'sockg': Namespace('http://www.semanticweb.org/zzy/ontologies/2024/0/soil-carbon-ontology/'), # from SOC-KG; should be substituted with a working IRI prefix.
    'securechain': Namespace('https://w3id.org/secure-chain/'), # from Secure Chain-KG
    'rural': Namespace('http://sail.ua.edu/ruralkg/'), # from RURAL-KG; should be substituted with a working IRI prefix.
    'contaminoso': Namespace('http://sawgraph.spatialai.org/v1/contaminoso#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'usfrs': Namespace('http://sawgraph.spatialai.org/v1/us-frs#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'usfrsdata': Namespace('http://sawgraph.spatialai.org/v1/us-frs-data#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'naics': Namespace('http://sawgraph.spatialai.org/v1/fio/naics#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'ilisgs': Namespace('http://sawgraph.spatialai.org/v1/il-isgs#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'meegad': Namespace('http://sawgraph.spatialai.org/v1/me-egad#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'memgs': Namespace('http://sawgraph.spatialai.org/v1/me-mgs#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'memgs2': Namespace('http://sawgraph.spatialai.org/v1/me_mgs#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'ussdwis': Namespace('http://sawgraph.spatialai.org/v1/us-sdwis#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'pfas': Namespace('http://sawgraph.spatialai.org/v1/pfas#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'sawwater': Namespace('http://sawgraph.spatialai.org/v1/saw_water#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'fio': Namespace('http://sawgraph.spatialai.org/v1/fio#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'psys': Namespace('http://proton.semanticweb.org/protonsys#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'io': Namespace('https://spec.industrialontologies.org/ontology/core/Core/'), # Industrial Ontologies Foundry
    'iosc': Namespace('https://spec.industrialontologies.org/ontology/supplychain/SupplyChain/'), # Industrial Ontologies Foundry
    'sudokn': Namespace('http://asu.edu/semantics/SUDOKN/'), # from SUDOKN: should be substituted with a working IRI prefix.
    'sudokn2': Namespace('Utilities:communication/'), # Not a real prefix; should be substituted wherever it occurs.
    'sudokn3': Namespace('Utilities:water/'), # Not a real prefix; should be substituted wherever it occurs.
}

replacements = list(replacement_prefixes.items())
""" Just some substitutions of the namespaces above with prefixes for ease of reading. """