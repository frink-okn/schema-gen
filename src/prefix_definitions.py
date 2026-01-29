from rdflib.namespace import Namespace, DCAT, DCAM, DCMITYPE, DCTERMS, GEO, OWL, RDF, PROV, SDO, SOSA, SKOS, RDFS, XSD, DC, VOID, FOAF, WGS, TIME, VANN, ORG

replacement_prefixes = {
    'dc': DC, # from rdflib.namespace
    'dcam': DCAM, # from rdflib.namespace
    'dcat': DCAT, # from rdflib.namespace
    'dcmitype': DCMITYPE, # from rdflib.namespace
    'dct': DCTERMS, # from rdflib.namespace
    'foaf': FOAF, # from rdflib.namespace
    'geo': GEO, # from rdflib.namespace
    'org': ORG, # from rdflib.namespace
    'owl': OWL, # from rdflib.namespace
    'prov': PROV, # from rdflib.namespace
    'rdf': RDF, # from rdflib.namespace
    'rdfs': RDFS, # from rdflib.namespace
    'sdos': SDO, # from rdflib.namespace
    'skos': SKOS, # from rdflib.namespace
    'sosa': SOSA, # from rdflib.namespace
    'time': TIME, # from rdflib.namespace
    'vann': VANN, # from rdflib.namespace
    'void': VOID, # from rdflib.namespace
    'xsd': XSD, # from rdflib.namespace
    'schema': Namespace('http://schema.org/'),
    'ical': Namespace('http://www.w3.org/2002/12/cal/ical#'), # RDF schema for iCalendar data
    'icalspec': Namespace('http://www.w3.org/2002/12/cal/icalSpec#'), # RDF schema for iCalendar data
    'adms': Namespace('http://www.w3.org/ns/adms#'), # Asset Description Metadata Schema
    'wgs': Namespace('http://www.w3.org/2003/01/geo/wgs84_pos#'), # from rdflib.namespace
    'bibo': Namespace('http://purl.org/ontology/bibo/'), # Bibliographic Ontology
    'xhv': Namespace('http://www.w3.org/1999/xhtml/vocab#'), # XHTML Vocabulary
    'swvs': Namespace('http://www.w3.org/2003/06/sw-vocab-status/ns#'), # SemWeb Vocab Status ontology
    'wot': Namespace('http://xmlns.com/wot/0.1/'), # Web of Trust
    'wn16': Namespace('http://xmlns.com/wordnet/1.6/'), # WordNet 1.6 (used by Web of Trust; does not itself resolve)
    'dtype': Namespace('http://www.linkedmodel.org/schema/dtype#'), # Datatype Ontology
    'vaem': Namespace('http://www.linkedmodel.org/schema/vaem#'), # Vocabulary for Attaching Essential Metadata
    'voag': Namespace('http://voag.linkedmodel.org/voag#'), # Vocabulary of Attribution and Governance
    'eli': Namespace('http://data.europa.eu/eli/ontology#'), # ELI Metadata Ontology
    'regorg': Namespace('http://www.w3.org/ns/regorg#'), # Registered Organization Vocabulary
    'voaf': Namespace('http://purl.org/vocommons/voaf#'), # Vocabulary of a Friend
    'prism': Namespace('http://prismstandard.org/namespaces/1.2/basic/'), # Publishing Requirements for Industry Standard Metadata
    'daml': Namespace('http://www.daml.org/2000/10/daml-ont#'), # DARPA Agent Markup Language (DAML)
    'daml-oil': Namespace('http://www.daml.org/2001/03/daml+oil#'), # Ontology Inference Layer (DAML)
    'daml-iso3166': Namespace('http://www.daml.org/2001/09/countries/iso-3166-ont#'), # ISO 3166 (DAML)
    'daml-usregionstate': Namespace('http://www.daml.ri.cmu.edu/ont/USRegionState.daml#'), # US States/Regions (DAML)
    'daml-country-ont': Namespace('http://www.daml.org/2001/09/countries/country-ont#'), # "country-ont" (DAML)
    'daml-state': Namespace('http://www.daml.ri.cmu.edu/ont/State.daml#'), # States (DAML)
    'daml-city': Namespace('http://www.daml.ri.cmu.edu/ont/City.daml#'), # Cities (DAML)
    'daml-country': Namespace('http://www.daml.ri.cmu.edu/ont/Country.daml#'), # Countries (DAML)
    'daml-profile': Namespace('http://www.daml.org/services/daml-s/2001/10/Profile.daml#'), # Profile (DAML)
    'daml-ont': Namespace('http://www.daml.ri.cmu.edu/ont/'), # unspecified (DAML)
    'daml-2001': Namespace('http://www.daml.org/2001/03/'), # unspecified (DAML)
    'wfb': Namespace('http://ontolingua.stanford.edu/doc/chimaera/ontologies/world-fact-book.daml#'), # CIA World Factbook (DAML)
    'time-entry': Namespace('http://www.isi.edu/~pan/damltime/time-entry.owl#'), # OWL-Time (DAML)
    'tzont': Namespace('http://www.isi.edu/~pan/damltime/timezone-ont.owl#'), # Time Zones (DAML)
    'xsd2000': Namespace('http://www.w3.org/2000/10/XMLSchema#'), # XML Schema (older version)
    'owl2-xml': Namespace('http://www.w3.org/2006/12/owl2-xml#'), # "used temporarily by the OWL Working Group. This namespace is expected to change."
    'cc': Namespace('http://web.resource.org/cc/'), # CC schema
    'creativecommons': Namespace('http://creativecommons.org/ns#'), # Creative Commons
    'event': Namespace('http://purl.org/NET/c4dm/event.owl#'), # Event Ontology
    'address': Namespace('http://schemas.talis.com/2005/address/schema#'), # Address Schema
    'gr': Namespace('http://purl.org/goodrelations/v1#'), # GoodRelations
    'frbr': Namespace('http://purl.org/vocab/frbr/core#'), # FRBR in RDF
    'frbroo': Namespace('http://iflastandards.info/ns/fr/frbr/frbroo/'), # FRBRoo model
    'cidoc-crm': Namespace('http://www.cidoc-crm.org/cidoc-crm/'), # CIDOC-CRM
    'vcard': Namespace('http://www.w3.org/2006/vcard/ns#'), # vCard ontology
    'mo': Namespace('http://purl.org/ontology/mo/'), # Music Ontology
    'ao': Namespace('http://purl.org/ontology/ao/core#'), # Association Ontology
    'sim': Namespace('http://purl.org/ontology/similarity/'), # Similarity Ontology
    'rev': Namespace('http://purl.org/stuff/rev#'), # RDF Review Vocabulary
    'pav': Namespace('http://purl.org/pav/'), # Provenance, Authoring and Versioning
    'kwgos': Namespace('https://stko-kwg.geog.ucsb.edu/lod/ontology'), # KnowWhereGraph ontology
    'kwgo': Namespace('http://stko-kwg.geog.ucsb.edu/lod/ontology/'), # KnowWhereGraph ontology
    'kwgr': Namespace('http://stko-kwg.geog.ucsb.edu/lod/resource/'), # KnowWhereGraph resource
    'irdr': Namespace('http://www.knowwheregraph.org/ontologies/hazard/IRDR/'), # Integrated Research on Disaster Risk
    'gnis-ld-gnis': Namespace('http://gnis-ld.org/lod/gnis/ontology/'), # GNIS-LD (Geographic Names Information System)
    'gnis-ld-usgs': Namespace('http://gnis-ld.org/lod/usgs/ontology/'), # GNIS-LD (United States Geological Survey)
    'iospress': Namespace('http://ld.iospress.nl/rdf/ontology/'), # IOS Press LD-Connect
    'iospress-datatype': Namespace('http://ld.iospress.nl/rdf/datatype/'), # IOS Press LD-Connect
    'iospress-geocode': Namespace('http://ld.iospress.nl/rdf/geocode/'), # IOS Press LD-Connect
    'c4o': Namespace('http://purl.org/spar/c4o/'), # Citation Counting and Context Characterization Ontology
    'biro': Namespace('http://purl.org/spar/biro/'), # Bibliographic Reference Ontology
    'swrl': Namespace('http://www.w3.org/2003/11/swrl#'), # Semantic Web Rule Language
    'swrlb': Namespace('http://www.w3.org/2003/11/swrlb#'), # Semantic Web Rule Language
    'dcgeoid': Namespace('https://datacommons.org/browser/geoId/'), # Google DataCommons
    'niem50': Namespace('http://release.niem.gov/niem/niem-core/5.0/'), # NIEM Core 5.0
    'niemfips50': Namespace(' http://release.niem.gov/niem/codes/fips/5.0/'), # NIEM FIPS 5.0
    'jxdm72': Namespace('http://release.niem.gov/niem/domains/jxdm/7.2/'), # NIEM Justice 7.2
    'nibrs': Namespace('http://fbi.gov/cjis/nibrs/2023.0/'), # CJIS NIBRS (is this a real prefix?)
    'bao': Namespace('http://www.bioassayontology.org/bao#BAO_'), # Bioassay Ontology
    'edam': Namespace('http://edamontology.org/'), # EDAM ontology
    'niehs': Namespace('https://ice.ntp.niehs.nih.gov/property/'), # Integrated Chemical Environment
    'umls': Namespace('https://identifiers.org/umls:'), # Unified Medical Language System
    'hyf': Namespace('https://www.opengis.net/def/schema/hy_features/hyf/'), # OGC ontology
    'sc': Namespace('http://shapechange.net/resources/ont/base#'), # ShapeChange
    'seegrid-basic': Namespace('http://def.seegrid.csiro.au/isotc211/iso19103/2005/basic#'), # SEEGrid
    'seegrid-ci': Namespace('http://def.seegrid.csiro.au/isotc211/iso19115/2003/citation#'), # SEEGrid
    'seegrid-role': Namespace('http://def.seegrid.csiro.au/isotc211/iso19115/2003/code/Role/'), # SEEGrid
    'spin': Namespace('http://spinrdf.org/spin#'), # SPARQL Inferencing Notation
    'spin-spl': Namespace('http://spinrdf.org/spl#'), # SPARQL Inferencing Notation
    'spin-sp': Namespace('http://spinrdf.org/sp#'), # SPARQL Inferencing Notation
    'spin-arg': Namespace('http://spinrdf.org/arg#'), # SPARQL Inferencing Notation
    'spin-spif': Namespace('http://spinrdf.org/spif#'), # SPARQL Inferencing Notation
    'sf': Namespace('http://www.opengis.net/ont/sf#'), # OGC ontology
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
    'neo4j': Namespace('neo4j://graph.schema#'), # Not a real prefix; should be substituted wherever it occurs.
    'example': Namespace('http://example.org/'), # Not a real prefix; should be substituted wherever it occurs.
    'attribute': Namespace('http://attribute.org/'), # Not a real prefix; should be substituted wherever it occurs.
    'relation': Namespace('http://relation.org/'), # Not a real prefix; should be substituted wherever it occurs.
    'badwdt': Namespace('https://www.wikidata.org/wiki/Property:'), # Not a real RDF prefix; should be substituted wherever it occurs.
    'dreamkg': Namespace('http://www.semanticweb.org/dreamkg/ijcai/'), # from DREAM-KG; should be substituted with a working IRI prefix.
    'scales': Namespace('http://schemas.scales-okn.org/rdf/scales#'), # from SCALES; should be substituted with a working IRI prefix.
    'sockg': Namespace('https://idir.uta.edu/sockg-ontology/docs/'), # from SOC-KG
    'securechain': Namespace('https://w3id.org/secure-chain/'), # from Secure Chain-KG
    'rural': Namespace('http://sail.ua.edu/ruralkg/'), # from RURAL-KG; should be substituted with a working IRI prefix.
    'coso': Namespace('http://w3id.org/coso/v1/contaminoso#'), # from SAWGRAPH
    'spatial': Namespace('http://purl.org/spatialai/spatial/spatial-full#'), # from SAWGRAPH
    'stad': Namespace('http://purl.org/spatialai/stad/v2/core/'), # from SAWGRAPH
    'fio': Namespace('http://w3id.org/fio/v1/fio#'), # from SAWGRAPH
    'fio-epa-frs': Namespace('http://w3id.org/fio/v1/epa-frs#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'fio-epa-frs-data': Namespace('http://w3id.org/fio/v1/epa-frs-data#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'naics': Namespace('http://w3id.org/fio/v1/naics#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'il_isgs': Namespace('http://sawgraph.spatialai.org/v1/il-isgs#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'il_isgs_data': Namespace('http://sawgraph.spatialai.org/v1/il-isgs-data#'), # from SAWGRAPH: should be substituted with a working IRI prefix.
    'me_egad': Namespace('http://sawgraph.spatialai.org/v1/me-egad#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'me_egad_data': Namespace('http://sawgraph.spatialai.org/v1/me-egad-data#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'me_mgs': Namespace('http://sawgraph.spatialai.org/v1/me-mgs#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'me_mgs_data': Namespace('http://sawgraph.spatialai.org/v1/me-mgs-data#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'pfas': Namespace('http://sawgraph.spatialai.org/v1/pfas#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'saw_geo': Namespace('http://sawgraph.spatialai.org/v1/saw_geo#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'us_frs': Namespace('http://sawgraph.spatialai.org/v1/us-frs#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'us_frs_data': Namespace('http://sawgraph.spatialai.org/v1/us-frs-data#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'us_sdwis': Namespace('http://sawgraph.spatialai.org/v1/us-sdwis#'), # from SAWGRAPH; should be substituted with a working IRI prefix.
    'io': Namespace('https://spec.industrialontologies.org/ontology/core/Core/'), # Industrial Ontologies Foundry
    'iosc': Namespace('https://spec.industrialontologies.org/ontology/supplychain/SupplyChain/'), # Industrial Ontologies Foundry
    'sudokn': Namespace('http://asu.edu/semantics/SUDOKN/'), # from SUDOKN: should be substituted with a working IRI prefix.
    'sudokn2': Namespace('Utilities:communication/'), # Not a real prefix; should be substituted wherever it occurs.
    'sudokn3': Namespace('Utilities:water/'), # Not a real prefix; should be substituted wherever it occurs.
    'aopkb': Namespace('http://aopkb.org/aop_ontology#'), # Adverse Outcome Pathways
    'biolink': Namespace('https://w3id.org/biolink/vocab/'), # Biolink Model
    'spoke-genelab': Namespace('https://spoke.ucsf.edu/genelab/'), # SPOKE GeneLab (non-functional prefix)
    'nasa-gesdisc': Namespace('https://nasa-gesdisc.proto-okn.net/kg/schema/'), # NASA GESDISC (non-functional prefix)
    # OBO graphs (obolibrary.org)
    'bfo': Namespace('http://purl.obolibrary.org/obo/BFO_'), # Basic Formal Ontology
    'bto': Namespace('http://purl.obolibrary.org/obo/BTO_'), # BRENDA Tissue Ontology (not in Ubergraph)
    'cl': Namespace('http://purl.obolibrary.org/obo/CL_'), # Cell Ontology
    'go': Namespace('http://purl.obolibrary.org/obo/GO_'), # Gene Ontology
    'hancestro': Namespace('http://purl.obolibrary.org/obo/HANCESTRO_'), # Human Ancestry Ontology (not in Ubergraph)
    'hp': Namespace('http://purl.obolibrary.org/obo/HP_'), # Human Phenotype Ontology
    'ncbitaxon': Namespace('http://purl.obolibrary.org/obo/NCBITaxon_'), # NCBI Taxonomy
    'ncit': Namespace('http://purl.obolibrary.org/obo/NCIT_'), # National Cancer Institute Thesaurus
    'mmo': Namespace('http://purl.obolibrary.org/obo/MMO_'), # Measurement Method Ontology
    'pato': Namespace('http://purl.obolibrary.org/obo/PATO_'), # Phenotype and Trait Ontology
    'uberon': Namespace('http://purl.obolibrary.org/obo/UBERON_'), # Uber-anatomy ontology
    # Other OLS4 graphs
    'cheminf': Namespace('http://semanticscience.org/resource/CHEMINF_'), # Chemical Information Ontology
    'sio': Namespace('http://semanticscience.org/resource/SIO_'), # Semanticscience Integrated Ontology
}

replacements = list(replacement_prefixes.items())
""" Just some substitutions of the namespaces above with prefixes for ease of reading. """
