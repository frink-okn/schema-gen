# This is a list of LinkML schemas representing external ontologies
# (i.e. those not defined by LinkML itself or by a Proto-OKN graph).
#
# Most of these were generated in order by excluding it and all entries below it
# from the external ontologies list
# and then rerunning the generation scripts
#
# python3 dump_yaml.py $graph /path/to/$graph
# gen-jsonld-context $graph.yaml >$graph".context.jsonld"
# gen-rdf $graph.yaml >$graph".ttl"
# python3 docgen-frink.py -v $graph".yaml" --diagram-type mermaid_class_diagram --directory ~/graph-descriptions/$graph --no-mergeimports --subfolder-type-separation --include-top-level-diagram --template-directory docgen-frink
#
# for each graph $graph .


external_ontologies_dict = {
    'owl-rdf-rdfs': {
        'read_path': 'https://purl.org/okn/schema/owl-rdf-rdfs',
        'from_path': 'okns:owl-rdf-rdfs'
    },
    'prov': {
        'read_path': 'https://purl.org/okn/schema/prov',
        'from_path': 'okns:prov'
    },
    'vcard': {
        'read_path': 'https://purl.org/okn/schema/vcard',
        'from_path': 'okns:vcard'
    },
    'skos': {
        'read_path': 'https://purl.org/okn/schema/skos',
        'from_path': 'okns:skos'
    },
    'dc': {
        'read_path': 'https://purl.org/okn/schema/dc',
        'from_path': 'okns:dc'
    },
    'time': {
        'read_path': 'https://purl.org/okn/schema/time',
        'from_path': 'okns:time'
    },
    'daml': {
        'read_path': 'https://purl.org/okn/schema/daml',
        'from_path': 'okns:daml'
    },
    'wfb': {
        'read_path': 'https://purl.org/okn/schema/wfb',
        'from_path': 'okns:wfb'
    },
    'vaem': {
        'read_path': 'https://purl.org/okn/schema/vaem',
        'from_path': 'okns:vaem'
    },
    'dtype': {
        'read_path': 'https://purl.org/okn/schema/dtype',
        'from_path': 'okns:dtype'
    },
    'swvs': {
        'read_path': 'https://purl.org/okn/schema/swvs',
        'from_path': 'okns:swvs'
    },
    'wgs': {
        'read_path': 'https://purl.org/okn/schema/wgs',
        'from_path': 'okns:wgs'
    },
    'ical': {
        'read_path': 'https://purl.org/okn/schema/ical',
        'from_path': 'okns:ical'
    },
    'wot': {
        'read_path': 'https://purl.org/okn/schema/wot',
        'from_path': 'okns:wot'
    },
    'xhv': {
        'read_path': 'https://purl.org/okn/schema/xhv',
        'from_path': 'okns:xhv'
    },
    'foaf': {
        'read_path': 'https://purl.org/okn/schema/foaf',
        'from_path': 'okns:foaf'
    },
    'cc': {
        'read_path': 'https://purl.org/okn/schema/cc',
        'from_path': 'okns:cc'
    },
    'frbr': {
        'read_path': 'https://purl.org/okn/schema/frbr',
        'from_path': 'okns:frbr'
    },
    'vann': {
        'read_path': 'https://purl.org/okn/schema/vann',
        'from_path': 'okns:vann'
    },
    'event': {
        'read_path': 'https://purl.org/okn/schema/event',
        'from_path': 'okns:event'
    },
    'address': {
        'read_path': 'https://purl.org/okn/schema/address',
        'from_path': 'okns:address'
    },
    'bibo': {
        'read_path': 'https://purl.org/okn/schema/bibo',
        'from_path': 'okns:bibo'
    },
    'frbroo': {
        'read_path': 'https://purl.org/okn/schema/frbroo',
        'from_path': 'okns:frbroo'
    },
    'cidoc-crm': {
        'read_path': 'https://purl.org/okn/schema/cidoc-crm',
        'from_path': 'okns:cidoc-crm'
    },
    'eli': {
        'read_path': 'https://purl.org/okn/schema/eli',
        'from_path': 'okns:eli'
    },
    'org': {
        'read_path': 'https://purl.org/okn/schema/org',
        'from_path': 'okns:org'
    },
    'sim': {
        'read_path': 'https://purl.org/okn/schema/sim',
        'from_path': 'okns:sim'
    },
    'rev': {
        'read_path': 'https://purl.org/okn/schema/rev',
        'from_path': 'okns:rev'
    },
    'ao': {
        'read_path': 'https://purl.org/okn/schema/ao',
        'from_path': 'okns:ao'
    },
    'mo': {
        'read_path': 'https://purl.org/okn/schema/mo',
        'from_path': 'okns:mo'
    },
    'sdo': {
        'read_path': 'https://purl.org/okn/schema/sdo',
        'from_path': 'okns:sdo'
    },
    'gr': {
        'read_path': 'https://purl.org/okn/schema/gr',
        'from_path': 'okns:gr'
    },
    'adms': {
        'read_path': 'https://purl.org/okn/schema/adms',
        'from_path': 'okns:adms'
    },
    'regorg': {
        'read_path': 'https://purl.org/okn/schema/regorg',
        'from_path': 'okns:regorg'
    },
    'void': {
        'read_path': 'https://purl.org/okn/schema/void',
        'from_path': 'okns:void'
    },
    'voag': {
        'read_path': 'https://purl.org/okn/schema/voag',
        'from_path': 'okns:voag'
    },
    'voaf': {
        'read_path': 'https://purl.org/okn/schema/voaf',
        'from_path': 'okns:voaf'
    },
    'qudt': {
        'read_path': 'https://purl.org/okn/schema/qudt',
        'from_path': 'okns:qudt'
    },
    'swrl': {
        'read_path': 'https://purl.org/okn/schema/swrl',
        'from_path': 'okns:swrl'
    },
    'biro': {
        'read_path': 'https://purl.org/okn/schema/biro',
        'from_path': 'okns:biro'
    },
    'c4o': {
        'read_path': 'https://purl.org/okn/schema/c4o',
        'from_path': 'okns:c4o'
    },
    'geo': {
        'read_path': 'https://purl.org/okn/schema/geo',
        'from_path': 'okns:geo'
    },
    'iospress': {
        'read_path': 'https://purl.org/okn/schema/iospress',
        'from_path': 'okns:iospress'
    },
    'gnis-ld-usgs': {
        'read_path': 'https://purl.org/okn/schema/gnis-ld-usgs',
        'from_path': 'okns:gnis-ld-usgs'
    },
    'gnis-ld-gnis': {
        'read_path': 'https://purl.org/okn/schema/gnis-ld-usgs',
        'from_path': 'okns:gnis-ld-gnis'
    },
    'kwg': {
        'read_path': 'https://purl.org/okn/schema/kwg',
        'from_path': 'okns:kwg'
    },
    # iof
    # bfo
    # ro
    # obi
    # sio
    # bao
    # cheminf
}
