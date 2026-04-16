def print_tokens(tokens):
    if not tokens:
        print("[ ! ] No tokens to display.")
        return

    h_idx, h_type, h_lex, h_line = "INDEX", "TYPE", "LEXEME", "LINE"

    w_idx = len(str(len(tokens)))
    if len(h_idx) > w_idx: w_idx = len(h_idx)
    
    w_type = len(h_type)
    w_lex = len(h_lex)
    w_line = len(h_line)

    for t in tokens:
        t_type = str(t._type)
        t._value = str(t._value).replace('\n', "\\n")
        t_val = t._value
        t_line = str(t._span.line_start)
        

        if len(t_type) > w_type: w_type = len(t_type)
        if len(t_val) > w_lex: w_lex = len(t_val)
        if len(t_line) > w_line: w_line = len(t_line)

    def pad_right(text, width):
        text = str(text)
        while len(text) < width:
            text = text + " "
        return text

    def pad_left_zeros(num, width):
        s = str(num)
        while len(s) < width:
            s = "0" + s
        return s

    total_w = w_idx + w_type + w_lex + w_line + 9
    separator = ""
    while len(separator) < total_w: separator += "-"

    print("\n[ TOKEN STREAM ]")
    print(separator)
    
    header = pad_right(h_idx, w_idx) + " | " + \
             pad_right(h_type, w_type) + " | " + \
             pad_right(h_lex, w_lex) + " | " + \
             pad_right(h_line, w_line)
    print(header)
    print(separator)

    count = 1
    for t in tokens:
        line_num = str(t._span.line_start)

        row = pad_left_zeros(count, w_idx) + " | " + \
              pad_right(t._type, w_type) + " | " + \
              pad_right(t._value, w_lex) + " | " + \
              pad_right(line_num, w_line)
        print(row)
        count += 1
    
    print(separator + "\n")