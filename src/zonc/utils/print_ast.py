from zonc.zonast import Node
from enum import Enum
from zonc.location_file import Span

def print_ast(node, indent="", is_last=True):
    """
    Pretty-print an AST tree, now supporting lists of tuples [(), ()].
    """
    if node is None:
        return

    node_name = node.__class__.__name__
    branch = "└── " if is_last else "├── "
    print(indent + branch + node_name)

    new_indent = indent + ("    " if is_last else "│   ")
    children = []

    # Función auxiliar para extraer nodos de estructuras anidadas (listas/tuplas)
    def collect_nodes(item, attr_name):
        if isinstance(item, (list, tuple)):
            for sub_item in item:
                collect_nodes(sub_item, attr_name)
        elif hasattr(item, "__dict__"):
            children.append((attr_name, item))
        else:
            # Si es un valor simple dentro de una tupla/lista que no es un objeto
            print(new_indent + f"├── {attr_name} (val): {item}")

    for attr, value in vars(node).items():
        if isinstance(value, Enum):
            print(new_indent + f"├── {attr}: {value.name}")
        elif isinstance(value, (list, tuple)):
            # Procesar la lista o lista de tuplas
            for item in value:
                if isinstance(item, (list, tuple)):
                    # Caso específico: lista de tuplas [ (nodo, nodo), (nodo, val) ]
                    collect_nodes(item, attr)
                elif hasattr(item, "__dict__"):
                    children.append((attr, item))
                else:
                    print(new_indent + f"├── {attr}: {item}")
        elif isinstance(value, Span):
            print(new_indent + f"├── {attr}")
            print(new_indent + "    " + f"├── start: {value.start}")
            print(new_indent + "    " + f"├── end: {value.end}")
        elif hasattr(value, "__dict__"):
            children.append((attr, value))
        else:
            # Atributo hoja simple
            print(new_indent + f"├── {attr}: {value}")

    # Imprimir los nodos hijos recolectados
    for i, (_, child) in enumerate(children):
        print_ast(child, new_indent, i == len(children) - 1)

