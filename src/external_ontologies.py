# This is a list of LinkML schemas representing external ontologies
# (i.e. those not defined by LinkML itself or by a Proto-OKN graph).

external_ontologies_list = {
    'sdo': {
        'read_path': './schemaorg',
        'prefixes': ['hsdo:', 'schema:'],
        'from_path': 'https://raw.githubusercontent.com/linkml/linkml-schemaorg/refs/heads/main/src/linkml/schemaorg'
    },
    'prov': {
        'read_path': './prov',
        'prefixes': ['prov:'],
        'from_path': 'https://raw.githubusercontent.com/linkml/linkml-prov/refs/heads/main/model/schema/prov'
    },
    'RDF-S': {
        'read_path': './rdf-rdfs',
        'prefixes': ['rdf:', 'rdfs:'],
        'from_path': 'https://raw.githubusercontent.com/frink-okn/schema-gen/refs/heads/main/rdf-rdfs'
    },
    'owl': {
        'read_path': './owl',
        'prefixes': ['owl:'],
        'from_path': 'https://raw.githubusercontent.com/frink-okn/schema-gen/refs/heads/main/owl'
    },
    'qudt': {
        'read_path': './qudt',
        'prefixes': ['qudt:'],
        'from_path': 'https://raw.githubusercontent.com/frink-okn/schema-gen/refs/heads/main/qudt'
    },
}