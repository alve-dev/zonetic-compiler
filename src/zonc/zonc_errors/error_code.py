from enum import Enum, auto

class ErrorCode(Enum):
    # Lexer Errors
    E0001 = auto()
    E0002 = auto()
    E0003 = auto()
    E0004 = auto()
    E0005 = auto()
    E0006 = auto()
    E0007 = auto()
    E0008 = auto()
    E0009 = auto()
    E0010 = auto()
    E0011 = auto()
    E0012 = auto()
    
    # Lexer Warnings
    W0001 = auto()
    
    # Normalizer Errors
    E1001 = auto()
    E1002 = auto()
    
    # Parser Errors
    E2001 = auto()
    E2002 = auto()
    E2003 = auto()
    E2004 = auto()
    E2005 = auto()
    E2006 = auto()
    E2007 = auto()
    E2008 = auto()
    E2009 = auto()
    E2010 = auto()
    E2011 = auto()
    E2012 = auto()
    E2013 = auto()
    E2014 = auto()
    E2015 = auto()
    E2016 = auto()
    E2017 = auto()
    E2018 = auto()
    E2019 = auto()
    E2020 = auto()
    E2021 = auto()
    E2022 = auto()
    E2023 = auto()
    E2024 = auto()
    E2025 = auto()
    E2026 = auto()
    E2027 = auto()
    E2028 = auto()
    E2029 = auto()
    E2030 = auto()
    E2031 = auto()
    E2032 = auto()
    E2033 = auto()
    
    # Parser Warnings
    W2001 = auto()
    
    # Semantic Errors
    E3001 = auto() 
    E3002 = auto()
    E3003 = auto()
    E3004 = auto()
    E3005 = auto()
    E3006 = auto()
    E3007 = auto()
    E3008 = auto()
    E3009 = auto()
    E3010 = auto()
    E3011 = auto()
    E3012 = auto()
    E3013 = auto()
    E3014 = auto()
    E3015 = auto()
    E3016 = auto()
    E3017 = auto()
    E3018 = auto()
    E3019 = auto()
    E3020 = auto()
    E3021 = auto()
    E3022 = auto()
    E3023 = auto()
    E3024 = auto()
    E3025 = auto()
    E3026 = auto()
    E3027 = auto()
    E3028 = auto() 
    E3029 = auto()
    E3030 = auto()
    E3031 = auto()
    E3032 = auto()
    E3033 = auto()
    E3034 = auto()
    E3035 = auto() # Libre
    E3036 = auto()
    E3037 = auto()
    E3038 = auto()
    E3039 = auto() # Libre
    E3040 = auto()
    E3041 = auto()
    E3042 = auto()
    E3043 = auto()
    E3044 = auto()
    E3045 = auto()
    E3046 = auto()
    
    
    # Semantics Warnings
    W3001 = auto()
    W3002 = auto()
    W3003 = auto()
    W3004 = auto()
    W3005 = auto()
    W3006 = auto()
    
    # Runtime Tree-Walker Errors
    E4001 = auto()
    E4002 = auto()
    
    # Optimization Errors
    E5001 = auto()
    E5002 = auto()
    E5003 = auto()
    E5004 = auto()
    E5005 = auto()
    E5006 = auto()
    
    W5001 = auto()
    
    
    
    
# actualmente hay 89 Zonetic Errors y 8 Zonetic Warnings
# 6 Errors son de el Lexer y 1 warning son del lexer
# 2 Errors son del Normalizer
# 33 Errors son del Parser y 1 warning son del parser
# 46 Errors son de Semantic y 6 Warnings son del Semantic
# 2 Error de Runtime 