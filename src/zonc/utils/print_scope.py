from zonc.enviroment import Enviroment

def print_scope(env: Enviroment):
    scope = env.scope
    
    for obj in scope.keys():
        print(f"{obj}:", "{", sep="")
        for attributes in scope[obj].keys():
            print(f"    {attributes} : {scope[obj][attributes]}")
        print("}")
    
    
    