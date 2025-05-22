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
