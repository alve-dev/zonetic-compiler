from .error_code import ErrorCode
from .error_definition import ErrorDefinition
from .severity import Severity

ERROR_REGISTRY: dict[ErrorCode, ErrorDefinition] = {
    ErrorCode.E0001 : ErrorDefinition(
        error_code=ErrorCode.E0001,
        severity=Severity.ERROR,
        message="I found an unexpected `{char}` character.",
        note = "Zonetic does not support or use the `{char}` character for this operation.",
        zonny= """
        [ ~_~] <("I don't recognize `{char}` in this context. Just delete the 
                 character so we can both move on with our lives.")"""
    ),
    
    ErrorCode.E0002 : ErrorDefinition(
        error_code=ErrorCode.E0002,
        severity=Severity.ERROR,
        message="I'm still waiting for you to close this comment.",
        note="Zonetic multiline comments must be explicitly closed with the `|-` token.",
        zonny="""
        [ ~_~] <("You started a comment but never finished it. I've reached the 
                 end of the file and I'm still waiting for that `|-`. 
                 Finish your sentence so I can go back to work!.")"""
    ),
    
    ErrorCode.E0003 : ErrorDefinition(
        error_code=ErrorCode.E0003,
        severity=Severity.ERROR,
        message="I encountered an escape sequence I don't know: `{escape}`.",
        note=rf"Zonetic only supports standard escape sequences like \n, \t, \, among others.",
        zonny="""
        [ ~_~] <("Is `{escape}` supposed to be some secret robot code? Because 
                 it's not in my manual. Just delete it or use a valid 
                 escape sequence so I can actually understand your text!.")"""
    ),
    
    ErrorCode.W0001 : ErrorDefinition(
        error_code=ErrorCode.W0001,
        severity=Severity.WARNING,
        message="Unnecessary escape character.",
        note="Zonetic allows using `{quote_escape}` inside `{quote_used}` strings (and vice-versa) without backslashes.",
        zonny="""
        [ ~_~] <("Why the `\\{quote_escape}`? You're already using {name_quote_used} quotes for the string. 
                 It's redundant and looks messy. Just delete the backslash 
                 and keep it simple, like I do with my ASCII face!.")"""
    ),
    
    ErrorCode.E0004 : ErrorDefinition(
        error_code=ErrorCode.E0004,
        severity=Severity.ERROR,
        message="I reached the end of the file looking for the closing {quote}, but never found it.",
        note="""
        In Zonetic, a string must be closed with the same quote it was opened with. 
        Without a closing {quote}, everything after the opening is consumed as part of the string.
        """,
        zonny="""
        [ ~_~] <("I read your entire file waiting for a {quote} that never came. 
                 Close your string before the end of the file.")"""
    ),
    
    ErrorCode.E0005 : ErrorDefinition(
        error_code=ErrorCode.E0005,
        severity=Severity.ERROR, 
        message="A floating point number can only have one decimal point, but I found more than one.",
        note="""
        In Zonetic, a float is written as digits, one `.`, and more digits. 
        Extra decimal points make the number invalid.""",
        zonny="""
        [ o_0] <("More than one dot in a number? Pick one decimal point 
                 and stick with it — remove the extra ones.")"""
    ),
    
    ErrorCode.E0006 : ErrorDefinition(
      error_code=ErrorCode.E0006,
      severity=Severity.ERROR,
      message="`{token}` is not a valid identifier — identifiers cannot start with a digit.",
      note="""
      In Zonetic, a valid identifier must start with a letter `a-z`, `A-Z`, or `_`. 
      Digits are allowed after the first character, but never at the start.""",
      zonny="""
      [ ~_~] <("`{token}` looks like you wanted an identifier but started with a number. 
               Flip it around — start with a letter or `_` 
               and put the digits after.")"""
    ),
    
    ErrorCode.E0007 : ErrorDefinition(
      error_code=ErrorCode.E0007,
      severity=Severity.ERROR,
      message="`{number}` uses `_` in an invalid position.",
      note="""
      In Zonetic, `_` is only allowed in integer literals to separate groups of thousands
      for readability — like `1_000_000`. It must appear between digit groups, never
      at the start, end, or in irregular positions like `10_0`.""",
      zonny="""
      [ ~_~] <("`_` is for making big numbers readable, not for decoration.
               Use it only to separate thousands — `1_000`, `10_000`, `1_000_000`.
               If that's not what you meant, just remove it.")"""
    ),
    
    ErrorCode.E0008 : ErrorDefinition(
      error_code=ErrorCode.E0008,
      severity=Severity.ERROR,
      message="`_` is not allowed in the decimal part of a float.",
      note="""
      In Zonetic, `_` is only allowed in the integer part of a number to separate
      thousands — `1_000.5` is valid, but `1_000.3_45` is not. The decimal part
      must always be written without underscores.""",
      zonny="""
      [ o_0] <("The integer part looks fine, but the decimal part has a `_` in it.
               Keep the underscores before the dot only —
               write the decimal digits without any separators.")"""
    ),
    
    ErrorCode.E0009 : ErrorDefinition(
      error_code=ErrorCode.E0009,
      severity=Severity.ERROR,
      message="`_` is not a valid identifier name.",
      note="""
      In Zonetic, while an identifier can start with `_`, it cannot 
      consist of only underscores. This is to ensure all variables 
      have a meaningful name for better code readability.""",
      zonny="""
      [ o_0] <("A single `_`? That's not a name, that's just a 
               placeholder! Give your variable a real name so 
               I know what it represents in your robot.")"""
    ),
    
    ErrorCode.E0010 : ErrorDefinition(
      error_code=ErrorCode.E0010,
      severity=Severity.ERROR,
      message="Scientific notation requires an exponent, but I found none.",
      note="""
      In Zonetic, when you use `e` or `E` for scientific notation, 
      you must follow it with an integer exponent (like `10e2` for 1000.0).""",
      zonny="""
      [ o_0] <("You started a scientific notation but left the 
               power hanging! Tell me the exponent, or if 
               you didn't mean to use it, just remove the `e/E`.")"""
    ),
    
    ErrorCode.E0011 : ErrorDefinition(
      error_code=ErrorCode.E0011,
      severity=Severity.ERROR,
      message="Exponents in scientific notation must be whole numbers.",
      note="""
      In Zonetic, the exponent (the part after the `e/E`) must be a 
      signed integer. Decimal points belong in the first part 
      of the number, not in the power.""",
      zonny="""
      [ ~_~] <("Whoa! Exponents are simple counters — they can't 
               have dots in them. Use a whole number after 
               the `e/E` and put the decimals in the first part.")"""
    ),
    
    ErrorCode.E0012 : ErrorDefinition(
      error_code=ErrorCode.E0012,
      severity=Severity.ERROR,
      message="Invalid character in scientific notation exponent.",
      note="""
      In Zonetic, the exponent part can only contain digits (0-9). 
      Symbols like `_` or extra letters are not allowed inside 
      the power for clarity.""",
      zonny="""
      [ >_<] <("Keep the exponent clean! Just use plain digits 
               after the `e/E`. No underscores, no letters, 
               just pure power!")"""
    ),
    
    ErrorCode.E1001 : ErrorDefinition(
        error_code=ErrorCode.E1001,
        severity=Severity.ERROR,
        message="I detected mixed statement terminator styles in this script.",
        note="""
        Zonetic supports hybrid statement terminators (newline or semicolon),
        but only one style may be used per script to preserve syntactic consistency and avoid ambiguity in normalization.""",
        zonny="""
        [ o_0] <("You used {mode_tr}… and then trusted a {used_tr}? Were you testing me?
                 Choose one terminator style per script: either explicit `;` or newline-based termination, but not both.")"""
    ),
    
    ErrorCode.E1002 : ErrorDefinition(
        error_code=ErrorCode.E1002,
        severity=Severity.ERROR,
        message="I found a semicolon where a statement cannot end.",
        note="""
        In Zonetic, the semicolon is a statement terminator. It is only valid at the end of a complete statement.
        Using it inside expressions or in isolation violates the syntactic structure expected by the normalizer.""",
        zonny="""
        [ ~_~] <("That semicolon looks confident… but it ends absolutely nothing.
                 A statement must exist before it. Remove the stray `;` or place it after a complete statement.")"""
    ),
    
    ErrorCode.E2001 : ErrorDefinition(
        error_code=ErrorCode.E2001,
        severity=Severity.ERROR,
        message="I was ready to create something, but you gave me no name.",
        note="""
        In Zonetic, every variable needs a label. I can't store data in a 'nothingness'.
        The syntax requires an identifier after `mut` or `inmut`.""",
        zonny="""
        [ o_0] <("Oh, great. You want a {name_mut}.. 'ghost'? 
                 I'm not a mind reader! I need a name to label 
                 this in my memory banks. Just add a name after 
                 `mut` or `inmut` so I know what to call it.")"""
    ),
    
    ErrorCode.E2002 : ErrorDefinition(
        error_code=ErrorCode.E2002,
        severity=Severity.ERROR,
        message="I found something that isn't a valid type right after your colon.",
        note="""
        In Zonetic, the `:` creates a contract. You promised me a data type here so I can allocate the right space in memory,
        but '{type}' doesn't match any type I know.""",
        zonny = """
        [ ~_0] <("You put `:` and then left me hanging with a mystery word!
                 If you're going to be explicit, actually be explicit! To fix this, either give me a valid type after 
                 the `:` or just delete the `:` entirely and let me use my super-brain to infer the type for you.")"""
    ), 

    ErrorCode.E2003 : ErrorDefinition(
        error_code=ErrorCode.E2003,
        severity=Severity.ERROR,
        message="I found an opening `(`, but you never closed the deal.",
        note="In Zonetic, every `(` needs a matching `)` to complete the expression.",
        zonny="""
        [ o_0] <("You left me hanging! A `(` without a `)` is like a robot with only one arm—it just doesn't work. 
                 Go back and close that parenthesis before I 
                 get an existential crisis.")"""
    ),
    
    ErrorCode.E2004 : ErrorDefinition(
        error_code=ErrorCode.E2004,
        severity=Severity.ERROR,
        message="I found `{token}` after a declaration, but I don't know what to do with it.",
        note="""
        In Zonetic, a declaration must end with `;` or newline to close the statement, 
        or `,` to continue with another declaration in the same line.""",
        zonny="""
        [ ~_~] <("I parsed your whole declaration and then you threw 
                 `{token}` at me. What am I supposed to do with that? 
                 End with `;`, a newline, or keep going with `,`.")"""
    ),
    
    ErrorCode.E2005 : ErrorDefinition(
        error_code=ErrorCode.E2005,
        severity=Severity.ERROR,
        message="Expected an expression, but found `{token}` instead.",
        note="In Zonetic, `{token}` cannot start an expression.",
        zonny="""
        [ o_0] <("`{token}`? That's not an expression, that's just 
                 chaos. Use a valid expression or check the N.E.R.T 
                 to see what I actually understand.")"""
    ),
    
    ErrorCode.E2006 : ErrorDefinition(
      error_code=ErrorCode.E2006,
      severity=Severity.ERROR,
      message="Expected an assignment operator after `{name}`, but found `{token}` instead.",
      note="""
      In Zonetic, after a variable name in an assignment, you must use a valid assignment operator.
      Currently supported: `=`, `+=`, `-=`, `*=`, `/=`, `//=`, `**=`, `%=`.""",
      zonny="""
      [ ~_~] <("`{token}` is a perfectly fine token... just not here. 
               After `{name}` I need an assignment operator, 
               not whatever that was supposed to be.")"""
    ),
    
    ErrorCode.E2007 : ErrorDefinition(
      error_code=ErrorCode.E2007,
      severity=Severity.ERROR,
      message="This block expression was expected to produce a value, but no `give` was found.",
      note="""
      In Zonetic, when a block expression is used in a value context — such as 
      an assignment or inside another expression — it must produce a value 
      using `give` as its last meaningful statement.""",
      zonny="""
      [ 0_0] <("You put a block here like it was going to give me something 
               and then just... nothing? Add a 'give' with the value 
               you want this block to produce.")"""
    ),
    
    ErrorCode.W2001 : ErrorDefinition(
      error_code=ErrorCode.W2001,
      severity=Severity.WARNING,
      message="`give` returned a value, but nothing is waiting for it.",
      note="""
      In Zonetic, `give` produces a value from a block expression. 
      When a block is used as a statement and not as a value, 
      any value produced by 'give' is simply lost.""",
      zonny="""
      [ o_0] <("You went through all the trouble of computing a value 
               just to throw it away? Remove the `give` — 
               the block will still run, the value just won't go anywhere.")""",
    ),
    
    ErrorCode.E2008 : ErrorDefinition(
      error_code=ErrorCode.E2008,
      severity=Severity.ERROR,
      message="I found an opening `{aux_r}`, but the block was never closed.",
      note="""In Zonetic, every block expression opened with `{aux_r}` must be closed with `{aux_l}`.""",
      zonny="""
      [ ~_~] <("You opened a block and just left it hanging. 
               I reached the end of the file still waiting for that `{aux_l}`. 
               Close your block before I lose my mind.")"""
    ),
    
    ErrorCode.E2009 : ErrorDefinition(
      error_code=ErrorCode.E2009,
      severity=Severity.ERROR,
      message="Expected `{aux_r}` to open a block expression, but found `{token}` instead.",
      note="""
      In Zonetic, every form or structure that requires a block must open it with '{aux_r}'. 
      After the form's signature — whether it includes a condition, parameters, or nothing at all — 
      a block expression must follow immediately.""",
      zonny="""
      [ o_0] <("I just finished reading the form signature and was ready for a `{aux_r}`, 
               but `{token}` showed up instead. 
               Open a block with `{aux_r}` right after the signature.")"""
    ),
    
    ErrorCode.E2010 : ErrorDefinition(
      error_code=ErrorCode.E2010,
      severity=Severity.ERROR,
      message="Unexpected `{token}` found where a statement was expected.",
      note="""
      In Zonetic, a statement must start with a recognized keyword or construct — 
      such as `mut`, `inmut`, `if`, a block expression, or a variable name for assignment.""",
      zonny="""
      [ 0_0] <("`{token}`? I was ready for a statement and you gave me that. 
               Check what you wrote — something here doesn't belong.")"""
    ),
    
    ErrorCode.E2011 : ErrorDefinition(
      error_code=ErrorCode.E2011,
      severity=Severity.ERROR,
      message="`{keyword}` found without an opening `if`.",
      note="""
      In Zonetic, `elif` and `else` can only appear as continuation 
      branches of an existing if form opened with `if`.""",
      zonny="""
      [ 0_0] <("`{keyword}` just showed up out of nowhere. 
               I need an `if` to open the form first — 
               `{keyword}` can't exist without one.")"""
    ),
    
    ErrorCode.E2012 : ErrorDefinition(
      error_code=ErrorCode.E2012,
      severity=Severity.ERROR,
      message="`give` can only be used inside a block expression.",
      note="""
      In Zonetic, `give` is a block-level statement — it produces a value from 
      the block it belongs to. Using it outside of a block expression has no meaning, 
      as there is no block to return from.""",
      zonny="""
      [ 0_0] <("`give`? There's no block here for me to return from. 
               `give` only makes sense inside a `{ }` — 
               wrap your code in a block or remove the `give`.")"""
    ),
    
    ErrorCode.E2013 : ErrorDefinition(
      error_code=ErrorCode.E2013,
      severity=Severity.ERROR,
      message="Expected a function name after `func`, but found `{token}` instead.",
      note="In Zonetic, `func` must be followed by a valid identifier — the name of the function.",
      zonny="""
      [ o_0] <("A function with no name? How am I supposed to call it? 
               Give it a valid identifier right after `func`.")"""
    ),
    
    ErrorCode.E2014 : ErrorDefinition(
      error_code=ErrorCode.E2014,
      severity=Severity.ERROR,
      message="Expected `(` after function name `{name}`, but found `{token}` instead.",
      note="""
      In Zonetic, the function name must be followed by `(` to open the parameter list, 
      even if the function has no parameters.""",
      zonny="""
      [ ~_~] <("`{name}` needs a `(` right after it to open the parameter list. 
               Don't forget the closing `)` either — 
               I need both to know where the parameters start and end.")"""
    ),
    
    ErrorCode.E2015 : ErrorDefinition(
      error_code=ErrorCode.E2015,
      severity=Severity.ERROR,
      message="`struct` definitions must be at the top-level.",
      note="""
      In Zonetic, the `struct` keyword is used to define a global blueprint. 
      To keep the program structure predictable for robotics, types cannot 
      be hidden inside functions or local scopes.""",
      zonny="""
      [ ~_~] <("Whoa! You're trying to build a factory inside a room. 
               `{name}` belongs outside in the open air (global scope) 
               so everyone can see how it's made. Move the definition to the top!")"""
    ),
    
    ErrorCode.E2016 : ErrorDefinition(
      error_code=ErrorCode.E2016,
      severity=Severity.ERROR,
      message="Expected `mut` or `inmut` to start a parameter, but found `{token}` instead.",
      note="""
      In Zonetic, every parameter must start with a mutability keyword — `mut` or `inmut`. 
      A complete parameter follows this structure: `mut | inmut name: type [= default]`.""",
      zonny="""
      [ o_0] <("This isn't Python — parameters don't just start with a name here. 
               Begin with `mut` or `inmut` so I know 
               what I'm allowed to do with this parameter.")"""
    ),
    
    ErrorCode.E2017 : ErrorDefinition(
      error_code=ErrorCode.E2017,
      severity=Severity.ERROR,
      message="Expected a parameter name after `{mut_keyword}`, but found `{token}` instead.",
      note="In Zonetic, after the mutability keyword a valid identifier must follow — the name of the parameter.",
      zonny="""
      [ ~_~] <("You told me the mutability but forgot the name. 
               Give this parameter a valid identifier 
               so I know what to call it.")"""
    ),
    
    ErrorCode.E2018 : ErrorDefinition(
      error_code=ErrorCode.E2018,
      severity=Severity.ERROR,
      message="`void` is not valid here.",
      note="""
      In Zonetic, `void` is only valid as a function return type after `->`. 
      It cannot be used as a variable type or a parameter type — 
      `void` means the absence of a value, not a type you can hold.""",
      zonny="""
      [ 0_0] <("`void` means nothing — literally. 
               You can't store nothing in a variable or pass nothing as a parameter. 
               `void` only makes sense after `->` to say a function returns nothing.")"""
    ),
    
    ErrorCode.E2019 : ErrorDefinition(
      error_code=ErrorCode.E2019,
      severity=Severity.ERROR,
      message="`{type}` is not a valid type for a parameter.",
      note="""
      In Zonetic, parameter types are always required and must be a valid type. 
      Unlike variables, parameters cannot have their type inferred — 
      every parameter must declare its type explicitly.""",
      zonny="""
      [ o_0] <("`{type}` is not a type I know. 
               Parameters have no inference — you have to be explicit here. 
               Use a valid type and check the types doc if you're not sure.")"""
    ),
    
    ErrorCode.E2020 : ErrorDefinition(
      error_code=ErrorCode.E2020,
      severity=Severity.ERROR,
      message="Expected `:` after parameter name `{name}` to declare its type.",
      note="""
      In Zonetic, parameter types are always required. Unlike variables, parameters 
      cannot be left without a type — use `:` followed by a valid type to declare it.""",
      zonny="""
      [ ~_~] <("`{name}` needs a type — I can't infer it here. 
               Add `:` followed by a valid type 
               and I'll know exactly what to expect.")"""
    ),
    
    ErrorCode.E2021 : ErrorDefinition(
      error_code=ErrorCode.E2021,
      severity=Severity.ERROR,
      message="Expected `->` after the parameter list, but found `{token}` instead.",
      note="""
      In Zonetic, every function must declare its return type explicitly using `->`. 
      Use `-> void` if the function returns nothing.""",
      zonny="""
      [ ~_~] <("The parameter list closed fine but then `{token}` showed up. 
               I need `->` to know what this function returns — 
               even if it's `-> void`.")"""
    ),
    
    ErrorCode.E2022 : ErrorDefinition(
      error_code=ErrorCode.E2022,
      severity=Severity.ERROR,
      message="Expected a valid return type after `->'`, but found `{token}` instead.",
      note="""
      In Zonetic, `->` must be followed by a valid type or `void`. 
      Every function return type is always explicit — there is no inference here.""",
      zonny="""
      [ o_0] <("`->` was there, that's great, but `{token}` is not a valid return type. 
          Use a valid type or `void` if this function 
          returns nothing.")"""
    ),
    
    ErrorCode.E2023 : ErrorDefinition(
      error_code=ErrorCode.E2023,
      severity=Severity.ERROR,
      message="Parameter `{name}` was already passed in this call.",
      note="""
      In Zonetic, each parameter can only receive one value per call. 
      `{name}` appears more than once — remove the duplicate.""",
      zonny="""
      [ ~_~] <("`{name}` already has a value in this call. 
               You can't pass it twice — pick one and remove the other.")"""
    ),
    
    ErrorCode.E2024 : ErrorDefinition(
      error_code=ErrorCode.E2024,
      severity=Severity.ERROR,
      message="Positional parameter found after a keyparam — all following parameters must be keyparams.",
      note="""
      In Zonetic, once a keyparam is used in a call, every following parameter 
      must also be passed by name. Mixing back to positional is not allowed.""",
      zonny="""
      [ ~_~] <("You switched to keyparams and then went back to positional. 
               Once you name one, name them all — 
               use `name = value` for every remaining parameter.")"""
    ),
    
    ErrorCode.E2025 : ErrorDefinition(
      error_code=ErrorCode.E2025,
      severity=Severity.ERROR,
      message="Expected `,` or `)` after parameter, but found `{token}` instead.",
      note="""
      In Zonetic, parameters must be separated by `,` and the list 
      must always be closed with `)` — both in function declarations and calls.""",
      zonny="""
      [ ~_~] <("I just read a parameter and then `{token}` showed up. 
               Use `,` to continue the parameter list 
               or `)` to close it.")"""
    ),
    
    ErrorCode.E2026 : ErrorDefinition(
      error_code=ErrorCode.E2026,
      severity=Severity.ERROR,
      message="`return` found outside of any block.",
      note="""
      In Zonetic, 'return' can only be used inside a function body. 
      It has no meaning outside of a block expression.""",
      zonny="""
      [ 0_0] <("'return' with nowhere to return from. 
               Put it inside a function body — 
               outside of a block it does absolutely nothing.")"""
    ),
    
    ErrorCode.E2027 : ErrorDefinition(
      error_code=ErrorCode.E2027,
      severity=Severity.ERROR,
      message="Expected an identifier after `struct`.",
      note="""
      In Zonetic, every 'struct' requires a unique name to identify the data 
      structure. This name is used throughout the program to create 
      instances.""",
      zonny="""
      [ o_0] <("You're defining a struct but forgot to give it a name! 
               How am I supposed to know what this is? 
               Give it a valid name like 'Motor' or 'Sensor' right after 'struct'.")"""
    ),
    
    ErrorCode.E2028 : ErrorDefinition(
      error_code=ErrorCode.E2028,
      severity=Severity.ERROR,
      message="Invalid field access syntax.",
      note="""
      In Zonetic, and in programming in general—just like in natural 
      languages—grammatical rules are fundamental to understand what 
      is being said. The dot operator `.` must always be followed by 
      a valid identifier (a name), not a keyword or a symbol, etc.""",
      zonny="""
      [ o_0] <("I'm lost! You put a dot but then said something that 
               doesn't look like a field name. If you're trying to 
               access an object's data, make sure to use a proper 
               name like `object.field`.")"""
    ),
    
    ErrorCode.E2029 : ErrorDefinition(
      error_code=ErrorCode.E2029,
      severity=Severity.ERROR,
      message="Field `{field}` was already assigned in this constructor.",
      note="""
      In Zonetic, each field in a constructor can only receive one 
      initial value. Even if the field is `mut`, you must provide 
      a single starting value inside the curly braces `{{ }}`.""",
      zonny="""
      [ ~_~] <("You're trying to give `{field}` two values at once! 
               A constructor is for setting the first value, not 
               starting a fight. Pick one and delete the duplicate.")"""
    ),
    
    ErrorCode.E2030 : ErrorDefinition(
      error_code=ErrorCode.E2030,
      severity=Severity.ERROR,
      message="Positional field assign found after a keyword assign.",
      note="""
      In Zonetic, once a keyword (like `field = value`) is used in a 
      constructor, all following assignments must also use keywords. 
      Mixing positional and keyword styles is not allowed.""",
      zonny="""
      [ ~_~] <("You started naming fields and then just threw '{token}' at me! 
               Once you name one, you have to name them all. 
               Use 'field = value' for the rest of this object.")"""
    ),
    
    ErrorCode.E2031 : ErrorDefinition(
      error_code=ErrorCode.E2031,
      severity=Severity.ERROR,
      message="Expected `,` or `]` after field assign, but found `{token}` instead.",
      note="""
      In Zonetic, field assignments in a constructor must be separated 
      by `,` (or a new line) and the entire block must be closed 
      with `]`. The compiler found something else that doesn't 
      belong in the object's box.""",
      zonny="""
      [ ~_~] <("I just finished an assignment and then `{token}` showed up 
               out of nowhere. Use `,` to add another field 
               or `]` to close the constructor!")"""
    ),
    
    ErrorCode.E2032 : ErrorDefinition(
      error_code=ErrorCode.E2032,
      severity=Severity.ERROR,
      message="Field access `{expr}` used as a statement.",
      note="""
      In Zonetic, accessing a field is an expression that returns a value. 
      To be a valid statement, you must either assign it a value (using `=`) 
      or call a method (using `()`). Standing alone, it doesn't 
      perform any action.""",
      zonny="""
      [ ~_~] <("I see you're looking at '{field}', but what's the plan? 
               You can't just leave it there! Assign it to something, 
               change its value, or call a method, but don't 
               leave it standing alone in the rain.")"""
    ),
        
    ErrorCode.E3001 : ErrorDefinition(
      error_code=ErrorCode.E3001,
      severity=Severity.ERROR,
      message="`{name}` was used but has never been declared.",
      note="""
      In Zonetic, a variable must be declared with `mut` or `inmut` before it can be used.
      Any attempt to read or write a name that does not exist in the current scope is an error.""",
      zonny="""
      [ o_0] <("`{name}`? I looked everywhere in this scope and I have 
               no idea who that is. Either declare it first with 
               `mut` or `inmut`, or check if you spelled it right.")"""
    ),
    
    ErrorCode.E3002 : ErrorDefinition(
      error_code=ErrorCode.E3002,
      severity=Severity.ERROR,
      message="`{name}` exists but has no value yet.",
      note="""
      In Zonetic, a variable must have a value before it can be used. 
      `{name}` was declared but never assigned a value at this point in the program.""",
      zonny="""
      [ o_0] <("`{name}` is right there in the scope, I can see it, 
               but it's completely empty. Give it a value before 
               trying to use it.")"""
    ),
    
    ErrorCode.E3003: ErrorDefinition(
      error_code=ErrorCode.E3003,
      severity=Severity.ERROR,
      message="Operand type mismatch in `{operator}`: expected {valid_types}, but found `{found_type}`.",
      note="""
      In Zonetic, the `{operator}` operator only accepts operands of type {valid_types}. 
      See the NERT for the full list of type rules for native expressions.""",
      zonny="""
      [ ~_~] <("`{found_type}` doesn't work with `{operator}`. 
               {valid_types} is what I need here — 
               make sure your expression returns the right type.")"""
    ),
    
    ErrorCode.E3004 : ErrorDefinition(
      error_code=ErrorCode.E3004,
      severity=Severity.ERROR,
      message="Operand type mismatch in `{operator}`: left is `{left_type}` but right is `{right_type}`.",
      note="""
      In Zonetic, both operands of `{operator}` must be of the same type. 
      Mixed-type operations are not allowed — use an explicit cast to convert 
      one operand before operating.""",
      zonny="""
      [ ~_~] <("`{left_type}` and `{right_type}` don't mix in `{operator}`. 
               Pick one type and cast the other — 
               I don't do implicit conversions.")"""
    ),
    
    ErrorCode.E3005 : ErrorDefinition(
      error_code=ErrorCode.E3005,
      severity=Severity.ERROR,
      message="`{name}` is a value and cannot be reassigned.",
      note="""
      In Zonetic, names declared with `inmut` are values — they can only be assigned once. 
      If you need a name that can change, declare it with `mut` instead.""",
      zonny="""
      [ ~_~] <("`{name}` was declared with `inmut` — that means no touching it again. 
               If you need it to change, go back and use `mut` when you declare it.")"""
    ),
    
    ErrorCode.E3006 : ErrorDefinition(
      error_code=ErrorCode.E3006,
      severity=Severity.ERROR,
      message="Cannot assign `{found_type}` to `{name}`, which expects `{expected_type}`.",
      note="""
      In Zonetic, a variable always keeps the same type it was declared or inferred with. 
      The value you are trying to assign does not match the type of `{name}`.""",
      zonny="""
      [ 0_0] <("`{name}` is a `{expected_type}` — you can't just hand it a `{found_type}`. 
               Either fix the expression or use a cast 
               to convert it to `{expected_type}` first.")"""
    ),
    
    ErrorCode.W3001 : ErrorDefinition(
      error_code=ErrorCode.W3001,
      severity=Severity.WARNING,
      message="Code after `give` will never execute.",
      note="""
      In Zonetic, 'give' exits the block immediately after producing its value. 
      Any statements below it inside the same block are unreachable.""",
      zonny="""
      [ ~_~] <("Everything below this 'give' is just sitting there doing nothing. 
               I'll never reach it — move it before the 'give' 
               or remove it entirely.")"""
    ),
    
    ErrorCode.E3007 : ErrorDefinition(
      error_code=ErrorCode.E3007,
      severity=Severity.ERROR,
      message="Condition field expects a `bool` expression, but found `{found_type}`.",
      note="""
      In Zonetic, a condition field only accepts expressions that return `bool`. 
      The expression provided returns `{found_type}`, which cannot be used 
      to make a decision. See condition_field_doc.md for more details.""",
      zonny="""
      [ o_0] <("I need a `bool` to make a decision here, 
               but you gave me a `{found_type}`. 
               I can't decide anything with that — 
               use an expression that returns `bool`.")"""
    ),
    
    ErrorCode.E3008 : ErrorDefinition(
      error_code=ErrorCode.E3008,
      severity=Severity.ERROR,
      message="This if form requires an `else` branch.",
      note="""
      In Zonetic, `else` is optional in most cases. However, when a variable declared 
      outside this if form receives its first assignment inside one of its branches, 
      an `else` branch is required. Without it, there is a path where that variable 
      remains empty after the if form.""",
      zonny="""
      [ ~_~] <("One of your variables is getting its first value inside here, 
               but what if none of the conditions are true? 
               Add an 'else' branch to cover that case.")"""
    ),
    
    ErrorCode.E3009 : ErrorDefinition(
      error_code=ErrorCode.E3009,
      severity=Severity.ERROR,
      message="`{name}` is assigned in some branches but not all — it may still be empty after this if form.",
      note="""
      In Zonetic, if a variable receives its first assignment inside an if form, 
      every branch must assign it — including 'else'. If even one branch skips it, 
      there is a chance '{name}' remains empty when that branch executes. 
      A variable with an existing value before the if form would not have this problem.""",
      zonny="""
      [ o_0] <("`{name}` gets a value in some branches but not others. 
               I can't guarantee it won't be empty — 
               assign it in every branch or give it a default value before the if form.")""",
    ),
    
    ErrorCode.E3010 : ErrorDefinition(
      error_code=ErrorCode.E3010,
      severity=Severity.ERROR,
      message="This if form is used as an expression but has no `else` branch.",
      note="""
      In Zonetic, when an if form is used as an expression, an `else` branch is always 
      required. Without it, there is a path where the if form produces no value, 
      leaving the program with nothing to work with. This guarantees the compiler 
      always has a safe exit and prevents runtime errors.""",
      zonny="""
      [ ~_~] <("You're using this if form as a value, but what if the condition is false? 
               I'd have nothing to return. 
               Add an 'else' branch so I always have something to give back.")"""
    ),
    
    ErrorCode.E3011 : ErrorDefinition(
      error_code=ErrorCode.E3011,
      severity=Severity.ERROR,
      message="Return type mismatch across branches in this if form expression.",
      note="""
      In Zonetic, when an if form is used as an expression, every branch must return 
      the same type. The first 'if' branch establishes the expected return type — 
      all 'elif' and 'else' branches must match it. This keeps the result type 
      predictable and safe.""",
      zonny="""
      [ o_0] <("Every branch promised me a value and then each one showed up 
               with something different. Pick a type and stick with it — 
               make all your 'give' statements return the same type as the first branch.")"""
    ),
    
    ErrorCode.W3002 : ErrorDefinition(
      error_code=ErrorCode.W3002,
      severity=Severity.WARNING,
      message="This condition is always `true` — all following branches are unreachable.",
      note="""
      In Zonetic, when an 'if' condition is a 'true' literal, the first block 
      always executes and every 'elif' and 'else' branch is never reached. 
      Consider removing the unreachable branches or replacing the condition 
      with a real expression.""",
      zonny="""
      [ ~_~] <("You wrote 'if true' — I'll always take this branch. 
               Everything after it is just decoration. 
               Remove the dead branches or use a real condition.")"""
    ),
    
    ErrorCode.W3003 : ErrorDefinition(
      error_code=ErrorCode.W3003,
      severity=Severity.WARNING,
      message="This condition is always `false` — the block will never execute.",
      note="""
      In Zonetic, when a condition field is a 'false' literal, the associated 
      block never executes. This is dead code — either fix the condition 
      or remove the block entirely.""",
      zonny="""
      [ ~_~] <("'false'? I'll never go in there. 
               This whole block is dead code — 
               fix the condition or just delete it.")"""
    ),
    
     ErrorCode.E3012 : ErrorDefinition(
      error_code=ErrorCode.E3012,
      severity=Severity.ERROR,
      message="`{keyword}` can only be used inside a loop.",
      note="""
      In Zonetic, `{keyword}` is a loop control statement — it only makes sense 
      inside a `while` or `infinity` form. Using it outside of a loop 
      has no effect and no meaning.""",
      zonny="""
      [ 0_0] <("There's no loop here for `{keyword}` to work with. 
               Move it inside a `while` or `infinity` — 
               or remove it if it doesn't belong.")"""
    ),
     
    ErrorCode.W3004 : ErrorDefinition(
      error_code=ErrorCode.W3004,
      severity=Severity.WARNING,
      message="This loop has no `break` statement — it may run forever.",
      note="""
      In Zonetic, a `while true` or `infinity` form with no `break` anywhere 
      in its block will run indefinitely. If this is intentional, you can 
      ignore this warning — otherwise add a `break` to exit the loop.""",
      zonny="""
      [ ~_~] <("I don't see a single `break` in here. 
               This loop is going to run forever and I can't stop it. 
               Add a `break` somewhere or I hope you like waiting.")"""
    ),
    
    ErrorCode.E3013 : ErrorDefinition(
      error_code=ErrorCode.E3013,
      severity=Severity.ERROR,
      message="The name `{name}` is already defined as a function.",
      note="""
      In Zonetic, function names are global and do not support shadowing.
      Unlike variables, once a name is assigned to a function, it cannot
      be reused for another `{kind}` in any scope to avoid ambiguity.""",
      zonny="""
      [ o_0] <("The name `{name}` is already taken by a function! I can't have two things
               named the same way, I'd get confused about which one to call.
               Give your new `{kind}` a unique name.")"""
    ),
    
    ErrorCode.E3014 : ErrorDefinition(
      error_code=ErrorCode.E3014,
      severity=Severity.ERROR,
      message="`return` statement found outside of a function.",
      note="""
      In Zonetic, the `return` keyword is strictly reserved for exiting
      functions and passing a result to the caller. Even inside  an `if`, `while`,
      `for`, etc., `return` can only be used if  those blocks are nested within a
      `func` declaration.""",
      zonny="""
      [ o_0] <("You're trying to `return` from here, but I can't find a function to
               exit from! If you just want to stop this block, remove  this `return`. If you're
               trying to yield a value from a block expression, use `give` instead.")"""
    ),
    
    ErrorCode.E3015 : ErrorDefinition(
      error_code=ErrorCode.E3015,
      severity=Severity.ERROR,
      message="Mismatched return type in function `{func_name}`.",
      note="""
      In Zonetic, every function must strictly follow its return contract.
      The type defined after `->` must match the value in the `return` statement.
      If the function is `void`, no value should be  returned. Check NERT (Native
      Expression Return Types) documentation to verify what each expression returns.""",
      zonny="""
      [ ~_~] <("You promised `{func_name}` would return `{expected}`, but you gave me
               `{found}`! A robot needs to know exactly what it's getting to avoid a short
               circuit. Change the expression to  match `{expected}` or, if it's `void`, just
               use `return`.")"""
    ),
    
    ErrorCode.W3005 : ErrorDefinition(
      error_code=ErrorCode.W3005,
      severity=Severity.WARNING,
      message="Unreachable code after `return` statement.",
      note="""
      In Zonetic, a `return` statement immediately exits the current
      function. Everything below this line, until the closing brace  `{aux}` of the `func`
      body, is dead code. It will be ignored by  the compiler and excluded from the
      final binary, which might lead to confusion if you expect it to run.""",
      zonny="""
      [ -_-] <("Once I hit this 'return', I'm jumping straight out of the function!
               Anything you wrote between here and the final '{aux}'  is invisible to me. If you
               need that code to run, move it  above the 'return' or delete it to keep things
               clean.")"""
    ),
    
    ErrorCode.E3016 : ErrorDefinition(
      error_code=ErrorCode.E3016,
      severity=Severity.ERROR,
      message="illegal immutable initialization in loop.",
      note="""
      In Zonetic, loops are unpredictable. Initializing an outer `inmut` here 
      could leave it empty or force a re-assignment. Use `mut` for external 
      changes or declare a local `inmut` inside the loop.""",
      zonny="""
      [ 0_0] <("You're gambling with immutability! If the loop never runs, the 
               variable stays empty; if it runs twice, it's no longer 'inmut'.
               Don't make me guess! Use `inmut` inside the loop if you need it 
               locally, or switch to `mut` if it must change. Keep your outer 
               `inmut` for read-only values!")"""
    ),
    
    ErrorCode.E3017 : ErrorDefinition(
      error_code=ErrorCode.E3017,
      severity=Severity.ERROR,
      message="You cannot declare a function inside another function.",
      note="""
      In Zonetic, all functions must be declared at the top level. Nested
      functions are not supported because they don't add any real value that can't be
      achieved with global functions, and keeping them separate makes the code and 
      the compiler much cleaner for everyone.""",
      zonny="""
      [ ~_~] <("A function inside a function? No thanks. In Zonetic we keep things
               simple and organized. Move `{inner_name}` to the top level and just call it from
               here. It's better for you and better for me.")"""
    ),
    
    ErrorCode.E3018 : ErrorDefinition(
      error_code=ErrorCode.E3018,
      severity=Severity.ERROR,
      message="`give` used in a non-expression block.",
      note="""
      In Zonetic, `give` is specifically designed to yield a value from an
      expression block (like an `if` or `infinity` assigned to a variable). A function
      body is a statement block, not an  expression. If you want to return a value to
      the caller, use `return`.""",
      zonny="""
      [ o_0] <("You're using `give` inside a function body, but there's no variable
               waiting for this value! It's like trying to  hand a wrench to a robot that hasn't
               reached out its arm. Use `return` if you're finished here, or move this `give`
               inside a valid expression block.")"""
    ),
    
    ErrorCode.E3019 : ErrorDefinition(
      error_code=ErrorCode.E3019,
      severity=Severity.ERROR,
      message="Function `{func_name}̣` does not return a value in all code paths.",
      note="""
      In Zonetic, if a function is defined to return a type, it MUST do so in
      every possible scenario. If the `if` condition fails and there is no `else` or a
      final `return` at the  end of the function, the program wouldn't know what to 
      send back to the caller""",
      zonny="""
      [ O_O] <("What happens if the 'if' is false? You're leaving me hanging! If I
               don't enter that block, I have nothing to  return. Either add an `else` with its
               own `return` or put a default `return` at the very bottom of the function.")"""
    ),
    
    ErrorCode.W3006 : ErrorDefinition(
      error_code=ErrorCode.W3006,
      severity=Severity.WARNING,
      message="Unreachable code detected after {keyword}.",
      note="""
      In Zonetic, once a {keyword} is reached, the flow of control immediately jumps out of the block.
      Any instructions placed after it are "dead code" because there is no logical path that can ever reach them.
      Cleaning this up makes your robot's logic easier to follow and your binary smaller.""",
      zonny="""
      [ ~_~] <("Wait, why is this code still here? Once I see a {keyword}, I'm gone! I'll never even look at these lines.
               Either move the {keyword} to the end or delete the ghost code.")"""
    ),
    
    ErrorCode.E3020 : ErrorDefinition(
      error_code=ErrorCode.E3020,
      severity=Severity.ERROR,
      message="Undefined function call.",
      note="""
      In Zonetic, every function call must have a clear anchor in 
      the global or local scope. I cannot guess what a name refers 
      to if it wasn't previously declared.""",
      zonny="""
      [ o_0] <("Whoops! You're calling for a function that doesn't exist. 
               I've searched every corner of your code and `{name}` is 
               nowhere to be found. Did you forget to define it or 
               maybe a typo snuck in?")"""
    ),
    
    ErrorCode.E3021 : ErrorDefinition(
      error_code=ErrorCode.E3021,
      severity=Severity.ERROR,
      message="Unexpected parameters in function call.",
      note="""
      In Zonetic, function signatures are strict. If a function is 
      declared without parameters, passing values to it creates 
      a mismatch in the program logic.""",
      zonny="""
      [ ~_~] <("You're trying to give me stuff I didn't ask for! This function 
               is a lone wolf, it doesn't need any parameters to do its job. 
               Just clear those parameters and we're good to go.")"""
    ),
    
    ErrorCode.E3022 : ErrorDefinition(
      error_code=ErrorCode.E3022,
      severity=Severity.ERROR,
      message="Mismatched parameter type.",
      note="""
      In Zonetic, types are strict anchors for safety. A function's 
      behavior is built around its parameter types.""",
      zonny="""
      [ o_0] <("Hey! You're trying to fit a square peg in a round hole. This 
                parameter is looking for a `{expect}`, but you gave me a `{found}`. 
                Check your logic (or the docs) and give me the right type!")"""
    ), 

    ErrorCode.E3023 : ErrorDefinition(
      error_code=ErrorCode.E3023,
      severity=Severity.ERROR,
      message="Attempted to use a non-existent keyparam in `{name}`.",
      note="""
      In Zonetic, every keyparam used in a call must map to an 
      existing parameter in the function signature. This strictness 
      prevents typos and ensures data integrity""",
      zonny="""
      [ o_0] <("Who are you talking to? I don't know any parameter named 
               `{name_param}` in this function. It's like calling for a Ronin 
               who never joined the clan! Check your spelling and try again.")"""
    ),
    
    ErrorCode.E3024 : ErrorDefinition(
      error_code=ErrorCode.E3024,
      severity=Severity.ERROR,
      message="Parameter value collision in `{name_func}`.",
      note="""
      In Zonetic, each parameter can only be assigned once. 
      The parameter `{name_param}` was already filled by a value at 
      position {param_pos}""",
      zonny="""
      [ o_0] <("Whoa! You're trying to give two different values to the same 
               parameter `{name_param}`. It already took a value from its position 
               in the line, so this keyparam is just causing a traffic jam. 
               One parameter, one value—that's the rule!")"""
    ),
    
    ErrorCode.E3025 : ErrorDefinition(
      error_code=ErrorCode.E3025,
      severity=Severity.ERROR,
      message="Missing required parameters in call to `{name_func}`.",
      note="""
      In Zonetic, all parameters without a default value must be 
      provided. This ensures the function never encounters an 
      uninitialized state during execution.""",
      zonny="""
      [ -_-] <("Wait! You're trying to build a bridge but you're missing {num} 
               essential piece(s). This function can't start until every 
               required parameter has a value. Check the definition 
               and fill the gaps!")"""
    ),
    
    ErrorCode.E3026 : ErrorDefinition(
      error_code=ErrorCode.E3026,
      severity=Severity.ERROR,
      message="Void function used as expression.",
      note="""
      In Zonetic, functions marked as `void` do not guarantee 
      a value. You cannot assign "nothing" to a variable.""",
      zonny="""
      [ o_0] <("What are you trying to catch? `{name}` doesn't return 
               anything, it's like trying to store an echo in a box!
               Replace this with a valid expression or use 
               a function that doesn't return void as an expr.")"""
    ),
    
    ErrorCode.E3027 : ErrorDefinition(
      error_code=ErrorCode.E3027,
      severity=Severity.ERROR,
      message="Parameter `{name}` is declared more than once in this function.",
      note="""In Zonetic, each parameter must have a unique name within a function signature.""",
      zonny="""[ ~_~] <("`{name}` showed up twice in the parameters. Pick one and remove the other.)"""
    ),
    
    ErrorCode.E3028 : ErrorDefinition(
      error_code=ErrorCode.E3028,
      severity=Severity.ERROR,
      message="This expression cannot be used as a field default value.",
      note="""
      In Zonetic, field default values only accept literals, basic operations, and construct expressions.
      Block expressions, if forms, function calls, etc. Are not allowed.""",
      zonny="""
      [ ~_~] <("Field defaults need to be simple and predictable. Use a literal or a construct instead.")"""
    ),
    
    ErrorCode.E3029 : ErrorDefinition(
      error_code=ErrorCode.E3029,
      severity=Severity.ERROR,
      message="Cannot assign `{found}` to field `{field}`, which expects `{expected}`.",
      note="""
      In Zonetic, the value passed for a field in a construct expression must match the field's declared type.""",
      zonny="""
      [ 0_0] <("`{field}` expects `{expected}` but you gave it `{found}`. Make the types match.")"""
    ),
    
    ErrorCode.E3030 : ErrorDefinition(
      error_code=ErrorCode.E3030,
      severity=Severity.ERROR,
      message="The object `{name}` was not found in the current scope.",
      note="In Zonetic, you must declare an object before accessing its fields.",
      zonny="""
        [ o_0] <("I looked everywhere but I can't find `{name}`. 
                 Did you forget to declare it or is it hiding 
                 in another scope? Check your spelling!")"""
    ),
    
    ErrorCode.E3031 : ErrorDefinition(
      error_code=ErrorCode.E3031,
      severity=Severity.ERROR,
      message="`{name}` is not an object and has no accessible fields.",
      note="The dot `.` operator can only be used on structs or types with an object scope.",
      zonny="""
        [ ~_~] <("You're treating `{name}` like a struct, but it's just 
                 a primitive value. I can't look for fields inside 
                 something that has no internal scope.")"""
    ),
    
    ErrorCode.E3032 : ErrorDefinition(
      error_code=ErrorCode.E3032,
      severity=Severity.ERROR,
      message="The field `{field}` does not exist in the struct `{struct_name}`.",
      note="Check the definition of `{struct_name}` to see its available members.",
      zonny="""
        [ o_0] <("I successfully entered `{struct_name}`, but `{field}` 
                 is nowhere to be found. Did you check the blueprint 
                 of the struct lately?")"""
    ),
    
    ErrorCode.E3033 : ErrorDefinition(
        error_code=ErrorCode.E3033,
        severity=Severity.ERROR,
        message="Cannot assign to `{field}`: this member is not defined in the target object.",
        note="Assignments require the target field to be explicitly defined in its struct.",
        zonny="""
        [ 0_0] <("Destination not found! You're trying to assign a value 
                 to `{field}`, but that field doesn't exist in the 
                 final object. Check your struct definition.")"""
    ),
    
    ErrorCode.E3034 : ErrorDefinition(
        error_code=ErrorCode.E3034,
        severity=Severity.ERROR,
        message="Field `{field}` is inmutable and already has a value.",
        note="""
        In Zonetic, an `inmut` field with a default value in the struct
        declaration cannot be overridden in a construct expression.""",
        zonny="""
        [ ~_~] <("`{field}` is inmut and already has its value set in the struct.
                 You can't override it here.")"""
    ),
    
    ErrorCode.E3036 : ErrorDefinition(
        error_code=ErrorCode.E3036,
        severity=Severity.ERROR,
        message="`{field}` is not a field of `{struct_name}`.",
        note="""
        In Zonetic, keyparam-style field assignment in a construct requires
        the field name to exist in the struct declaration.""",
        zonny="""
        [ o_0] <("I looked inside `{struct_name}` and `{field}` is not there.
                 Check the struct declaration and the field name.")"""
    ),
    
    ErrorCode.E3037 : ErrorDefinition(
        error_code=ErrorCode.E3037,
        severity=Severity.ERROR,
        message="Too many values passed to `{struct_name}` — expected at most {max}, got {found}.",
        note="""
        In Zonetic, a construct expression cannot receive more values than
        the number of fields in the struct.""",
        zonny="""
        [ 0_0] <("`{struct_name}` only has {max} fields but you passed {found}.
                 Remove the extra ones.")"""
    ),
    
    ErrorCode.E3038 : ErrorDefinition(
        error_code=ErrorCode.E3038,
        severity=Severity.ERROR,
        message="Struct `{name}` does not exist.",
        note="""
        In Zonetic, construct expressions require the struct to be declared before use.
        Structs are registered through pre-scan and reachable from anywhere in the program.""",
        zonny="""
        [ o_0] <("`{name}` is not a struct I know about. Check the name or declare the struct first.")"""
    ),
    
    ErrorCode.E3040 : ErrorDefinition(
        error_code=ErrorCode.E3040,
        severity=Severity.ERROR,
        message="`{field}` is not a field of this struct.",
        note="""
        In Zonetic, the final field in a chain access must exist inside the struct of the preceding object.""",
        zonny="""
        [ o_0] <("I followed the chain all the way down and `{field}` isn't there at the end. Check the struct.")"""
    ),
    
    ErrorCode.E3041 : ErrorDefinition(
        error_code=ErrorCode.E3041,
        severity=Severity.ERROR,
        message="`{name}` is already declared as a struct and cannot be used as a function name.",
        note="""
        In Zonetic, struct names and function names share the same namespace.
        A function cannot have the same name as an existing struct.""",
        zonny="""
        [ ~_~] <("'{name}' is already a struct. Pick a different name for this function — they can't share the same one.")"""
    ),
    
    ErrorCode.E3042 : ErrorDefinition(
        error_code=ErrorCode.E3042,
        severity=Severity.ERROR,
        message="`{name}` is already declared as a function and cannot be used as a struct name.",
        note="""
        In Zonetic, struct names and function names share the same namespace.
        A struct cannot have the same name as an existing function.""",
        zonny="""
        [ ~_~] <("`{name}` is already a function. Pick a different name for this struct — they can't share the same one.")"""
    ),
        
    ErrorCode.E3043 : ErrorDefinition(
        error_code=ErrorCode.E3043,
        severity=Severity.ERROR,
        message="This block has no statements.",
        note="""
        In Zonetic, a block expression must contain at least one statement to be meaningful.""",
        zonny="""
        [ ~_~] <("An empty block does absolutely nothing. Add at least one statement or remove it.")"""
    ),
    
    ErrorCode.E3044 : ErrorDefinition(
        error_code=ErrorCode.E3044,
        severity=Severity.ERROR,
        message="Field `{name}` is already declared in this struct.",
        note="""
        In Zonetic, field names inside a struct must be unique. Shadowing between fields is not allowed —
        it would make the struct impossible to reason about.""",
        zonny="""
        [ ~_~] <("`{name}` appears twice in the struct. Every field needs a unique name.")"""
    ),
    
    ErrorCode.E3045 : ErrorDefinition(
        error_code=ErrorCode.E3045,
        severity=Severity.ERROR,
        message="`{name}` is not a declared field of this struct.",
        note="""
        In Zonetic, assignment statements inside a struct block can only target fields declared in the same struct.""",
        zonny="""
        [ o_0] <("`{name}` doesn't exist as a field here. Declare it first before assigning it a value.")"""
    ),
    
    ErrorCode.E3046 : ErrorDefinition(
        error_code=ErrorCode.E3046,
        severity=Severity.ERROR,
        message="This statement is not allowed inside a struct block.",
        note="""
        In Zonetic, a struct block only accepts field declarations and their assignments.
        Control flow, expressions, and other statements are not permitted.""",
        zonny="""
        [ ~_~] <("Structs are for declaring fields, not for running code.
                 Remove this and keep only field declarations.")"""
    ),
    
    ErrorCode.E4001 : ErrorDefinition(
      error_code=ErrorCode.E4001,
      severity=Severity.ERROR,
      message="Division by zero is not allowed — `{operator}` received zero as the right operand.",
      note="""
      In Zonetic, dividing by zero or using zero as the modulo divisor is undefined. 
      This should have been caught earlier — but the value of the divisor 
      was only known at runtime.""",
      zonny="""
      [ x_x] <("DIVISION BY ZERO. I'm not okay. 
               How did this get past me? The right side of '{operator}' 
               is zero and I absolutely cannot work with that. 
               Make sure your divisor is never zero before operating.")"""
    ),
    
    ErrorCode.E4002 : ErrorDefinition(
      error_code=ErrorCode.E4002,
      severity=Severity.ERROR,
      message="Stack overflow — maximum recursion depth of {limit} exceeded.",
      note="""
      In Zonetic, the call stack has a default limit of {limit} to prevent infinite recursion. 
      If this limit was reached, a base case is likely missing or unreachable.
      The limit can be increased with --max-depth if deeper recursion is needed.""",
      zonny="""
      [ x_x] <("I just kept going and going and I ran out of stack. 
               Add a base case so it knows when to stop — 
               or raise --max-depth if you're sure 200 isn't enough.")"""
    ),
    
    ErrorCode.E5001 : ErrorDefinition(
      error_code=ErrorCode.E5001,
      severity=Severity.ERROR,
      message="Division by zero detected during compilation.",
      note="""
      In Zonetic, division by zero is undefined for integer types. 
      Since both operands are constants, I can calculate this now 
      and prevent your program from crashing later.""",
      zonny="""
      [ 0_0] <("Nice try! I saw that zero from a mile away. 
               Constant folding doesn't just make things faster, 
               it also catches your math crimes. Don't make me 
               divide by zero, I'm a compiler, not a philosopher.")"""
    ),
    
    ErrorCode.E5002 : ErrorDefinition(
      error_code=ErrorCode.E5002,
      severity=Severity.ERROR,
      message="Constant operation results in Infinity.",
      note="""
      In Zonetic, dividing a `double` by zero is allowed by the IEEE 754 standard,
      resulting in `{inf}`. However, I'm letting you know because this usually 
      leads to unpredictable behavior in robotic sensors.""",
      zonny="""
      [ o_0] <("Infinity? That's a lot of distance for a robot to cover. 
               I'll let it pass because it's a `double`, but are you 
               sure you want your variables touching the stars?")"""
    ),
    
    ErrorCode.E5003 : ErrorDefinition(
      error_code=ErrorCode.E5003,
      severity=Severity.ERROR,
      message="Constant operation results in NaN (Not a Number)",
      note="""
      In Zonetic, this operation results in `NaN`. While floating-point 
      math allows it, `NaN` values are contagious and will ruin any 
      calculation or sensor reading they touch.""",
      zonny="""
      [ x_o] <("Zero divided by zero? You just broke math. 
               I'm giving you a `NaN`, but don't expect me to 
               know what to do with it later. It's not a number, 
               it's a headache for your robot.")"""
    ),
    
    ErrorCode.E5004 : ErrorDefinition(
      error_code=ErrorCode.E5004,
      severity=Severity.ERROR,
      message="Integer overflow detected during constant folding.",
      note="""
      In Zonetic, `{type_int}` has a fixed capacity. The result of this 
      operation exceeds the maximum value of approximately {magnitud}.""",
      zonny="""
      [ >_<] <("Whoa! That's a massive number. My `{type_int}` storage 
               is sweating just looking at it. I can't fit 
               more than {magnitud} in there!")"""
    ),
    
    ErrorCode.E5005 : ErrorDefinition(
      error_code=ErrorCode.E5005,
      severity=Severity.ERROR,
      message="Floating-point overflow detected during constant folding.",
      note="""
      In Zonetic, `{target_type}` follows the IEEE 754 standard. 
      The maximum representable value is approximately {max_val}.
      Anything beyond this limit results in `{inf}`.""",
      zonny="""
      [ >_<] <("Whoa! That's too much for a `{target_type}`. 
               I can't track a number that big without 
               losing my mind and just calling it `{inf}`. 
               Check your exponents!")"""
    ),
    
    ErrorCode.W5001 : ErrorDefinition(
      error_code=ErrorCode.W5001,
      severity=Severity.WARNING,
      message="Floating-point underflow detected during constant folding.",
      note="""
      In Zonetic, `{target_type}` cannot accurately represent values smaller 
      than approximately {min_val}. To prevent unstable calculations, 
      I will treat this result as `0.0`.""",
      zonny="""
      [ ._.] <("That number is microscopic! It's too small for a 
               `{target_type}` to track, so I'm rounding it to `0.0`. 
               Be careful, vanishing decimals can make robot 
               sensors do very strange things!")"""
    ),
}


