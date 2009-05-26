def uniquify(seq):
    """Returns a unique list.  This preserves order"""
    seen = {}
    result = []
    for item in seq:
        if item in seen: continue
        seen[item] = 1
        result.append(item)
    return result
