grammar ListLang;

// --- LEXER RULES ---
// Keywords
FUNC      : 'func' ;
IF        : 'if' ;
THEN      : 'then' ;
END       : 'end' ;
ELSE      : 'else' ;
WHILE     : 'while' ;
DO        : 'do' ;
UNTIL     : 'until' ;
FOR       : 'for' ;
FROM      : 'from' ;
TO        : 'to' ;
SWITCH    : 'switch' ;
CASE      : 'case' ;
DEFAULT   : 'default' ;
RETURN    : 'return' ;
WRITE     : 'write' ;
READ      : 'read' ;
LEN       : 'len' ;
DEQUEUE   : 'dequeue' ;
LAMBDA    : 'lambda' ;
OUT       : 'out' ;
BREAK     : 'break' ;
CONTINUE  : 'continue' ;

// Logical operators
AND       : 'and' ;
OR        : 'or' ;
NOT       : 'not' ;

// Identifiers and Literals
IDENTIFIER: [a-zA-Z_][a-zA-Z_0-9]* ;
NUMBER    : [0-9]+ ('.' [0-9]+)? ; // Supports integers and floats
// FIX: Using the most liberal STRING definition. It matches anything
// starting with '"' and ending with '"', allowing all characters inside,
// including unescaped newlines. This might be too permissive for a real language,
// but necessary if input files contain them literally.
STRING    : '"' ( ~( '"' | '\\' ) | '\\' . )* '"' ;


// Operators and Punctuation
ARROW_RIGHT : '->' ;
ARROW_LEFT  : '<-' ;
ASSIGN      : '=' ; // Added ASSIGN token for '='
APPEND      : '<<' ; // List append

// Comparison operators
LE        : '<=' ; // Less than or equal
GE        : '>=' ; // Greater than or equal
EQ        : '==' ; // Equal
NE        : '!=' ; // Not equal
LT        : '<' ;  // Less than
GT        : '>' ;  // Greater than

// Arithmetic operators
PLUS      : '+' ;
MINUS     : '-' ;
MULT      : '*' ;
DIV       : '/' ;

// Delimiters
LPAREN    : '(' ;
RPAREN    : ')' ;
LBRACK    : '[' ;
RBRACK    : ']' ;
LBRACE    : '{' ;
RBRACE    : '}' ;
COLON     : ':' ;
COMMA     : ',' ;
DOT       : '.' ;
SEMI      : ';' ;

// --- WHITESPACE AND COMMENTS ---
// FIX: Ensure these are explicitly skipped by the lexer, not just hidden.
// -> skip is the correct way for ANTLR to discard these tokens.
COMMENT       : '/*' .*? '*/' -> skip ;
LINE_COMMENT  : '//' ~[\r\n]* -> skip ;
WS            : [ \t\r\n]+ -> skip ;


// --- PARSER RULES ---

program
    : (functionDecl | statement)* EOF
    ;

functionDecl
    : FUNC IDENTIFIER LPAREN parameterList? RPAREN (ARROW_RIGHT)? statementBlock END // ARROW_RIGHT is optional
    ;

parameterList
    : parameter (COMMA parameter)*
    ;

parameter
    : IDENTIFIER OUT?
    ;

identifierList
    : IDENTIFIER (COMMA IDENTIFIER)*
    ;

singleAssignment
    : expression ARROW_RIGHT IDENTIFIER                                 #ExpressionRightAssignment
    | IDENTIFIER ARROW_LEFT expression                                  #IdentifierLeftAssignment
    | IDENTIFIER ASSIGN expression                                      #IdentifierAssignExpression // New assignment type for '='
    | expression LBRACK expression RBRACK ARROW_LEFT expression         #ListElementAssignment
    | expression LBRACK expression RBRACK ASSIGN expression             #ListElementAssignExpression // New assignment type for '='
    | IDENTIFIER DOT IDENTIFIER ARROW_LEFT expression                   #StructFieldAssignment
    | IDENTIFIER DOT IDENTIFIER ASSIGN expression                       #StructFieldAssignExpression // New assignment type for '='
    ;

multiAssignment
    : identifierList (ARROW_LEFT | ASSIGN) expressionList // Allow '=' for multi-assignment
    ;

assignmentStatement
    : singleAssignment (COMMA singleAssignment)*
    | multiAssignment
    ;

statement
    : assignmentStatement SEMI?
    | expression SEMI?
    | lambdaExpr SEMI? // Lambda expression as a statement (e.g., to assign to a variable)
    | functionDecl
    | ifStatement
    | whileStatement
    | doUntilStatement
    | forStatement
    | switchStatement
    | returnStatement SEMI?
    | writeStatement SEMI?
    | breakStatement SEMI?
    | continueStatement SEMI?
    | statementBlock
    ;

breakStatement
    : BREAK
    ;

continueStatement
    : CONTINUE
    ;

statementBlock
    : LBRACE (statement | functionDecl)* RBRACE // Allow functionDecl inside statementBlock
    ;

ifStatement
    : IF expression THEN (statement | statementBlock) (ELSE (statement | statementBlock))? END
    ;

whileStatement
    : WHILE expression DO (statement | statementBlock) END
    ;

doUntilStatement
    : DO (statement | statementBlock) UNTIL expression END
    ;

forStatement
    : FOR IDENTIFIER FROM expression TO expression DO (statement | statementBlock) END
    ;

switchStatement
    : SWITCH expression (COLON)? caseClause+ (DEFAULT (COLON)? (statement | statementBlock))? END // COLON is optional for SWITCH and DEFAULT
    ;

caseClause
    : CASE expression COLON (statement | statementBlock)
    ;

returnStatement
    : RETURN (expression | lambdaExpr)?
    ;

writeStatement
    : WRITE LPAREN argumentList? RPAREN
    ;

argument
    : expression OUT?
    ;

argumentList
    : argument (COMMA argument)*
    ;

functionCall
    : IDENTIFIER LPAREN argumentList? RPAREN
    ;

expressionList
    : expression (COMMA expression)*
    ;

// IMPORTANT: All alternatives must have labels when one does.
// Labels must be unique and not conflict with existing rule names.
expression
    : lambdaExpr                                                #LambdaExpressionActual
    | READ LPAREN RPAREN                                        #ReadCall
    | LEN LPAREN expression RPAREN                              #LenCall
    | DEQUEUE FROM expression                                   #DequeueCall
    | MINUS expression                                          #UnaryMinus
    | NOT expression                                            #UnaryNot
    | primaryExpr                                               #PrimaryExpressionActual
    | expression MULT expression                                #MultiplyExpr
    | expression DIV expression                                 #DivideExpr
    | expression PLUS expression                                #PlusExpr
    | expression MINUS expression                               #MinusExpr
    | expression APPEND expression                              #AppendExpr
    | expression (LT|LE|GT|GE|EQ|NE) expression                 #ComparisonExpr
    | expression (AND|OR) expression                            #LogicalExpr
    | expression LBRACK expression RBRACK                       #ListAccessExpr
    | IDENTIFIER DOT IDENTIFIER                                 #StructFieldAccessExpr
    ;

// IMPORTANT: All alternatives must have labels when one does.
primaryExpr
    : LPAREN expression RPAREN                                  #ParenExpression
    | functionCall                                              #FunctionCallExpression
    | literal                                                   #LiteralExpression
    | IDENTIFIER                                                #IdentifierExpression
    ;

// Removed SEMI? from lambdaExpr rules, as it's part of statement context
lambdaExpr
    : LAMBDA LPAREN parameterList? RPAREN ARROW_RIGHT expression        #LambdaReturn
    | LAMBDA LPAREN parameterList? RPAREN ARROW_RIGHT statementBlock    #LambdaBlock
    ;

literal
    : NUMBER
    | STRING
    | listLiteral
    | structLiteral
    ;

listLiteral
    : LBRACK expressionList? RBRACK
    ;

structLiteral
    : LBRACE (fieldAssignment (COMMA fieldAssignment)*)? RBRACE
    ;

fieldAssignment
    : IDENTIFIER COLON expression
    ;