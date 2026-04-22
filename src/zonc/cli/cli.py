import sys
from .cmd_zonc import cmd_zon_run, cmd_zon_version, cmd_zon_help, cmd_zon_set_path, cmd_zon_show_path, cmd_zon_clear_path
from .cmd_zonc import cmd_zon_set_file, cmd_zon_compile
from zonc.utils import levenshtein_zon
from .cmdregistry import COMMANDS

def run_cli():
    args = sys.argv[1:]
    if len(args) == 0:
        print("[zon error]: No command or file specified.")
        print("-- The forge is idle. Use zon help to learn the commands and start building.")
        return
    
    if args[0] == 'rin':
        if len(args) < 2:
            print("[zon error]: No file specified for the run command.")
            print("-- The engine needs a target. Use zon rin <filename>.zon to start execution.")
            return
        
        cmd_zon_run(args[1])
        
    elif args[0] == 'c':
        path = args[1:]
        if len(path) < 1:
            print("[zon error]: No file specified for the compile command.")
            print("-- The engine needs a target. Use zon c <filename>.zon to start execution.")
            return
        
        cmd_zon_compile(path[0])
        
    elif args[0] == "help":
        params = args[1:]
        if len(params) > 0:
            cmd_zon_help(params[0], COMMANDS)
            return
        
        cmd_zon_help(commands=COMMANDS)
        return
    
    elif args[0] == "st":
        flag = args[1:]
        if len(flag) < 1:
            print("[zon error]: No flag provided for st command")
            print("-- Usage: zon st <flag>")
            return
        
        if args[1] == "--path":
            path = args[2:]
            if len(path) < 1:
                print("[zon error]: No path provided for st --path.")
                print("-- Usage: zon st --path </path/to/your/scripts>")
                return

            cmd_zon_set_path(path[0])
            
        elif args[1] == "--file":
            path = args[2:]
            if len(path) < 1:
                print("[zon error]: No path or filename specified.")
                print("-- Usage: zon st --file <path/to/folder/script.zon>")
                return
            
            keyend = args[3:]
            if len(keyend) < 1:
                cmd_zon_set_file([args[2], "EOF"], 0)
            else:
                cmd_zon_set_file(args[2:4], 0)
            
        elif args[1] == "--zbc":
            path = args[2:]
            if len(path) < 1:
                print("[zon error]: No path or filename bytecode specified.")
                print("-- Usage: zon st --zbc <path/to/folder/script.zon>")
                return
            
            keyend = args[3:]
            print(keyend)
            if len(keyend) < 1:
                cmd_zon_set_file([args[2], "EOF"], 4)
            else:
                cmd_zon_set_file(args[2:4], 4)
        
        else:
            list_commands = ["--file", "--path", "--zbc"]
            leven = levenshtein_zon.suggest_command(args[1], list_commands, 5)
            if leven is None: leven = "Use zon help to see the available commands."
            else: leven = leven = f"Did you mean?: {leven}"
            
            
            print(f"[zon error]: Unknown flag '{args[1]}' for area '{args[0]}'.")
            print(f"-- The forge doesn't recognize that instruction in this sector. {leven}")
            return
        
    elif args[0] == "vw":
        flag = args[1:]
        if len(flag) < 1:
            print("[zon error]: No flag provided for vw command")
            print("-- Usage: zon vw <flag>")
            return
        
        match args[1]:
            case "--path": cmd_zon_show_path()
            case "--vers": cmd_zon_version()
            case "--ast":
                path = args[2:]
                if len(path) < 1:
                    print("[zon error]: No file specified for the ast command.")
                    print("--Usage zon vw --ast <path>")
                    return
                cmd_zon_run(path[0], "ast")
                
            case "--tokens":
                path = args[2:]
                if len(path) < 1:
                    print("[zon error]: No file specified for the tokens command.")
                    print("--Usage zon vw --ast <path>")
                    return
                cmd_zon_run(path[0], "token")
                
            case _:
                list_commands = ["--file", "--path", "--tokens", "--ast", "--vers"]
                leven = levenshtein_zon.suggest_command(args[1], list_commands, 5)
                if leven is None: leven = "Use zon help to see the available commands."
                else: leven = leven = f"Did you mean?: {leven}"
                
                
                print(f"[zon error]: Unknown flag '{args[1]}' for area '{args[0]}'.")
                print(f"-- The forge doesn't recognize that instruction in this sector. {leven}")
                return
                  
    elif args[0] == "clr":
        flag = args[1:]
        if len(flag) < 1:
            print("[zon error]: No flag provided for clr command")
            print("-- Usage: zon clr <flag>")
            return
        
        if args[1] == "--path":
            cmd_zon_clear_path()
        else:
            list_commands = ["--his", "--path"]
            leven = levenshtein_zon.suggest_command(args[1], list_commands, 5)
            if leven is None: leven = "Use zon help to see the available commands."
            else: leven = leven = f"Did you mean?: {leven}"
            
            
            print(f"[zon error]: Unknown flag '{args[1]}' for area '{args[0]}'.")
            print(f"-- The forge doesn't recognize that instruction in this sector. {leven}")
            return
            
    elif args[0] == "repl":
        if args[1] == "--in":
            endkey = args[2:]
            if len(endkey) < 1:
                cmd_zon_set_file(["EOF"], mode=1)
            else:
                cmd_zon_set_file(args[2:3], 1)
            
        else:
            endkey = args[2:]
            if len(endkey) < 1:
                cmd_zon_set_file([args[1], "EOF"], mode=3)
            else:
                cmd_zon_set_file(args[1:3], mode=3)
                
    else:
        list_commands = []
        for key in COMMANDS:
            if key == "r|run":
                list_commands.append("r")
                list_commands.append("run")
                continue
            list_commands.append(key)
        
        leven = levenshtein_zon.suggest_command(args[0], list_commands, 5)
        if leven is None: leven = "Use zon help to see the available commands."
        else: leven = leven = f"Did you mean?: {leven}"
            
        print("[zon error]: Unknown command.")
        print(f"-- The forge doesn't recognize that instruction. {leven}")