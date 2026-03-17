from .error_code import ErrorCode
from .error_definition import ErrorDefinition
from .severity import Severity

ERROR_REGISTRY: dict[ErrorCode, ErrorDefinition] = {
    ErrorCode.E0001 : ErrorDefinition(
        error_code=ErrorCode.E0001,
        severity=Severity.ERROR,
        message="I found an unexpected `{char}` character",
        note = "Zonetic does not support or use the `{char}` character for this operation",
        zonny= """[ ~_~] <("I don't recognize `{char}` in this context. Just delete the 
          character so we can both move on with our lives.")"""
    ),
    
    ErrorCode.E0002 : ErrorDefinition(
        error_code=ErrorCode.E0002,
        severity=Severity.ERROR,
        message="I'm still waiting for you to close this comment",
        note="Zonetic multiline comments must be explicitly closed with the `|-` token",
        zonny="""[ ~_~] <("You started a comment but never finished it. I've reached the 
          end of the file and I'm still waiting for that `|-`. 
          Finish your sentence so I can go back to work!")"""
    ),
    
    ErrorCode.E0003 : ErrorDefinition(
        error_code=ErrorCode.E0003,
        severity=Severity.ERROR,
        message="I encountered an escape sequence I don't know: `{escape}`",
        note="Zonetic only supports standard escape sequences like \\n, \\t, \\\, among others",
        zonny="""[ ~_~] <("Is `{escape}` supposed to be some secret robot code? Because 
          it's not in my manual. Just delete it or use a valid 
          escape sequence so I can actually understand your text!")"""
    ),
    
    ErrorCode.W0001 : ErrorDefinition(
        error_code=ErrorCode.W0001,
        severity=Severity.WARNING,
        message="Unnecessary escape character",
        note="Zonetic allows using `{quote_escape}` inside `{quote_used}` strings (and vice-versa) without backslashes",
        zonny="""[ ~_~] <("Why the `\\{quote_escape}`? You're already using {name_quote_used} quotes for the string. 
          It's redundant and looks messy. Just delete the backslash 
          and keep it simple, like I do with my ASCII face!")"""
    ),
    
    ErrorCode.E0004 : ErrorDefinition(
        error_code=ErrorCode.E0004,
        severity=Severity.ERROR,
        message="I reached the end of the file looking for the closing {quote}, but never found it.",
        note="""In Zonetic, a string must be closed with the same quote it was opened with. 
          Without a closing {quote}, everything after the opening is consumed as part of the string.""",
        zonny="""[ ~_~] <("I read your entire file waiting for a {quote} that never came. 
          Close your string before the end of the file.")"""
    ),
    
    ErrorCode.E0005 : ErrorDefinition(
        error_code=ErrorCode.E0005,
        severity=Severity.ERROR,
        message="A floating point number can only have one decimal point, but I found more than one.",
        note="""In Zonetic, a float is written as digits, one `.`, and more digits. 
          Extra decimal points make the number invalid.""",
        zonny="""[ o_0] <("More than one dot in a number? Pick one decimal point 
          and stick with it — remove the extra ones.")"""
    ),
    
    ErrorCode.E1001 : ErrorDefinition(
        error_code=ErrorCode.E1001,
        severity=Severity.ERROR,
        message="I detected mixed statement terminator styles in this script",
        note="""Zonetic supports hybrid statement terminators (newline or semicolon),
          but only one style may be used per script to preserve syntactic consistency and avoid ambiguity in normalization""",
        zonny="""[ o_0] <("You used {mode_tr}… and then trusted a {used_tr}? Were you testing me?
          Choose one terminator style per script: either explicit `;` or newline-based termination, but not both.")"""
    ),
    
    ErrorCode.E1002 : ErrorDefinition(
        error_code=ErrorCode.E1002,
        severity=Severity.ERROR,
        message="I found a semicolon where a statement cannot end",
        note="""In Zonetic, the semicolon is a statement terminator. It is only valid at the end of a complete statement.
          Using it inside expressions or in isolation violates the syntactic structure expected by the normalizer""",
        zonny="""[ ~_~] <("That semicolon looks confident… but it ends absolutely nothing.
          A statement must exist before it. Remove the stray `;` or place it after a complete statement.")"""
    ),
    
    ErrorCode.E2001 : ErrorDefinition(
        error_code=ErrorCode.E2001,
        severity=Severity.ERROR,
        message="I was ready to create something, but you gave me no name.",
        note="""In Zonetic, every variable needs a label. I can't store data in a 'nothingness'.
          The syntax requires an identifier after `mut` or `inmut`.""",
        zonny="""[ o_0] <("Oh, great. You want a {name_mut}.. 'ghost'? 
          I'm not a mind reader! I need a name to label 
          this in my memory banks. Just add a name after 
          `mut` or `inmut` so I know what to call it.")"""
    ),
    
    ErrorCode.E2002 : ErrorDefinition(
        error_code=ErrorCode.E2002,
        severity=Severity.ERROR,
        message="I found something that isn't a valid type right after your colon",
        note="""In Zonetic, the `:` creates a contract. You promised me a data type here so I can allocate the right space in memory,
          but '{type}' doesn't match any type I know.""",
        zonny = """[ ~_0] <("You put `:` and then left me hanging with a mystery word!
          If you're going to be explicit, actually be explicit! To fix this, either give me a valid type after 
          the `:` or just delete the `:` entirely and let me use my super-brain to infer the type for you.")"""
    ), 

    ErrorCode.E2003 : ErrorDefinition(
        error_code=ErrorCode.E2003,
        severity=Severity.ERROR,
        message="I found an opening `(`, but you never closed the deal.",
        note="In Zonetic, every `(` needs a matching `)` to complete the expression.",
        zonny="""[ o_0] <("You left me hanging! A `(` without a `)` is like a robot with only one arm—it just doesn't work. 
          Go back and close that parenthesis before I 
          get an existential crisis.")"""
    ),
    
    ErrorCode.E2004 : ErrorDefinition(
        error_code=ErrorCode.E2004,
        severity=Severity.ERROR,
        message="I found `{token}` after a declaration, but I don't know what to do with it.",
        note="""In Zonetic, a declaration must end with `;` or newline to close the statement, 
          or `,` to continue with another declaration in the same line.""",
        zonny="""[ ~_~] <("I parsed your whole declaration and then you threw 
          `{token}` at me. What am I supposed to do with that? 
          End with `;`, a newline, or keep going with `,`.")"""
    ),
    
    ErrorCode.E2005 : ErrorDefinition(
        error_code=ErrorCode.E2005,
        severity=Severity.ERROR,
        message="Expected an expression, but found `{token}` instead.",
        note="In Zonetic, `{token}` cannot start an expression.",
        zonny="""[ o_0] <("`{token}`? That's not an expression, that's just 
          chaos. Use a valid expression or check the N.E.R.T 
          to see what I actually understand.")"""
    ),
    
    ErrorCode.E2006 : ErrorDefinition(
      error_code=ErrorCode.E2006,
      severity=Severity.ERROR,
      message="Expected an assignment operator after `{name}`, but found `{token}` instead.",
      note="""In Zonetic, after a variable name in an assignment, you must use a valid assignment operator.
          Currently supported: `=`, `+=`, `-=`, `*=`, `/=`, `//=`, `**=`, `%=`""",
      zonny="""[ ~_~] <("`{token}` is a perfectly fine token... just not here. 
          After `{name}` I need an assignment operator, 
          not whatever that was supposed to be.")"""
    ),
    
    ErrorCode.E2007 : ErrorDefinition(
      error_code=ErrorCode.E2007,
      severity=Severity.ERROR,
      message="This block expression was expected to produce a value, but no `give` was found.",
      note="""In Zonetic, when a block expression is used in a value context — such as 
          an assignment or inside another expression — it must produce a value 
          using `give` as its last meaningful statement.""",
      zonny="""[ 0_0] <("You put a block here like it was going to give me something 
          and then just... nothing? Add a 'give' with the value 
          you want this block to produce.")"""
    ),
    
    ErrorCode.W2001 : ErrorDefinition(
      error_code=ErrorCode.W2001,
      severity=Severity.WARNING,
      message="`give` returned a value, but nothing is waiting for it.",
      note="""In Zonetic, `give` produces a value from a block expression. 
           When a block is used as a statement and not as a value, 
           any value produced by 'give' is simply lost.""",
      zonny="""[ o_0] <("You went through all the trouble of computing a value 
          just to throw it away? Remove the `give` — 
          the block will still run, the value just won't go anywhere.")""",
    ),
    
    ErrorCode.E2008 : ErrorDefinition(
      error_code=ErrorCode.E2008,
      severity=Severity.ERROR,
      message="I found an opening `{aux_r}`, but the block was never closed.",
      note="""In Zonetic, every block expression opened with `{aux_r}` must be closed with `{aux_l}`.""",
      zonny="""[ ~_~] <("You opened a block and just left it hanging. 
          I reached the end of the file still waiting for that `{aux_l}`. 
          Close your block before I lose my mind.")"""
    ),
    
    ErrorCode.E2009 : ErrorDefinition(
      error_code=ErrorCode.E2009,
      severity=Severity.ERROR,
      message="Expected `{aux_r}` to open a block expression, but found `{token}` instead.",
      note="""In Zonetic, every form or structure that requires a block must open it with '{aux_r}'. 
        After the form's signature — whether it includes a condition, parameters, or nothing at all — 
        a block expression must follow immediately.""",
      zonny="""[ o_0] <("I just finished reading the form signature and was ready for a `{aux_r}`, 
        but `{token}` showed up instead. 
        Open a block with `{aux_r}` right after the signature.")"""
    ),
    
    ErrorCode.E2010 : ErrorDefinition(
      error_code=ErrorCode.E2010,
      severity=Severity.ERROR,
      message="Unexpected `{token}` found where a statement was expected.",
      note="""In Zonetic, a statement must start with a recognized keyword or construct — 
          such as `mut`, `inmut`, `if`, a block expression, or a variable name for assignment.""",
      zonny="""[ 0_0] <("`{token}`? I was ready for a statement and you gave me that. 
          Check what you wrote — something here doesn't belong.")"""
    ),
    
    ErrorCode.E2011 : ErrorDefinition(
      error_code=ErrorCode.E2011,
      severity=Severity.ERROR,
      message="`{keyword}` found without an opening `if`.",
      note="""In Zonetic, `elif` and `else` can only appear as continuation 
          branches of an existing if form opened with `if`.""",
      zonny="""[ 0_0] <("`{keyword}` just showed up out of nowhere. 
          I need an `if` to open the form first — 
          `{keyword}` can't exist without one.")"""
    ),
    
    ErrorCode.E3001 : ErrorDefinition(
      error_code=ErrorCode.E3001,
      severity=Severity.ERROR,
      message="`{name}` was used but has never been declared.",
      note="""In Zonetic, a variable must be declared with 'mut' or 'inmut' before it can be used.
          Any attempt to read or write a name that does not exist in the current scope is an error.""",
      zonny="""[ o_0] <("`{name}`? I looked everywhere in this scope and I have 
          no idea who that is. Either declare it first with 
          'mut' or 'inmut', or check if you spelled it right.")"""
    ),
    
    ErrorCode.E3002 : ErrorDefinition(
      error_code=ErrorCode.E3002,
      severity=Severity.ERROR,
      message="`{name}` exists but has no value yet.",
      note="""In Zonetic, a variable must have a value before it can be used. 
          `{name}` was declared but never assigned a value at this point in the program.""",
      zonny="""[ o_0] <("`{name}` is right there in the scope, I can see it, 
          but it's completely empty. Give it a value before 
          trying to use it.")"""
    ),
    
    ErrorCode.E3003: ErrorDefinition(
      error_code=ErrorCode.E3003,
      severity=Severity.ERROR,
      message="Operand type mismatch in `{operator}`: expected {valid_types}, but found `{found_type}`.",
      note="""In Zonetic, the `{operator}` operator only accepts operands of type {valid_types}. 
           See the NERT for the full list of type rules for native expressions.""",
      zonny="""[ ~_~] <("`{found_type}` doesn't work with `{operator}`. 
          {valid_types} is what I need here — 
          make sure your expression returns the right type.")"""
    ),
    
    ErrorCode.E3004 : ErrorDefinition(
      error_code=ErrorCode.E3004,
      severity=Severity.ERROR,
      message="Operand type mismatch in `{operator}`: left is `{left_type}` but right is `{right_type}`.",
      note="""In Zonetic, both operands of `{operator}` must be of the same type. 
          Mixed-type operations are not allowed — use an explicit cast to convert 
          one operand before operating.""",
      zonny="""[ ~_~] <("`{left_type}` and `{right_type}` don't mix in `{operator}`. 
          Pick one type and cast the other — 
          I don't do implicit conversions.")"""
    ),
    
    ErrorCode.E3005 : ErrorDefinition(
      error_code=ErrorCode.E3005,
      severity=Severity.ERROR,
      message="`{name}` is a value and cannot be reassigned.",
      note="""In Zonetic, names declared with `inmut` are values — they can only be assigned once. 
          If you need a name that can change, declare it with `mut` instead.""",
      zonny="""[ ~_~] <("`{name}` was declared with `inmut` — that means no touching it again. 
          If you need it to change, go back and use `mut` when you declare it.")"""
    ),
    
    ErrorCode.E3006 : ErrorDefinition(
      error_code=ErrorCode.E3006,
      severity=Severity.ERROR,
      message="Cannot assign `{found_type}` to `{name}`, which expects `{expected_type}`.",
      note="""In Zonetic, a variable always keeps the same type it was declared or inferred with. 
           The value you are trying to assign does not match the type of `{name}`.""",
      zonny="""[ 0_0] <("`{name}` is a `{expected_type}` — you can't just hand it a `{found_type}`. 
          Either fix the expression or use a cast 
          to convert it to `{expected_type}` first.")"""
    ),
    
    ErrorCode.W3001 : ErrorDefinition(
      error_code=ErrorCode.W3001,
      severity=Severity.WARNING,
      message="Code after `give` will never execute.",
      note="""In Zonetic, 'give' exits the block immediately after producing its value. 
           Any statements below it inside the same block are unreachable.""",
      zonny="""[ ~_~] <("Everything below this 'give' is just sitting there doing nothing. 
          I'll never reach it — move it before the 'give' 
          or remove it entirely.")"""
    ),
}