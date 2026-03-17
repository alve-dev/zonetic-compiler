from zonc.cli import run_cli

def main():
    run_cli()

if __name__ == "__main__":
    main()
    
    """Python match version
    match x:
        case 1:
            print("Es 1")
        case 2:
            print(" Es 2")
        case 3:
            print("Es 3")
        case _:
            print("No se que es voy a esplotar..")
            explotar()
            break
    """
        
    """Akon version match
    match (x)
    {
        1 => write("Es 1");
        2 => write("Es 2");
        3 => write("Es 3");
        default => {
            write("No se que es voy a explotar...");
            explotar();
        }
    }
    
    
    let int number = match x
    {
        1 => give 10;
        2 => give 20;
        3 => give 30;
        4 => give 40;
        5 => give 50;
        default => {
            write("Desconocido");
            give 0;
        }
    }
    
    //ejemplo de array
    python::lista = [1, 2, 3]
    akon::var array<int, 3> lista = [1, 2, 3];
    
    python::print(lista[1]) //output: 2
    akon::write(lista[1]) //output: 2
    
    python::lista.append(4) //lista[1, 2, 3, 4]
    akon::lista.push(4) //lista[1, 2, 3, 4]
    
    python::lista.pop(2) //[1, 2, 4]
    akon::lista.remove(2) //lista[1, 2, 4]
    
    python::lista_2d = [[1, 2, 3], [4, 5, 6]]
    akon::var array<int, [3, 3]> lista_2 = [[1, 2, 3], [4, 5, 6]];
    
    python:list_2d[1][2] //elemento numero 3 de la lista numero 2: 3
    akon:list_2d[1, 2] //elemento numero (1 + 1) * (2 + 1) - 1 osea el elemento numero 6(index 5) en una lista lineal = [1, 2, 3, 4, 5, 6]
    
    """