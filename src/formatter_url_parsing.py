import re
from collections import defaultdict
from urllib.parse import urlparse

def get_formatter_urls(filepath='query.tsv'):
    formatter_mappings = defaultdict(set)

    with open(filepath) as f:
        next(f) # skip header
        for line in f:
            prop, formatter, formatter_type, prefix = line.strip('\n').split('\t')
            if not prop.startswith('http://www.wikidata.org/entity/P'):
                continue

            if not '$1' in formatter:
                continue
            parsed_iri = urlparse(formatter)
            if '$1' in parsed_iri.netloc:
                continue

            formatter_regex = re.compile(re.escape(formatter).replace('\$1','(.*)'))

            formatter_mappings[parsed_iri.netloc].add((prop, formatter_regex, formatter_type))
            if prefix != '':
                identifiers_org_formatter = re.compile(re.escape('https://identifiers.org/') + prefix + ':(.*)')
                formatter_mappings['identifiers.org'].add((prop, identifiers_org_formatter, 'http://www.wikidata.org/entity/P4793'))

    return formatter_mappings