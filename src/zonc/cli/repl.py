from .cmd_zonc import cmd_akorn_help, cmd_akorn_run, cmd_akorn_version

def repl():
    while True:
        cmd = input(">> ")
        
        args = cmd.split(" ")
        
        if len(args) <= 1:
            print("Usage: [command]")
            continue
        
        if args[0] == "exit":
            break
        
        elif args[0] == "run":
            try:
                cmd_akorn_run(args[1])
            except IndexError:
                print("Usage: run [rute script akon]")
            
        elif args[0] == "token":
            try:
                cmd_akorn_run(args[1], "token")
            except IndexError:
                print("Usage: token [rute script akon]")
        
        elif args[0] == "ast":
            try:
                cmd_akorn_run(args[1], "ast")
            except IndexError:
                print("Usage: ast [rute script akon]")
        
        elif args[0] == "smt":
            try:
                cmd_akorn_run(args[1], "smt")
            except IndexError:
                print("Usage: smt [rute script zonetic]")
        
        elif args[0] == "version":
            cmd_akorn_version()
        
        elif args[0] == "help":
            cmd_akorn_help()
