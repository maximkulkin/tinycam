def index_if(items, predicate, missing=-1):
    for index, item in enumerate(items):
        if predicate(item):
            return index

    return missing


def find_if(items, predicate, missing=None):
    for item in items:
        if predicate(item):
            return item

    return missing
