def print_ast(root_node):
    # --- PASO 1: Recolectar filas (Recursión) ---
    # Guardaremos tuplas: (texto_con_ramas, detalle_del_nodo)
    rows = []

    def walk(node, indent="", is_last=True, is_root=True):
        # 1. Elegir el prefijo
        if is_root:
            marker = ""
        else:
            marker = "└─ " if is_last else "├─ "
        
        # 2. Construir el nombre visual (Ramas + Tipo de Nodo)
        node_name = node.__class__.__name__
        full_name = indent + marker + node_name
        
        # 3. Obtener detalle personalizado (o vacío si no tiene)
        detail = ""
        if hasattr(node, "get_details"):
            detail = str(node.get_details())
        elif hasattr(node, "value"):
            detail = str(node.value)
            
        rows.append((full_name, detail))

        # 4. Procesar hijos de forma genérica
        children = []
        if hasattr(node, "get_children"):
            children = node.get_children()
        
        # Filtrar por si acaso algún hijo es None (ej: un 'else' opcional)
        if children is None: return
        children = [c for c in children if c is not None]

        if children:
            new_indent = indent
            if not is_root:
                new_indent += "   " if is_last else "│  "
            
            for i, child in enumerate(children):
                last_child = (i == len(children) - 1)
                walk(child, new_indent, last_child, False)

    # Ejecutar la recolección
    walk(root_node)

    # --- PASO 2: Calcular anchos y Dibujar ---
    h_type, h_det = "NODE TYPE", "VALUE / DETAIL"
    w_type = len(h_type)
    w_det = len(h_det)

    for name, detail in rows:
        if len(name) > w_type: w_type = len(name)
        if len(detail) > w_det: w_det = len(detail)

    # Separador manual
    sep = ""
    while len(sep) < (w_type + w_det + 3): sep += "-"

    # Funciones de padding puras
    def pad(text, width):
        t = str(text)
        while len(t) < width: t += " "
        return t

    # --- PASO 3: Imprimir ---
    print("\n[ ABSTRACT SYNTAX TREE ]")
    print(sep)
    print(pad(h_type, w_type) + " | " + pad(h_det, w_det))
    print(sep)
    for name, detail in rows:
        print(pad(name, w_type) + " | " + pad(detail, w_det))
    print(sep + "\n")