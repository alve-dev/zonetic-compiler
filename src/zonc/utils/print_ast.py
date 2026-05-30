def print_ast(root_node):
    rows = []

    def walk(node, indent="", is_last=True, is_root=True):
        if is_root:
            marker = ""
        else:
            marker = "└─ " if is_last else "├─ "
        
        node_name = node.__class__.__name__
        full_name = indent + marker + node_name
        
        detail = ""
        if hasattr(node, "get_details"):
            detail = str(node.get_details())
        elif hasattr(node, "value"):
            detail = str(node.value)
            
        rows.append((full_name, detail))

        children = []
        if hasattr(node, "get_children"):
            children = node.get_children()
        
        if children is None: return
        children = [c for c in children if c is not None]

        if children:
            new_indent = indent
            if not is_root:
                new_indent += "   " if is_last else "│  "
            
            for i, child in enumerate(children):
                last_child = (i == len(children) - 1)
                walk(child, new_indent, last_child, False)

    walk(root_node)

    h_type, h_det = "NODE TYPE", "VALUE / DETAIL"
    w_type = len(h_type)
    w_det = len(h_det)

    for name, detail in rows:
        if len(name) > w_type: w_type = len(name)
        if len(detail) > w_det: w_det = len(detail)

    sep = ""
    while len(sep) < (w_type + w_det + 3): sep += "-"

    def pad(text, width):
        t = str(text)
        while len(t) < width: t += " "
        return t

    print("\n[ ABSTRACT SYNTAX TREE ]")
    print(sep)
    print(pad(h_type, w_type) + " | " + pad(h_det, w_det))
    print(sep)
    for name, detail in rows:
        print(pad(name, w_type) + " | " + pad(detail, w_det))
    print(sep + "\n")