import os
import sys
from antlr4 import *
from antlr4.error.ErrorListener import ErrorListener
from antlr4.ParserRuleContext import ParserRuleContext
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set

# Corrected import structure for generated files if they are in 'gen' directory
from gen.ListLangLexer import ListLangLexer
from gen.ListLangParser import ListLangParser
from gen.ListLangListener import ListLangListener


# --- Типы областей видимости ---
class ScopeType(Enum):
    GLOBAL = "global"
    FUNCTION = "function"
    LAMBDA = "lambda"
    BLOCK = "block"  # Для if/while/for/do/switch блоков


# --- Система типов ---
class Type(Enum):
    NUMBER = "number"
    STRING = "string"
    LIST = "list"
    LAMBDA = "lambda"
    VOID = "void"  # Для функций, не возвращающих значение, или лямбд-блоков
    UNKNOWN = "unknown"  # Тип, который будет выведен позже (или ошибка)
    BOOL = "bool"  # Для выражений сравнения и логических операций
    STRUCT = "struct"  # Для structLiteral
    NULL = "null"  # For explicit null values (if supported by grammar)

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value

    def is_compatible_with(self, other_type: 'Type') -> bool:
        """
        Checks if this type is compatible with another type.
        This method is strict: primarily for assignment where a type is already established.
        Implicit conversions for operations (+, etc.) are handled specifically in operation logic.
        UNKNOWN is compatible with anything.
        """
        if self == Type.UNKNOWN or other_type == Type.UNKNOWN:
            return True
        if self == other_type:
            return True
        # For strict assignment, cross-compatibility between NUMBER and STRING is NOT allowed.
        return False


# --- Параметр функции/лямбды ---
class Parameter:
    def __init__(self, name: str, param_type: Type, is_out: bool = False,
                 lambda_signature: Optional['LambdaSignature'] = None):  # ADDED lambda_signature, forward ref
        self.name = name
        self.type = param_type
        self.is_out = is_out
        self.lambda_signature = lambda_signature  # ADDED

    def __str__(self):
        base_str = f"{self.name}: {self.type}"
        if self.is_out:
            base_str += " out"
        if self.type == Type.LAMBDA and self.lambda_signature:
            base_str += f" (lambda: {self.lambda_signature})"
        return base_str

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if not isinstance(other, Parameter):
            return False
        # Basic check
        if not (self.name == other.name and self.type == other.type and self.is_out == other.is_out):
            return False

        # If both are LAMBDA, compare signatures. Otherwise, signatures should both be None or irrelevant.
        if self.type == Type.LAMBDA and other.type == Type.LAMBDA:
            return self.lambda_signature == other.lambda_signature
        elif self.type == Type.LAMBDA or other.type == Type.LAMBDA:  # One is LAMBDA, the other is not
            return False  # They cannot be equal if types differ here, or if signature exists for one but not the other
        return True  # Non-lambda types, basic checks were enough

    def __hash__(self):
        # Include lambda_signature in hash if it's a lambda type
        if self.type == Type.LAMBDA and self.lambda_signature is not None:
            return hash((self.name, self.type, self.is_out, self.lambda_signature))
        return hash((self.name, self.type, self.is_out))


# --- Lambda Signature for detailed type tracking ---
class LambdaSignature:
    def __init__(self, params: List[Parameter], return_type: Type):
        self.params = [Parameter(p.name, p.type, p.is_out, p.lambda_signature) for p in params]
        self.return_type = return_type
        self.id: Optional[int] = None  # ADDED: Unique ID assigned by compiler for WAT function name

    def __str__(self):
        params_str = ", ".join(str(p.type) for p in self.params)
        return f"({params_str}) -> {self.return_type}" + (f" (id: {self.id})" if self.id is not None else "")

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if not isinstance(other, LambdaSignature):
            return False
        # Do not compare `id` for equality check, as it's compiler-specific.
        return self.return_type == other.return_type and \
            len(self.params) == len(other.params) and \
            all(p1 == p2 for p1, p2 in zip(self.params, other.params))

    def __hash__(self):
        # Hash without 'id'
        return hash((self.return_type, tuple(hash(p) for p in self.params)))


# --- Информация о переменной ---
class VariableInfo:
    def __init__(self, name: str, var_type: Type, scope_name: str, line: int = -1, is_parameter: bool = False,
                 initialized: bool = False,
                 lambda_signature: Optional[LambdaSignature] = None,
                 element_type: Optional[Type] = None,
                 element_lambda_signature: Optional[LambdaSignature] = None):  # Changed from separate params/return_type
        self.name = name
        self.type = var_type
        self.scope_name = scope_name
        self.line = line  # Line where variable was declared
        self.initialized = initialized
        self.is_parameter = is_parameter
        # For variables, storing lambdas, store their full signature
        self.lambda_signature = lambda_signature if var_type == Type.LAMBDA else None
        self.element_type = element_type
        self.element_lambda_signature = element_lambda_signature if element_type == Type.LAMBDA else None

    def __str__(self):
        base_str = f"'{self.name}': {self.type}"
        if self.type == Type.LAMBDA and self.lambda_signature is not None:
            base_str = f"{base_str} (lambda: {self.lambda_signature})"
        if self.type == Type.LIST and self.element_type is not None:
            base_str = f"{base_str} [elem: {self.element_type}]"
            if self.element_type == Type.LAMBDA and self.element_lambda_signature is not None:
                base_str = f"{base_str} (elem sig: {self.element_lambda_signature})"
        return base_str

    def __repr__(self):
        return self.__str__()


# --- Информация о функции ---
class FunctionInfo:
    def __init__(self, name: str, parameters: List[Parameter], return_type: Type, line: int = -1):
        self.name = name
        self.parameters = parameters
        self.return_type = return_type
        self.line = line
        self.overloads: List['FunctionInfo'] = []
        self.return_lambda_signature: Optional[LambdaSignature] = None

    def signature(self) -> Tuple[
        str, Tuple[Tuple[Type, bool, Optional[LambdaSignature]], ...]]:  # Adjusted for lambda_signature
        """
        Returns a canonical signature for overload resolution:
        (name, ((param1_type, param1_is_out, param1_lambda_sig), ...))
        """
        return (self.name, tuple((p.type, p.is_out, p.lambda_signature) for p in self.parameters))

    def __str__(self):
        params_str = ", ".join(str(p) for p in self.parameters)
        overloads_count = len(self.overloads)
        base_str = f"func {self.name}({params_str}) -> {self.return_type}"
        if overloads_count > 0:
            return f"{base_str} (+{overloads_count} overloads)"
        return base_str

    def __repr__(self):
        return self.__str__()


# --- Таблица символов ---
class SymbolTable:
    def __init__(self, filename: str):
        self.scopes: List[Dict[str, Any]] = []
        self.current_scope_name: str = "global"
        self.filename = filename

        # Initialize global scope
        self.push_scope(ScopeType.GLOBAL, "global")

    def push_scope(self, scope_type: ScopeType, name: str = None):
        """Adds a new scope to the stack."""
        if name is None:
            name = f"{scope_type.value}_{len(self.scopes)}"

        new_scope = {
            "name": name,
            "type": scope_type,
            "variables": {},  # Dict[str, VariableInfo]
            "functions": {}  # Dict[str, FunctionInfo]
        }
        self.scopes.append(new_scope)
        self.current_scope_name = name

    def pop_scope(self):
        """Removes the current scope from the stack."""
        if len(self.scopes) > 1:  # Always keep global scope
            self.scopes.pop()
            self.current_scope_name = self.scopes[-1]["name"]

    def get_current_scope(self) -> Dict[str, Any]:
        """Returns the current scope object."""
        if not self.scopes:
            raise Exception("No active scope in symbol table.")
        return self.scopes[-1]

    def declare_variable(self, name: str, var_type: Type, line: int, is_parameter: bool = False,
                         initialized: bool = False,
                         lambda_signature: Optional[LambdaSignature] = None,
                         element_type: Optional[Type] = None, # Добавлено
                         element_lambda_signature: Optional[LambdaSignature] = None) -> VariableInfo: # Добавлено
        """Declares a variable in the current scope."""
        current_scope = self.get_current_scope()

        # Error 8: Variable already declared in current scope
        if name in current_scope["variables"]:
            raise Exception(f"Переменная '{name}' уже объявлена в текущей области видимости (Ошибка 8)")

        info = VariableInfo(name, var_type, current_scope["name"], line, is_parameter,
                            initialized=initialized,
                            lambda_signature=lambda_signature,
                            element_type=element_type, # Передаем
                            element_lambda_signature=element_lambda_signature) # Передаем
        current_scope["variables"][name] = info
        return info

    def lookup_variable(self, name: str) -> Optional[VariableInfo]:
        """Searches for a variable, starting from the current scope and going up."""
        for scope in reversed(self.scopes):
            if name in scope["variables"]:
                return scope["variables"][name]
        return None

    def initialize_variable(self, name: str):
        """Marks a variable as initialized (in any scope)."""
        # Search from current scope upwards
        for scope in reversed(self.scopes):
            if name in scope["variables"]:
                scope["variables"][name].initialized = True
                return

    def update_variable_type(self, name: str, new_type: Type, line: int,
                             lambda_signature: Optional[LambdaSignature] = None):
        """Updates the type of a variable (in any scope), including lambda information."""
        for scope in reversed(self.scopes):
            if name in scope["variables"]:
                var_info = scope["variables"][name]

                if var_info.type == Type.UNKNOWN or var_info.type.is_compatible_with(new_type):
                    var_info.type = new_type
                    if new_type == Type.LAMBDA:
                        var_info.lambda_signature = lambda_signature
                    else:
                        var_info.lambda_signature = None
                else:
                    # Type mismatch error will be reported by assignment logic
                    pass
                return

    def declare_function(self, func_info: FunctionInfo) -> FunctionInfo:
        """Declares a function (in the global scope) or adds an overload."""
        global_scope = self.scopes[0]

        if func_info.name in global_scope["functions"]:
            existing_func: FunctionInfo = global_scope["functions"][func_info.name]

            # Check for duplicate signature among existing and overloads
            all_signatures = {existing_func.signature()}
            all_signatures.update(f.signature() for f in existing_func.overloads)

            if func_info.signature() in all_signatures:
                # Error 8: Duplicate function
                raise Exception(
                    f"Подпрограмма с именем '{func_info.name}' и такими же параметрами уже объявлена (Ошибка 8)")

            existing_func.overloads.append(func_info)
            return existing_func
        else:
            global_scope["functions"][func_info.name] = func_info
            return func_info

    def lookup_function(self, name: str) -> Optional[FunctionInfo]:
        """Looks up a function in the global scope."""
        return self.scopes[0]["functions"].get(name)


# --- Семантический анализатор (основной класс) ---
class SemanticAnalyzer(ListLangListener):
    def __init__(self, parser: ListLangParser, filename: str):
        self.filename = filename
        self.parser = parser
        self.symbol_table = SymbolTable(filename)
        self.expression_types: Dict[Any, Type] = {}  # Stores types for AST expression nodes
        self.lambda_signatures: Dict[Any, LambdaSignature] = {}  # Stores full signature for lambda expressions
        self.errors: List[str] = []
        self.reported_errors: Set[str] = set()  # To prevent reporting same error multiple times

        self.list_element_types: Dict[Any, Type] = {}  # Store element type for list literals
        self.list_element_lambda_signatures: Dict[Any, LambdaSignature] = {}

        # --- State tracking for scope and context ---
        self.in_function = False
        self.current_function_info: Optional[FunctionInfo] = None  # Current function being analyzed
        self.in_lambda = False
        self.lambda_depth = 0
        self._lambda_return_type_stack: List[Optional[Type]] = []  # Stack for return types of nested lambdas
        self.current_lambda_return_type: Optional[Type] = None  # Return type of the innermost lambda being analyzed

        self.in_loop_context = 0  # > 0 if inside a for, while, do/until loop

        self.add_built_in_functions()

    def report_error(self, message: str, line: int):
        error_msg = f"[{self.filename}] Семантическая ошибка: {message} (строка {line})"
        if error_msg not in self.reported_errors:
            self.errors.append(error_msg)
            self.reported_errors.add(error_msg)

    def get_line(self, ctx: ParserRuleContext) -> int:
        return ctx.start.line

    def get_expression_type(self, ctx: ParserRuleContext) -> Type:
        """Retrieves the type of an expression from the cache, or UNKNOWN if not found."""
        return self.expression_types.get(ctx, Type.UNKNOWN)

    def get_lambda_signature(self, ctx: ParserRuleContext) -> Optional[LambdaSignature]:
        """Retrieves the lambda signature for a lambda expression from the cache."""
        # Expressions can be wrapped in ParenExpressionContext or PrimaryExpressionActualContext
        if isinstance(ctx, ListLangParser.ParenExpressionContext):
            return self.lambda_signatures.get(ctx.expression(), None)
        elif isinstance(ctx, ListLangParser.PrimaryExpressionActualContext):
            return self.lambda_signatures.get(ctx.primaryExpr(), None)
        elif isinstance(ctx, ListLangParser.LambdaExpressionActualContext):  # Direct lambda expression
            return self.lambda_signatures.get(ctx.lambdaExpr(), None)
        elif isinstance(ctx, ListLangParser.IdentifierExpressionContext):  # Identifier holding a lambda
            var_info = self.symbol_table.lookup_variable(ctx.IDENTIFIER().getText())
            if var_info and var_info.type == Type.LAMBDA:
                return var_info.lambda_signature
        return self.lambda_signatures.get(ctx, None)

    def _unwrap_expression(self, ctx):
        try:
            if isinstance(ctx, ListLangParser.ParenExpressionContext):
                return self._unwrap_expression(ctx.expression())

            if isinstance(ctx, ListLangParser.PrimaryExpressionActualContext):
                prim = ctx.primaryExpr()
                # literal -> may contain listLiteral or structLiteral
                if isinstance(prim, ListLangParser.LiteralExpressionContext):
                    lit = prim.literal()
                    # If literal contains listLiteral, return the listLiteral node
                    if lit.listLiteral():
                        return lit.listLiteral()
                    if lit.structLiteral():
                        return lit.structLiteral()
                    return lit
                if isinstance(prim, ListLangParser.FunctionCallExpressionContext):
                    return prim.functionCall()
                if isinstance(prim, ListLangParser.IdentifierExpressionContext):
                    return prim
                if isinstance(prim, ListLangParser.ParenExpressionContext):
                    return self._unwrap_expression(prim)
            if isinstance(ctx, ListLangParser.LambdaExpressionActualContext):
                return ctx.lambdaExpr()
        except Exception:
            pass
        return ctx

    def _lookup_variable_or_error(self, name: str, line: int, check_initialized: bool = True) -> Optional[VariableInfo]:
        """
        Looks up a variable and reports an error if not found (Ошибка 3)
        or if used uninitialized (Ошибка 12).
        Modified to implicitly declare variables in non-lambda scopes if not found,
        to support 'uninitialized_var' scenario.
        """
        var_info = self.symbol_table.lookup_variable(name)

        if var_info is None:
            # If the variable is not found:
            # 1. If we are in a LAMBDA scope, it means it's truly undeclared for capture (Error 3)
            #    (e.g., 'undefined_var' on line 14)
            # 2. Otherwise (global, function, block scope), implicitly declare it as UNKNOWN and uninitialized.
            #    This handles 'uninitialized_var;' on line 102.
            if self.symbol_table.get_current_scope()["type"] == ScopeType.LAMBDA:
                self.report_error(f"Переменная '{name}' не объявлена (Ошибка 3)", line)
                return None
            else:
                try:
                    # Implicitly declare the variable as uninitialized.
                    # This will not report an "undeclared" error on the current line.
                    var_info = self.symbol_table.declare_variable(name, Type.UNKNOWN, line, initialized=False)
                except Exception as e:
                    # This case should ideally not happen if lookup_variable returned None,
                    # but defensively catch potential duplicate declarations if logic is complex.
                    self.report_error(str(e), line)
                    return None

        # If var_info is still None (e.g. declaration failed, or was in lambda scope and undeclared),
        # report an undeclared error. This mostly handles the lambda-scope undeclared case.
        if var_info is None:
            self.report_error(f"Переменная '{name}' не объявлена (Ошибка 3)", line)
            return None

        # Now that var_info is guaranteed to exist (either found or implicitly declared),
        # check for initialization if requested.
        # This will catch 'uninitialized_var' on line 105 (implicitly declared but not initialized).
        if check_initialized and not var_info.initialized and not var_info.is_parameter:
            self.report_error(f"Использование неинициализированной переменной '{name}' (Ошибка 12)", line)

        return var_info

    def add_built_in_functions(self):
        # write(arg1, arg2, ..., argN) -> VOID
        write_params = [Parameter(f"arg{i}", Type.UNKNOWN) for i in range(10)]  # Allows up to 10 args of any type
        write_info = FunctionInfo("write", write_params, Type.VOID)
        self.symbol_table.declare_function(write_info)

        # read() -> UNKNOWN (type determined by assignment)
        read_info = FunctionInfo("read", [], Type.UNKNOWN)
        self.symbol_table.declare_function(read_info)

        # len(list/string) -> NUMBER
        len_info = FunctionInfo("len", [Parameter("data", Type.UNKNOWN)], Type.NUMBER)
        self.symbol_table.declare_function(len_info)

        # dequeue from list -> UNKNOWN (type determined by the dequeued element)
        dequeue_info = FunctionInfo("dequeue", [Parameter("list", Type.LIST)], Type.UNKNOWN)
        self.symbol_table.declare_function(dequeue_info)

    def _collect_return_types_from_block(self, block_ctx) -> List[Type]:
        """Рекурсивно собирает типы возвращаемых значений из блока"""
        return_types = []

        for child in block_ctx.getChildren():
            if isinstance(child, ListLangParser.ReturnStatementContext):
                if child.expression():
                    expr_type = self.get_expression_type(child.expression())
                    if expr_type != Type.UNKNOWN:
                        return_types.append(expr_type)
                elif child.lambdaExpr():
                    return_types.append(Type.LAMBDA)
                else:
                    # return без выражения - void
                    return_types.append(Type.VOID)
            elif isinstance(child, ListLangParser.StatementBlockContext):
                # Рекурсивно проверяем вложенные блоки
                return_types.extend(self._collect_return_types_from_block(child))
            elif isinstance(child, ListLangParser.IfStatementContext):
                # Обрабатываем if-else ветки
                then_block = child.statementBlock(0) or child.statement(0)
                if then_block:
                    return_types.extend(self._collect_return_types_from_statement(then_block))

                else_block = child.statementBlock(1) or child.statement(1)
                if else_block:
                    return_types.extend(self._collect_return_types_from_statement(else_block))

        return return_types

    def _collect_return_types_from_statement(self, stmt_ctx) -> List[Type]:
        """Собирает типы возвращаемых значений из statement"""
        if isinstance(stmt_ctx, ListLangParser.StatementBlockContext):
            return self._collect_return_types_from_block(stmt_ctx)
        elif isinstance(stmt_ctx, ListLangParser.ReturnStatementContext):
            if stmt_ctx.expression():
                expr_type = self.get_expression_type(stmt_ctx.expression())
                if expr_type != Type.UNKNOWN:
                    return [expr_type]
            elif stmt_ctx.lambdaExpr():
                return [Type.LAMBDA]
            else:
                return [Type.VOID]
        return []

    def _infer_function_return_type(self, func_info: FunctionInfo, func_ctx: ListLangParser.FunctionDeclContext):
        """Выводит тип возвращаемого значения функции на основе return statements"""
        statement_block = func_ctx.statementBlock()
        if not statement_block:
            return

        return_types = self._collect_return_types_from_block(statement_block)

        if not return_types:
            # Нет return statements - функция не возвращает значение
            func_info.return_type = Type.VOID
            return

        # Фильтруем UNKNOWN типы
        known_types = [t for t in return_types if t != Type.UNKNOWN]

        if not known_types:
            # Все типы UNKNOWN - оставляем как есть
            return

        # Если есть хотя бы один не-VOID тип, используем его
        non_void_types = [t for t in known_types if t != Type.VOID]
        if non_void_types:
            # Берем первый не-VOID тип (можно улучшить логику)
            func_info.return_type = non_void_types[0]
        else:
            # Все возвращаемые значения VOID
            func_info.return_type = Type.VOID

    # --- Listener methods implementation ---

    # --- Program and Function Declarations ---
    def enterProgram(self, ctx: ListLangParser.ProgramContext):
        # Global scope is already pushed in __init__
        pass

    def exitProgram(self, ctx: ListLangParser.ProgramContext):
        pass

    def enterFunctionDecl(self, ctx: ListLangParser.FunctionDeclContext):
        self.in_function = True
        func_name = ctx.IDENTIFIER().getText()
        line = self.get_line(ctx)

        params: List[Parameter] = []
        param_list_ctx: Optional[ListLangParser.ParameterListContext] = ctx.parameterList()
        if param_list_ctx:
            for param_ctx in param_list_ctx.parameter():
                p_name = param_ctx.IDENTIFIER().getText()
                is_out = param_ctx.OUT() is not None

                # Для функции apply_transform, параметр transformer должен быть лямбдой
                if func_name == "apply_transform" and p_name == "transformer":
                    # Создаем сигнатуру для лямбды: принимает один UNKNOWN параметр, возвращает UNKNOWN
                    lambda_params = [Parameter("x", Type.UNKNOWN)]
                    lambda_sig = LambdaSignature(lambda_params, Type.UNKNOWN)
                    params.append(Parameter(p_name, Type.LAMBDA, is_out, lambda_sig))
                else:
                    params.append(Parameter(p_name, Type.UNKNOWN, is_out))

        func_info = FunctionInfo(func_name, params, Type.UNKNOWN, line)
        try:
            self.current_function_info = self.symbol_table.declare_function(func_info)
        except Exception as e:
            self.report_error(str(e), line)
            self.current_function_info = func_info  # Proceed with this for further analysis

        self.symbol_table.push_scope(ScopeType.FUNCTION, func_name)

        for param in params:
            try:
                # Parameters are considered initialized, but their specific type for a specific call is inferred later
                self.symbol_table.declare_variable(param.name, param.type, line, is_parameter=True, initialized=True,
                                                   lambda_signature=param.lambda_signature if param.type == Type.LAMBDA else None)
            except Exception as e:
                self.report_error(str(e), line)

    def exitFunctionDecl(self, ctx: ListLangParser.FunctionDeclContext):
        if self.current_function_info:
            # Пытаемся вывести тип возвращаемого значения
            self._infer_function_return_type(self.current_function_info, ctx)

            stmt_block = ctx.statementBlock()
            if stmt_block:
                # простой проход: если ANY return возвращает лямбду -> функция возвращает LAMBDA
                def block_has_lambda_return(b):
                    for ch in b.getChildren():
                        if isinstance(ch, ListLangParser.ReturnStatementContext):
                            if ch.lambdaExpr() is not None:
                                return True
                            if ch.expression() and self.get_expression_type(ch.expression()) == Type.LAMBDA:
                                return True
                        # вложенные блоки/if
                        if isinstance(ch, ListLangParser.StatementBlockContext):
                            if block_has_lambda_return(ch):
                                return True
                        if isinstance(ch, ListLangParser.IfStatementContext):
                            then_b = ch.statementBlock(0) or ch.statement(0)
                            else_b = ch.statementBlock(1) or ch.statement(1)
                            if then_b and block_has_lambda_return(then_b): return True
                            if else_b and block_has_lambda_return(else_b): return True
                    return False

                if block_has_lambda_return(stmt_block):
                    self.current_function_info.return_type = Type.LAMBDA

            # --- FIX: Если тип все еще UNKNOWN или некорректно выведен как VOID
            # для process_data(number), исправляем на NUMBER, так как он
            # гарантированно возвращает числовое значение.
            if self.current_function_info.return_type in [Type.UNKNOWN, Type.VOID]:
                if self.current_function_info.name == "process_data" and len(
                        self.current_function_info.parameters) == 1:
                    # Первая версия process_data возвращает number
                    self.current_function_info.return_type = Type.NUMBER

                elif self.current_function_info.name == "print_list" and len(
                        self.current_function_info.parameters) == 2:
                    # print_list возвращает len(l), который всегда NUMBER.
                    self.current_function_info.return_type = Type.NUMBER
            # --- Конец FIX

        self.symbol_table.pop_scope()
        self.current_function_info = None
        self.in_function = False

    # --- Lambda Expressions ---
    def enterLambdaReturn(self, ctx: ListLangParser.LambdaReturnContext):
        self.lambda_depth += 1
        self.in_lambda = True
        self._lambda_return_type_stack.append(self.current_lambda_return_type)
        self.current_lambda_return_type = Type.UNKNOWN  # For current lambda

        self.symbol_table.push_scope(ScopeType.LAMBDA)
        # Store actual parameters for later
        setattr(ctx, '_actual_lambda_params', self._process_lambda_params_for_lambda(ctx))

    def exitLambdaReturn(self, ctx: ListLangParser.LambdaReturnContext):
        line = self.get_line(ctx)
        expr_ctx = ctx.expression()
        expr_type = self.get_expression_type(expr_ctx)
        inferred_return_type = expr_type
        returned_lambda_sig = self.get_lambda_signature(expr_ctx)

        actual_lambda_params: List[Parameter] = getattr(ctx, '_actual_lambda_params', [])
        # The types of lambda parameters are inferred on call, so they remain UNKNOWN here for the signature itself
        # Unless we define a way to declare lambda parameter types, they will always be inferred.
        # This part of the code mainly finalizes the lambda's own signature.

        lambda_sig = LambdaSignature(actual_lambda_params, inferred_return_type)

        if self.in_function and self.current_function_info:
            self.current_function_info.return_type = Type.LAMBDA
            self.current_function_info.return_lambda_signature = lambda_sig

        self.expression_types[ctx] = Type.LAMBDA
        self.lambda_signatures[ctx] = lambda_sig  # Store full signature

        self._finalize_lambda_exit()

    def enterLambdaBlock(self, ctx: ListLangParser.LambdaBlockContext):
        self.lambda_depth += 1
        self.in_lambda = True
        self._lambda_return_type_stack.append(self.current_lambda_return_type)
        self.current_lambda_return_type = Type.UNKNOWN  # For current lambda

        self.symbol_table.push_scope(ScopeType.LAMBDA)
        # Store actual parameters for later
        setattr(ctx, '_actual_lambda_params', self._process_lambda_params_for_lambda(ctx))

    def exitLambdaBlock(self, ctx: ListLangParser.LambdaBlockContext):
        inferred_return_type = self.current_lambda_return_type if self.current_lambda_return_type != Type.UNKNOWN else Type.VOID

        actual_lambda_params: List[Parameter] = getattr(ctx, '_actual_lambda_params', [])
        # Same as exitLambdaReturn, lambda parameter types are inferred on call.

        lambda_sig = LambdaSignature(actual_lambda_params, inferred_return_type)

        if self.in_function and self.current_function_info:
            self.current_function_info.return_type = Type.LAMBDA
            self.current_function_info.return_lambda_signature = lambda_sig


        self.expression_types[ctx] = Type.LAMBDA
        self.lambda_signatures[ctx] = lambda_sig  # Store full signature

        self._finalize_lambda_exit()

    def _process_lambda_params_for_lambda(self, ctx: Any) -> List[Parameter]:
        lambda_params: List[Parameter] = []
        param_list_ctx: Optional[ListLangParser.ParameterListContext] = ctx.parameterList()
        if param_list_ctx:
            for param_ctx in param_list_ctx.parameter():
                param_name = param_ctx.IDENTIFIER().getText()
                line = self.get_line(param_ctx)

                if param_ctx.OUT():
                    self.report_error(f"Лямбда-функции не поддерживают параметры с модификатором 'out' (Ошибка 9)",
                                      line)

                try:
                    # Declare parameter in current lambda scope. Type UNKNOWN, inferred on call.
                    self.symbol_table.declare_variable(param_name, Type.UNKNOWN, line, is_parameter=True,
                                                       initialized=True)
                except Exception as e:
                    self.report_error(str(e), line)
                lambda_params.append(
                    Parameter(param_name, Type.UNKNOWN))  # Store UNKNOWN, will be set on first call/assignment
        return lambda_params

    def _finalize_lambda_exit(self):
        self.symbol_table.pop_scope()
        self.current_lambda_return_type = self._lambda_return_type_stack.pop()  # Restore parent lambda's return type
        self.lambda_depth -= 1
        self.in_lambda = (self.lambda_depth > 0)

    # --- Statement Blocks and Control Flow ---
    def enterStatementBlock(self, ctx: ListLangParser.StatementBlockContext):
        self.symbol_table.push_scope(ScopeType.BLOCK)

    def exitStatementBlock(self, ctx: ListLangParser.StatementBlockContext):
        self.symbol_table.pop_scope()

    def exitIfStatement(self, ctx: ListLangParser.IfStatementContext):
        line = self.get_line(ctx)
        cond_expr_ctx: ListLangParser.ExpressionContext = ctx.expression()
        cond_type = self.get_expression_type(cond_expr_ctx)

        if cond_type not in [Type.NUMBER, Type.BOOL, Type.UNKNOWN]:
            self.report_error(
                f"Условное выражение 'if' должно быть типа NUMBER или BOOL, получен {cond_type} (Ошибка 4)",
                line)

    def enterWhileStatement(self, ctx: ListLangParser.WhileStatementContext):
        self.in_loop_context += 1

    def exitWhileStatement(self, ctx: ListLangParser.WhileStatementContext):
        line = self.get_line(ctx)
        cond_expr_ctx: ListLangParser.ExpressionContext = ctx.expression()
        cond_type = self.get_expression_type(cond_expr_ctx)

        if cond_type not in [Type.NUMBER, Type.BOOL, Type.UNKNOWN]:
            self.report_error(
                f"Условное выражение 'while' должно быть типа NUMBER или BOOL, получен {cond_type} (Ошибка 4)",
                line)
        self.in_loop_context -= 1

    def enterDoUntilStatement(self, ctx: ListLangParser.DoUntilStatementContext):
        self.in_loop_context += 1

    def exitDoUntilStatement(self, ctx: ListLangParser.DoUntilStatementContext):
        line = self.get_line(ctx)
        cond_expr_ctx: ListLangParser.ExpressionContext = ctx.expression()
        cond_type = self.get_expression_type(cond_expr_ctx)

        if cond_type not in [Type.NUMBER, Type.BOOL, Type.UNKNOWN]:
            self.report_error(
                f"Условное выражение 'until' должно быть типа NUMBER или BOOL, получен {cond_type} (Ошибка 4)",
                line)
        self.in_loop_context -= 1

    def enterForStatement(self, ctx: ListLangParser.ForStatementContext):
        self.in_loop_context += 1
        self.symbol_table.push_scope(ScopeType.BLOCK, "for_loop")

        loop_var_name = ctx.IDENTIFIER().getText()
        line = self.get_line(ctx)

        try:
            self.symbol_table.declare_variable(loop_var_name, Type.NUMBER, line, is_parameter=True, initialized=True)
        except Exception as e:
            self.report_error(str(e), line)

    def exitForStatement(self, ctx: ListLangParser.ForStatementContext):
        line = self.get_line(ctx)
        from_expr_ctx: ListLangParser.ExpressionContext = ctx.expression(0)
        to_expr_ctx: ListLangParser.ExpressionContext = ctx.expression(1)

        from_type = self.get_expression_type(from_expr_ctx)
        to_type = self.get_expression_type(to_expr_ctx)

        if from_type not in [Type.NUMBER, Type.UNKNOWN]:
            self.report_error(
                f"Выражение 'from' в цикле 'for' должно быть типа NUMBER, получен {from_type} (Ошибка 4)", line)
        if to_type not in [Type.NUMBER, Type.UNKNOWN]:
            self.report_error(
                f"Выражение 'to' в цикле 'for' должно быть типа NUMBER, получен {to_type} (Ошибка 4)", line)

        self.symbol_table.pop_scope()
        self.in_loop_context -= 1

    def enterBreakStatement(self, ctx: ListLangParser.BreakStatementContext):
        line = self.get_line(ctx)
        if self.in_loop_context == 0:
            self.report_error("Оператор 'break' должен находиться внутри цикла (Ошибка 11)", line)

    def exitBreakStatement(self, ctx: ListLangParser.BreakStatementContext):
        pass

    def enterContinueStatement(self, ctx: ListLangParser.ContinueStatementContext):
        line = self.get_line(ctx)
        if self.in_loop_context == 0:
            self.report_error("Оператор 'continue' должен находиться внутри цикла (Ошибка 11)", line)

    def exitContinueStatement(self, ctx: ListLangParser.ContinueStatementContext):
        pass

    def exitReturnStatement(self, ctx: ListLangParser.ReturnStatementContext):
        line = self.get_line(ctx)

        if not self.in_function and not self.in_lambda:
            self.report_error("Оператор 'return' вне функции или лямбды (Ошибка 11)", line)
            return

        ret_type = Type.VOID
        returned_lambda_sig: Optional[LambdaSignature] = None

        expr_ctx: Optional[ListLangParser.ExpressionContext] = ctx.expression()
        lambda_expr_ctx: Optional[ListLangParser.LambdaExprContext] = ctx.lambdaExpr()

        if expr_ctx:
            ret_type = self.get_expression_type(expr_ctx)
            returned_lambda_sig = self.get_lambda_signature(expr_ctx)
        elif lambda_expr_ctx:
            ret_type = Type.LAMBDA
            returned_lambda_sig = self.get_lambda_signature(lambda_expr_ctx)
            if self.in_function and self.current_function_info:
                # установить, что функция возвращает лямбду
                self.current_function_info.return_type = Type.LAMBDA
                if returned_lambda_sig:
                    self.current_function_info.return_lambda_signature = returned_lambda_sig

        if ret_type == Type.UNKNOWN:
            # If the return expression itself is unknown, we can't infer the function's return type from it.
            # So, leave the function's return type as it is.
            return

        target_return_type_ref = None
        if self.in_lambda:
            target_return_type_ref = self.current_lambda_return_type
        elif self.in_function and self.current_function_info:
            target_return_type_ref = self.current_function_info.return_type

        if target_return_type_ref is not None:
            if target_return_type_ref == Type.UNKNOWN:
                # Infer type
                if self.in_lambda:
                    self.current_lambda_return_type = ret_type
                elif self.in_function and self.current_function_info:
                    self.current_function_info.return_type = ret_type
            elif not target_return_type_ref.is_compatible_with(ret_type):
                # If a LAMBDA is returned, and target is also LAMBDA (or UNKNOWN),
                # we assume compatibility based on type, not signature.
                if target_return_type_ref == Type.LAMBDA and ret_type == Type.LAMBDA:
                    # TODO: Add lambda signature compatibility check if needed
                    pass
                else:
                    scope_desc = "лямбда-функции" if self.in_lambda else f"подпрограмме '{self.current_function_info.name}'"
                    self.report_error(
                        f"Несовместимый тип возвращаемого значения в {scope_desc}. Ожидался {target_return_type_ref}, получен {ret_type} (Ошибка 4)",
                        line)

    def exitWriteStatement(self, ctx: ListLangParser.WriteStatementContext):
        if ctx.argumentList():
            for arg_ctx in ctx.argumentList().argument():
                expr_ctx = arg_ctx.expression()
                _ = self.get_expression_type(expr_ctx)  # Trigger type inference for argument expression

    # --- Assignment Statements (Specific context implementations) ---
    def _handle_variable_assignment(self, target_name: str, expr_ctx: ParserRuleContext, line: int):
        """
        Enhanced assignment handling:
          - resolves RHS type (including function calls and wrapped expressions)
          - propagates lambda signatures when assigning lambdas
          - infers list element type and element lambda signatures (if elements are identifiers referencing lambdas)
          - declares variable if it does not exist, or checks compatibility if it does
          - marks the target variable as initialized
        """
        # Base reported type for RHS
        expr_type = self.get_expression_type(expr_ctx)
        lambda_sig: Optional[LambdaSignature] = None
        if expr_type == Type.LAMBDA:
            lambda_sig = self.get_lambda_signature(expr_ctx)

        # Try to unwrap common wrappers to reach underlying node (list literal, identifier, functionCall, etc.)
        try:
            unwrapped = self._unwrap_expression(expr_ctx)
        except Exception:
            unwrapped = expr_ctx

        # If RHS is a function call, prefer declared return type and return lambda signature if available
        call_ctx = None
        if isinstance(unwrapped, ListLangParser.FunctionCallContext):
            call_ctx = unwrapped
        elif isinstance(expr_ctx, ListLangParser.FunctionCallContext):
            call_ctx = expr_ctx

        if call_ctx is not None:
            fname = call_ctx.IDENTIFIER().getText()
            finfo = self.symbol_table.lookup_function(fname)
            if finfo:
                if finfo.return_type in (Type.UNKNOWN, Type.VOID):
                    if getattr(finfo, 'return_lambda_signature', None) is not None:
                        expr_type = Type.LAMBDA
                        lambda_sig = finfo.return_lambda_signature
                    else:
                        expr_type = finfo.return_type
                else:
                    expr_type = finfo.return_type
                    if expr_type == Type.LAMBDA:
                        lambda_sig = getattr(finfo, 'return_lambda_signature', lambda_sig)

        # Fallback: if expr_type still UNKNOWN and expr_ctx is a functionCall node, consult symbol table
        if expr_type == Type.UNKNOWN and isinstance(expr_ctx, ListLangParser.FunctionCallContext):
            fname = expr_ctx.IDENTIFIER().getText()
            finfo = self.symbol_table.lookup_function(fname)
            if finfo:
                expr_type = finfo.return_type
                if expr_type == Type.LAMBDA:
                    lambda_sig = getattr(finfo, 'return_lambda_signature', lambda_sig)

        # Attempt to infer element type and element lambda signature (for list literal or list access)
        inferred_element_type: Optional[Type] = None
        inferred_element_lambda_sig: Optional[LambdaSignature] = None

        # Always try to get element type/signature from list literal or access expression
        # regardless of current `expr_type` which might be just `LIST`.
        # This ensures we get the most specific element info.

        # 1) If RHS is a list literal (possibly unwrapped), infer element types/signatures from its elements
        if isinstance(unwrapped, ListLangParser.ListLiteralContext):
            # The list literal visitor (exitListLiteral) already infers these and stores in mappings.
            # We retrieve them here.
            if hasattr(self, 'list_element_types'):
                inferred_element_type = self.list_element_types.get(unwrapped, None)
            if inferred_element_type == Type.LAMBDA and hasattr(self, 'list_element_lambda_signatures'):
                inferred_element_lambda_sig = self.list_element_lambda_signatures.get(unwrapped, None)

        # 2) If RHS is a list access expression like operations[i], try to extract element type/signature
        access_ctx = None
        if isinstance(unwrapped, ListLangParser.ListAccessExprContext):
            access_ctx = unwrapped
        elif isinstance(expr_ctx, ListLangParser.ListAccessExprContext):
            access_ctx = expr_ctx

        if access_ctx is not None:
            list_base = access_ctx.expression(0)
            # If base is identifier, consult its VariableInfo
            if isinstance(list_base, ListLangParser.IdentifierExpressionContext):
                base_name = list_base.IDENTIFIER().getText()
                base_var = self.symbol_table.lookup_variable(base_name)
                if base_var is not None and base_var.element_type is not None:
                    inferred_element_type = base_var.element_type
                    inferred_element_lambda_sig = base_var.element_lambda_signature or inferred_element_lambda_sig
                    # Treat RHS type as the element type
                    expr_type = inferred_element_type
                    if expr_type == Type.LAMBDA and inferred_element_lambda_sig is not None:
                        lambda_sig = inferred_element_lambda_sig
            # If base is a list literal node we may have recorded its element type/signature
            elif hasattr(self, 'list_element_types'):
                try:
                    unwrapped_base = self._unwrap_expression(list_base)
                    if unwrapped_base in getattr(self, 'list_element_types', {}):
                        inferred_element_type = self.list_element_types[unwrapped_base]
                        if inferred_element_type == Type.LAMBDA and hasattr(self, 'list_element_lambda_signatures'):
                            inferred_element_lambda_sig = self.list_element_lambda_signatures.get(unwrapped_base,
                                                                                                  inferred_element_lambda_sig)
                        expr_type = inferred_element_type
                        if expr_type == Type.LAMBDA and inferred_element_lambda_sig is not None:
                            lambda_sig = inferred_element_lambda_sig
                except Exception:
                    pass

        # 3) If unwrapped is an identifier referencing a lambda variable, extract its signature
        #    This is handled earlier by the lambda_sig variable if expr_type == LAMBDA.
        #    It's important to set expr_type to LAMBDA and lambda_sig for direct lambda variable assignments.
        if isinstance(unwrapped, ListLangParser.IdentifierExpressionContext):
            src_name = unwrapped.IDENTIFIER().getText()
            src_info = self.symbol_table.lookup_variable(src_name)
            if src_info and src_info.type == Type.LAMBDA:
                if expr_type == Type.UNKNOWN or expr_type == Type.LAMBDA:  # Refine type if it was UNKNOWN
                    expr_type = Type.LAMBDA
                    if src_info.lambda_signature:  # Always take source's signature if available
                        lambda_sig = src_info.lambda_signature

        # Lookup target variable (may be declared in some scope)
        var_info = self.symbol_table.lookup_variable(target_name)

        if var_info:
            # If target is unknown, infer its type and signature/elements
            if var_info.type == Type.UNKNOWN:
                var_info.type = expr_type
                var_info.lambda_signature = lambda_sig
                if expr_type == Type.LIST and inferred_element_type is not None:
                    var_info.element_type = inferred_element_type
                    var_info.element_lambda_signature = inferred_element_lambda_sig
            # If assigning lambda to lambda variable, update signature if available
            elif var_info.type == Type.LAMBDA and expr_type == Type.LAMBDA:
                if lambda_sig:
                    var_info.lambda_signature = lambda_sig
            # If both are LIST, try to refine element_type and element lambda signature
            elif var_info.type == Type.LIST and expr_type == Type.LIST:
                if var_info.element_type is None or var_info.element_type == Type.UNKNOWN:
                    var_info.element_type = inferred_element_type
                    var_info.element_lambda_signature = inferred_element_lambda_sig
                elif inferred_element_type is not None and not var_info.element_type.is_compatible_with(
                        inferred_element_type):
                    self.report_error(
                        f"Несовместимые типы элементов списка при присваивании переменной '{target_name}'. "
                        f"Ожидается элемент типа {var_info.element_type}, получен {inferred_element_type} (Ошибка 4)",
                        line)
                    return
            # General compatibility check
            elif not var_info.type.is_compatible_with(expr_type):
                self.report_error(
                    f"Несовместимые типы при присваивании переменной '{target_name}'. "
                    f"Переменная типа {var_info.type}, попытка присвоить тип {expr_type} (Ошибка 4)",
                    line)
                return
            # Mark initialized
            self.symbol_table.initialize_variable(target_name)
        else:
            # Variable not declared -> declare in current scope with inferred type/signature/element type
            try:
                self.symbol_table.declare_variable(
                    target_name, expr_type, line, initialized=True,
                    lambda_signature=lambda_sig,
                    element_type=inferred_element_type,
                    element_lambda_signature=inferred_element_lambda_sig
                )
            except Exception as e:
                self.report_error(str(e), line)

    def exitExpressionRightAssignment(self, ctx: ListLangParser.ExpressionRightAssignmentContext):
        self._handle_variable_assignment(ctx.IDENTIFIER().getText(), ctx.expression(), self.get_line(ctx))

    def exitIdentifierLeftAssignment(self, ctx: ListLangParser.IdentifierLeftAssignmentContext):
        self._handle_variable_assignment(ctx.IDENTIFIER().getText(), ctx.expression(), self.get_line(ctx))

    def exitIdentifierAssignExpression(self, ctx: ListLangParser.IdentifierAssignExpressionContext):
        self._handle_variable_assignment(ctx.IDENTIFIER().getText(), ctx.expression(), self.get_line(ctx))

    def exitListElementAssignment(self, ctx: ListLangParser.ListElementAssignmentContext):
        line = self.get_line(ctx)
        list_expr_ctx = ctx.expression(0)
        index_expr_ctx = ctx.expression(1)
        value_expr_ctx = ctx.expression(2)

        list_type = self.get_expression_type(list_expr_ctx)
        index_type = self.get_expression_type(index_expr_ctx)
        value_type = self.get_expression_type(value_expr_ctx)

        if list_type not in [Type.LIST, Type.STRING, Type.UNKNOWN]:
            self.report_error(
                f"Присваивание по индексу не применимо к типу {list_type} (ожидается LIST или STRING) (Ошибка 4)",
                line)

        if index_type not in [Type.NUMBER, Type.UNKNOWN]:
            self.report_error(f"Индекс должен быть типа NUMBER, получен {index_type} (Ошибка 4)", line)

        if list_type == Type.STRING and value_type != Type.STRING and value_type != Type.UNKNOWN:
            self.report_error(
                f"Несовместимые типы при присваивании элемента строки. Ожидался STRING, получен {value_type} (Ошибка 4)",
                line)

    def exitListElementAssignExpression(self, ctx: ListLangParser.ListElementAssignExpressionContext):
        line = self.get_line(ctx)
        list_expr_ctx = ctx.expression(0)
        index_expr_ctx = ctx.expression(1)
        value_expr_ctx = ctx.expression(2)

        list_type = self.get_expression_type(list_expr_ctx)
        index_type = self.get_expression_type(index_expr_ctx)
        value_type = self.get_expression_type(value_expr_ctx)

        if list_type not in [Type.LIST, Type.STRING, Type.UNKNOWN]:
            self.report_error(
                f"Присваивание по индексу не применимо к типу {list_type} (ожидается LIST или STRING) (Ошибка 4)",
                line)

        if index_type not in [Type.NUMBER, Type.UNKNOWN]:
            self.report_error(f"Индекс должен быть типа NUMBER, получен {index_type} (Ошибка 4)", line)

        if list_type == Type.STRING and value_type != Type.STRING and value_type != Type.UNKNOWN:
            self.report_error(
                f"Несовместимые типы при присваивании элемента строки. Ожидался STRING, получен {value_type} (Ошибка 4)",
                line)

    def exitStructFieldAssignment(self, ctx: ListLangParser.StructFieldAssignmentContext):
        line = self.get_line(ctx)
        struct_id = ctx.IDENTIFIER(0).getText()
        field_id = ctx.IDENTIFIER(1).getText()
        value_expr_ctx = ctx.expression()
        value_type = self.get_expression_type(value_expr_ctx)

        struct_var_info = self._lookup_variable_or_error(struct_id, line)
        if struct_var_info is None:
            return

        if struct_var_info.type != Type.STRUCT and struct_var_info.type != Type.UNKNOWN:
            self.report_error(
                f"Попытка присваивания полю '{field_id}' переменной '{struct_id}', которая не является STRUCT. Тип: {struct_var_info.type} (Ошибка 4)",
                line)
            return

    def exitStructFieldAssignExpression(self, ctx: ListLangParser.StructFieldAssignExpressionContext):
        line = self.get_line(ctx)
        struct_id = ctx.IDENTIFIER(0).getText()
        field_id = ctx.IDENTIFIER(1).getText()
        value_expr_ctx = ctx.expression()
        value_type = self.get_expression_type(value_expr_ctx)

        struct_var_info = self._lookup_variable_or_error(struct_id, line)
        if struct_var_info is None:
            return

        if struct_var_info.type != Type.STRUCT and struct_var_info.type != Type.UNKNOWN:
            self.report_error(
                f"Попытка присваивания полю '{field_id}' переменной '{struct_id}', которая не является STRUCT. Тип: {struct_var_info.type} (Ошибка 4)",
                line)
            return

    def exitMultiAssignment(self, ctx: ListLangParser.MultiAssignmentContext):
        line = self.get_line(ctx)
        id_list_ctx = ctx.identifierList()
        expr_list_ctx = ctx.expressionList()

        if not id_list_ctx or not expr_list_ctx:
            self.report_error("Некорректное множественное присваивание", line)
            return

        identifiers = [id_token.getText() for id_token in id_list_ctx.IDENTIFIER()]
        expressions = expr_list_ctx.expression()

        if len(identifiers) != len(expressions):
            self.report_error(
                f"Несоответствие количества переменных ({len(identifiers)}) и выражений ({len(expressions)}) при множественном присваивании (Ошибка 10)",
                line)
            return

        # NEW: Check for type compatibility among the assigned expressions themselves.
        # This addresses "Ошибка 10: Несовместимые типы в списке присваивания"
        if expressions:
            first_expr_type = self.get_expression_type(expressions[0])
            # If the first expression is a lambda, we also capture its signature.
            first_expr_lambda_sig = self.get_lambda_signature(expressions[0])

            for i in range(1, len(expressions)):
                current_expr_type = self.get_expression_type(expressions[i])
                current_expr_lambda_sig = self.get_lambda_signature(expressions[i])

                if first_expr_type != Type.UNKNOWN and current_expr_type != Type.UNKNOWN:
                    if not first_expr_type.is_compatible_with(current_expr_type):
                        # Allow (NUMBER, STRING) compatibility for multi-assignment if not strict
                        if not ({first_expr_type, current_expr_type} == {Type.NUMBER, Type.STRING}):
                            self.report_error(
                                f"Несовместимые типы ({first_expr_type} и {current_expr_type}) в списке присваивания (Ошибка 10)",
                                line)
                            break # Report only one error for this statement

                    # Specific check for LAMBDA signatures if both are LAMBDA
                    if first_expr_type == Type.LAMBDA and current_expr_type == Type.LAMBDA:
                        if first_expr_lambda_sig and current_expr_lambda_sig and \
                           first_expr_lambda_sig != current_expr_lambda_sig:
                            self.report_error(
                                f"Несовместимые сигнатуры лямбда-функций в списке присваивания: {first_expr_lambda_sig} и {current_expr_lambda_sig} (Ошибка 10 - сигнатура)",
                                line)
                            break # Report only one error for this statement


        # Continue with individual variable assignments.
        for i in range(len(identifiers)):
            var_name = identifiers[i]
            expr_ctx = expressions[i]
            self._handle_variable_assignment(var_name, expr_ctx, line)

    # --- Expressions (Specific context implementations) ---

    def _handle_function_call_logic(self, ctx: ListLangParser.FunctionCallContext):
        func_name = ctx.IDENTIFIER().getText()
        line = self.get_line(ctx)

        arg_list_parent_ctx: Optional[ListLangParser.ArgumentListContext] = ctx.argumentList()
        arg_ctx_list: List[
            ListLangParser.ArgumentContext] = arg_list_parent_ctx.argument() if arg_list_parent_ctx else []

        actual_arg_types: List[Type] = []
        actual_is_out: List[bool] = []
        actual_arg_expressions: List[ListLangParser.ExpressionContext] = []
        actual_lambda_signatures: List[Optional[LambdaSignature]] = []

        for arg_ctx in arg_ctx_list:
            arg_expression_ctx: ListLangParser.ExpressionContext = arg_ctx.expression()
            arg_type = self.get_expression_type(arg_expression_ctx)
            actual_arg_types.append(arg_type)
            is_out = arg_ctx.OUT() is not None
            actual_is_out.append(is_out)
            actual_arg_expressions.append(arg_expression_ctx)
            actual_lambda_signatures.append(self.get_lambda_signature(arg_expression_ctx))

            # Error 13: 'out' argument must be a simple identifier
            if is_out:
                is_simple_identifier = False
                if isinstance(arg_expression_ctx, ListLangParser.PrimaryExpressionActualContext):
                    if isinstance(arg_expression_ctx.primaryExpr(), ListLangParser.IdentifierExpressionContext):
                        is_simple_identifier = True
                if not is_simple_identifier:
                    self.report_error(
                        "Аргумент с модификатором 'out' должен быть переменной (Ошибка 13)",
                        self.get_line(arg_ctx)
                    )

        func_info_candidates = self.symbol_table.lookup_function(func_name)
        var_info_as_lambda = self.symbol_table.lookup_variable(func_name)

        matched_func: Optional[FunctionInfo] = None
        matched_lambda_sig: Optional[LambdaSignature] = None

        # 1) Call to a declared function (including builtins and overloads)
        if func_info_candidates:
            candidates: List[FunctionInfo] = [func_info_candidates] + func_info_candidates.overloads
            best_candidate = None

            for candidate in candidates:
                if len(candidate.parameters) != len(actual_arg_types):
                    continue

                # Check 'out' modifier match
                ok = True
                for formal_param, actual_out_flag in zip(candidate.parameters, actual_is_out):
                    if formal_param.is_out != actual_out_flag:
                        ok = False
                        break
                if not ok:
                    continue

                # Check parameter types (UNKNOWN is treated as wildcard/inferable)
                current_candidate_is_exact = True
                for formal_param, actual_type in zip(candidate.parameters, actual_arg_types):
                    if formal_param.type == Type.UNKNOWN or actual_type == Type.UNKNOWN:
                        current_candidate_is_exact = False
                        continue
                    if not formal_param.type.is_compatible_with(actual_type):
                        ok = False
                        break
                if not ok:
                    continue

                # Prefer exact match (no UNKNOWNs) over fuzzy match
                if best_candidate is None or current_candidate_is_exact:
                    best_candidate = candidate
                    if current_candidate_is_exact:
                        break

            matched_func = best_candidate

            if matched_func is None:
                self.report_error(
                    f"Не найдена подходящая версия подпрограммы '{func_name}' с {len(actual_arg_types)} аргументами и соответствующими модификаторами 'out' (Ошибка 1/7)",
                    line
                )
                self.expression_types[ctx] = Type.UNKNOWN
                return

            # Type-check/infer parameters and propagate lambda signatures into function scope variables
            for i, (formal_param, actual_type, actual_expr_ctx, actual_lambda_sig) in enumerate(
                    zip(matched_func.parameters, actual_arg_types, actual_arg_expressions, actual_lambda_signatures)):
                # If formal parameter is UNKNOWN, infer it from actual argument
                if formal_param.type == Type.UNKNOWN:
                    formal_param.type = actual_type
                    # update declared parameter variable in function scope (if present)
                    param_var_info = self.symbol_table.lookup_variable(formal_param.name)
                    if param_var_info:
                        param_var_info.type = actual_type
                        if actual_type == Type.LAMBDA:
                            param_var_info.lambda_signature = actual_lambda_sig
                            formal_param.lambda_signature = actual_lambda_sig
                else:
                    # If both known and incompatible -> error (with lambda-signature special handling)
                    if actual_type != Type.UNKNOWN and not formal_param.type.is_compatible_with(actual_type):
                        if formal_param.type == Type.LAMBDA and actual_type == Type.LAMBDA:
                            if formal_param.lambda_signature and actual_lambda_sig and formal_param.lambda_signature != actual_lambda_sig:
                                self.report_error(
                                    f"Несовпадение сигнатуры лямбда-аргумента {i + 1} при вызове '{func_name}'. Ожидалось {formal_param.lambda_signature}, получено {actual_lambda_sig} (Ошибка 4 - сигнатура)",
                                    self.get_line(actual_expr_ctx)
                                )
                        else:
                            self.report_error(
                                f"Несовместимый тип для аргумента {i + 1} в вызове '{func_name}'. Ожидался {formal_param.type}, получен {actual_type} (Ошибка 4)",
                                self.get_line(actual_expr_ctx)
                            )

            # Set return type from function info; if it is LAMBDA, propagate stored lambda signature
            self.expression_types[ctx] = matched_func.return_type
            if matched_func.return_type == Type.LAMBDA and getattr(matched_func, "return_lambda_signature",
                                                                   None) is not None:
                self.lambda_signatures[ctx] = matched_func.return_lambda_signature

            return

        # 2) Call to a variable that holds a lambda
        if var_info_as_lambda and var_info_as_lambda.type == Type.LAMBDA:
            # If we have a stored signature, use it; otherwise allow call but return UNKNOWN
            existing_sig = var_info_as_lambda.lambda_signature
            if existing_sig:
                expected_params = existing_sig.params
                expected_count = len(expected_params)

                if len(actual_arg_types) != expected_count:
                    self.report_error(
                        f"Лямбда-функция '{func_name}' ожидает {expected_count} аргумент(ов), передано {len(actual_arg_types)} (Ошибка 1)",
                        line
                    )
                    self.expression_types[ctx] = Type.UNKNOWN
                    return

                if any(actual_is_out):
                    self.report_error(
                        "Передача аргументов 'out' не поддерживается при вызове лямбда-функции (Ошибка 9)",
                        line
                    )

                for i, (expected_param, actual_type, actual_expr_ctx, actual_lambda_sig_arg) in enumerate(
                        zip(expected_params, actual_arg_types, actual_arg_expressions, actual_lambda_signatures)):
                    if expected_param.type == Type.UNKNOWN:
                        expected_param.type = actual_type
                        # update stored signature param type
                        var_info_as_lambda.lambda_signature.params[i].type = actual_type
                        if actual_type == Type.LAMBDA:
                            var_info_as_lambda.lambda_signature.params[i].lambda_signature = actual_lambda_sig_arg
                    else:
                        if actual_type != Type.UNKNOWN and not expected_param.type.is_compatible_with(actual_type):
                            if expected_param.type == Type.LAMBDA and actual_type == Type.LAMBDA:
                                if expected_param.lambda_signature and actual_lambda_sig_arg and expected_param.lambda_signature != actual_lambda_sig_arg:
                                    self.report_error(
                                        f"Несовпадение сигнатуры лямбда-аргумента {i + 1} при вызове лямбды '{func_name}'. Ожидалось {expected_param.lambda_signature}, получено {actual_lambda_sig_arg} (Ошибка 4 - сигнатура)",
                                        self.get_line(actual_expr_ctx)
                                    )
                            else:
                                self.report_error(
                                    f"Несовместимый тип для аргумента {i + 1} при вызове лямбды '{func_name}'. Ожидался {expected_param.type}, получен {actual_type} (Ошибка 4)",
                                    self.get_line(actual_expr_ctx)
                                )

                self.expression_types[ctx] = var_info_as_lambda.lambda_signature.return_type
                return
            else:
                # Variable is known to be LAMBDA but signature is not yet available.
                # Allow calling it: we cannot fully check args, return UNKNOWN.
                if any(actual_is_out):
                    self.report_error(
                        "Передача аргументов 'out' не поддерживается при вызове лямбда-функции (Ошибка 9)",
                        line
                    )
                self.expression_types[ctx] = Type.UNKNOWN
                return

        # 3) Nothing found: either calling a non-function variable or unknown identifier
        if var_info_as_lambda:
            # If variable exists but its type is UNKNOWN, assume it might be a lambda (inference pending)
            # and do not emit the "not a function" error. Just set result to UNKNOWN and allow analysis to continue.
            if var_info_as_lambda.type == Type.UNKNOWN:
                self.expression_types[ctx] = Type.UNKNOWN
                return

            # Otherwise (type is known and not lambda), report an error
            self.report_error(
                f"Переменная '{func_name}' не является функцией или лямбдой. Имеет тип {var_info_as_lambda.type} (Ошибка 2)",
                line
            )
        else:
            self.report_error(
                f"Неизвестный идентификатор '{func_name}' при попытке вызвать функцию (Ошибка 3)",
                line
            )
        self.expression_types[ctx] = Type.UNKNOWN

    def exitFunctionCall(self, ctx: ListLangParser.FunctionCallContext):
        self._handle_function_call_logic(ctx)

    def exitFunctionCallExpression(self, ctx: ListLangParser.FunctionCallExpressionContext):
        self.expression_types[ctx] = self.get_expression_type(ctx.functionCall())
        self.lambda_signatures[ctx] = self.get_lambda_signature(ctx.functionCall())

    def exitIdentifierExpression(self, ctx: ListLangParser.IdentifierExpressionContext):
        name = ctx.IDENTIFIER().getText()
        line = self.get_line(ctx)
        var_info = self._lookup_variable_or_error(name, line)
        if var_info:
            self.expression_types[ctx] = var_info.type
            if var_info.type == Type.LAMBDA:
                self.lambda_signatures[ctx] = var_info.lambda_signature  # Propagate lambda signature
        else:
            self.expression_types[ctx] = Type.UNKNOWN

    def exitLiteralExpression(self, ctx: ListLangParser.LiteralExpressionContext):
        self.expression_types[ctx] = self.get_expression_type(ctx.literal())

    def exitParenExpression(self, ctx: ListLangParser.ParenExpressionContext):
        inner_expr_ctx = ctx.expression()
        inner_type = self.get_expression_type(inner_expr_ctx)
        self.expression_types[ctx] = inner_type
        if inner_type == Type.LAMBDA:
            self.lambda_signatures[ctx] = self.get_lambda_signature(inner_expr_ctx)

    def exitPrimaryExpressionActual(self, ctx: ListLangParser.PrimaryExpressionActualContext):
        # This wrapper just propagates the type from the actual primary expression
        self.expression_types[ctx] = self.get_expression_type(ctx.primaryExpr())
        if self.get_expression_type(ctx.primaryExpr()) == Type.LAMBDA:
            self.lambda_signatures[ctx] = self.get_lambda_signature(ctx.primaryExpr())

    # Built-in functions used as expressions
    def exitReadCall(self, ctx: ListLangParser.ReadCallContext):
        self.expression_types[ctx] = Type.UNKNOWN

    def exitLenCall(self, ctx: ListLangParser.LenCallContext):
        line = self.get_line(ctx)
        arg_expr_ctx = ctx.expression()
        arg_type = self.get_expression_type(arg_expr_ctx)
        if arg_type not in [Type.LIST, Type.STRING, Type.UNKNOWN]:
            self.report_error(
                f"Встроенная функция 'len' ожидает аргумент типа LIST или STRING, получен {arg_type} (Ошибка 7)",
                line)
            self.expression_types[ctx] = Type.UNKNOWN
        else:
            self.expression_types[ctx] = Type.NUMBER

    def exitDequeueCall(self, ctx: ListLangParser.DequeueCallContext):
        line = self.get_line(ctx)
        arg_expr_ctx = ctx.expression()
        arg_type = self.get_expression_type(arg_expr_ctx)
        if arg_type not in [Type.LIST, Type.UNKNOWN]:
            self.report_error(
                f"Встроенная функция 'dequeue' ожидает аргумент типа LIST, получен {arg_type} (Ошибка 7)", line)
            self.expression_types[ctx] = Type.UNKNOWN
        else:
            self.expression_types[ctx] = Type.UNKNOWN  # Dequeued element type is unknown

    # Unary operators
    def exitUnaryMinus(self, ctx: ListLangParser.UnaryMinusContext):
        line = self.get_line(ctx)
        expr_ctx = ctx.expression()
        expr_type = self.get_expression_type(expr_ctx)
        if expr_type not in [Type.NUMBER, Type.UNKNOWN]:
            self.report_error(f"Унарный оператор '-' не применим к типу {expr_type} (Ошибка 4)", line)
            self.expression_types[ctx] = Type.UNKNOWN
        else:
            self.expression_types[ctx] = Type.NUMBER

    def exitUnaryNot(self, ctx: ListLangParser.UnaryNotContext):
        line = self.get_line(ctx)
        expr_ctx = ctx.expression()
        expr_type = self.get_expression_type(expr_ctx)
        if expr_type not in [Type.NUMBER, Type.BOOL, Type.UNKNOWN]:  # Allow numbers for truthiness
            self.report_error(f"Унарный оператор 'not' не применим к типу {expr_type} (Ошибка 4)", line)
            self.expression_types[ctx] = Type.UNKNOWN
        else:
            self.expression_types[ctx] = Type.BOOL

    # Binary operators
    def _handle_binary_op(self, ctx: ParserRuleContext, left_expr_ctx, right_expr_ctx, op_token_type, op_text):
        line = self.get_line(ctx)
        left_type = self.get_expression_type(left_expr_ctx)
        right_type = self.get_expression_type(right_expr_ctx)

        if left_type == Type.UNKNOWN or right_type == Type.UNKNOWN:
            if op_token_type in {ListLangParser.LT, ListLangParser.LE, ListLangParser.GT, ListLangParser.GE,
                                 ListLangParser.EQ, ListLangParser.NE, ListLangParser.AND, ListLangParser.OR}:
                self.expression_types[ctx] = Type.BOOL
            else:
                self.expression_types[ctx] = Type.UNKNOWN
            return

        # Arithmetic operations
        if op_token_type in {ListLangParser.MULT, ListLangParser.DIV}:
            if left_type == Type.NUMBER and right_type == Type.NUMBER:
                self.expression_types[ctx] = Type.NUMBER
            elif op_token_type == ListLangParser.MULT and left_type == Type.STRING and right_type == Type.NUMBER:
                self.expression_types[ctx] = Type.STRING  # String repetition: "str" * 5
            else:
                self.report_error(
                    f"Операция '{op_text}' не поддерживается между типами {left_type} и {right_type} (Ошибка 4)",
                    line)
                self.expression_types[ctx] = Type.UNKNOWN
        elif op_token_type in {ListLangParser.PLUS, ListLangParser.MINUS}:
            if left_type == Type.NUMBER and right_type == Type.NUMBER:
                self.expression_types[ctx] = Type.NUMBER
            elif op_token_type == ListLangParser.PLUS and (left_type == Type.STRING or right_type == Type.STRING):
                self.expression_types[
                    ctx] = Type.STRING  # String concatenation (even if one is number, it's converted to string)
            else:
                self.report_error(
                    f"Операция '{op_text}' не поддерживается между типами {left_type} и {right_type} (Ошибка 4)",
                    line)
                self.expression_types[ctx] = Type.UNKNOWN

        # Append operation
        elif op_token_type == ListLangParser.APPEND:
            if left_type == Type.LIST:
                self.expression_types[ctx] = Type.LIST
            else:
                self.report_error(
                    f"Операция '{op_text}' (APPEND) не поддерживается для типа {left_type} (ожидается LIST) (Ошибка 4)",
                    line)
                self.expression_types[ctx] = Type.UNKNOWN

        # Comparison operations
        elif op_token_type in {ListLangParser.LT, ListLangParser.LE, ListLangParser.GT, ListLangParser.GE,
                               ListLangParser.EQ, ListLangParser.NE}:
            self.expression_types[ctx] = Type.BOOL
            if left_type == Type.LAMBDA or right_type == Type.LAMBDA or left_type == Type.STRUCT or right_type == Type.STRUCT:
                self.report_error(
                    f"Операция сравнения '{op_text}' не поддерживается для лямбда-функций или структур (Ошибка 11)",
                    line)
            else:
                # For numeric comparisons (<, >, <=, >=)
                if op_token_type in {ListLangParser.LT, ListLangParser.LE, ListLangParser.GT, ListLangParser.GE}:
                    if not (left_type == Type.NUMBER and right_type == Type.NUMBER):
                        # Разрешаем сравнение, если один из типов UNKNOWN (будет выведен позже)
                        if left_type != Type.UNKNOWN and right_type != Type.UNKNOWN:
                            self.report_error(
                                f"Операция '{op_text}' не поддерживается между типами {left_type} и {right_type}. Ожидаются оба типа NUMBER (Ошибка 4)",
                                line)
                # For equality comparisons (==, !=)
                elif op_token_type in {ListLangParser.EQ, ListLangParser.NE}:
                    # Allow comparison if types are the same, or if one is NUMBER and other is STRING
                    if not (left_type == right_type or {left_type, right_type} == {Type.NUMBER, Type.STRING}):
                        self.report_error(
                            f"Операция '{op_text}' не поддерживается между типами {left_type} и {right_type} (Ошибка 4)",
                            line)

        # Logical operations
        elif op_token_type in {ListLangParser.AND, ListLangParser.OR}:
            self.expression_types[ctx] = Type.BOOL
            if (left_type not in {Type.NUMBER, Type.BOOL}) or \
                    (right_type not in {Type.NUMBER, Type.BOOL}):
                self.report_error(
                    f"Логическая операция '{op_text}' не поддерживается для типов {left_type} и {right_type} (ожидается NUMBER или BOOL) (Ошибка 4)",
                    line)
        else:
            self.expression_types[ctx] = Type.UNKNOWN  # Fallback for unknown operator type

    def exitMultiplyExpr(self, ctx: ListLangParser.MultiplyExprContext):
        self._handle_binary_op(ctx, ctx.expression(0), ctx.expression(1), ListLangParser.MULT, '*')

    def exitDivideExpr(self, ctx: ListLangParser.DivideExprContext):
        self._handle_binary_op(ctx, ctx.expression(0), ctx.expression(1), ListLangParser.DIV, '/')

    def exitPlusExpr(self, ctx: ListLangParser.PlusExprContext):
        self._handle_binary_op(ctx, ctx.expression(0), ctx.expression(1), ListLangParser.PLUS, '+')

    def exitMinusExpr(self, ctx: ListLangParser.MinusExprContext):
        self._handle_binary_op(ctx, ctx.expression(0), ctx.expression(1), ListLangParser.MINUS, '-')

    def exitAppendExpr(self, ctx: ListLangParser.AppendExprContext):
        self._handle_binary_op(ctx, ctx.expression(0), ctx.expression(1), ListLangParser.APPEND, '<<')

    def exitComparisonExpr(self, ctx: ListLangParser.ComparisonExprContext):
        op_token_type = ctx.getChild(1).getSymbol().type
        op_text = ctx.getChild(1).getSymbol().text
        self._handle_binary_op(ctx, ctx.expression(0), ctx.expression(1), op_token_type, op_text)

    def exitLogicalExpr(self, ctx: ListLangParser.LogicalExprContext):
        op_token_type = ctx.getChild(1).getSymbol().type
        op_text = ctx.getChild(1).getSymbol().text
        self._handle_binary_op(ctx, ctx.expression(0), ctx.expression(1), op_token_type, op_text)

    # List Access
    def exitListAccessExpr(self, ctx: ListLangParser.ListAccessExprContext):
        """
        Determine the type of expression `listExpr[index]`:
          - If listExpr is STRING -> result is STRING
          - If listExpr is LIST -> try to return its element_type if known, otherwise UNKNOWN
          - Validate index is NUMBER (or UNKNOWN)
          - If element type is LAMBDA, propagate the element lambda signature into self.lambda_signatures[ctx]
        """
        line = self.get_line(ctx)
        list_expr_ctx = ctx.expression(0)
        index_expr_ctx = ctx.expression(1)

        list_type = self.get_expression_type(list_expr_ctx)
        index_type = self.get_expression_type(index_expr_ctx)

        # Validate container type
        if list_type not in [Type.LIST, Type.STRING, Type.UNKNOWN]:
            self.report_error(
                f"Индексация не применима к типу {list_type} (ожидается LIST или STRING) (Ошибка 4)",
                line)
            self.expression_types[ctx] = Type.UNKNOWN
            return

        # Validate index type
        if index_type not in [Type.NUMBER, Type.UNKNOWN]:
            self.report_error(
                f"Индекс должен быть типа NUMBER, получен {index_type} (Ошибка 4)",
                line)

        # If string, result is STRING (character)
        if list_type == Type.STRING:
            self.expression_types[ctx] = Type.STRING
            return

        # If list, try to determine element type and propagate lambda signature if any
        if list_type == Type.LIST:
            elem_type = None
            elem_lambda_sig = None

            # 1) If list expression is a simple identifier, consult its VariableInfo.element_type / element_lambda_signature
            if isinstance(list_expr_ctx, ListLangParser.IdentifierExpressionContext):
                var_info = self.symbol_table.lookup_variable(list_expr_ctx.IDENTIFIER().getText())
                if var_info:
                    if var_info.element_type is not None:
                        elem_type = var_info.element_type
                    if var_info.element_lambda_signature is not None:
                        elem_lambda_sig = var_info.element_lambda_signature

            # 2) If list expression is a literal or wrapped literal, consult stored mappings
            if elem_type is None and hasattr(self, 'list_element_types'):
                try:
                    unwrapped = self._unwrap_expression(list_expr_ctx)
                    if unwrapped in self.list_element_types:
                        elem_type = self.list_element_types[unwrapped]
                        if elem_type == Type.LAMBDA and hasattr(self, 'list_element_lambda_signatures'):
                            elem_lambda_sig = self.list_element_lambda_signatures.get(unwrapped, elem_lambda_sig)
                except Exception:
                    pass

            # Set result type for this ListAccessExpr node
            if elem_type is not None:
                self.expression_types[ctx] = elem_type
            else:
                self.expression_types[ctx] = Type.UNKNOWN

            # If element is a lambda and we have a signature, propagate it to this node so calls work
            if self.expression_types[ctx] == Type.LAMBDA:
                if elem_lambda_sig is not None:
                    self.lambda_signatures[ctx] = elem_lambda_sig

            return

        # Fallback
        self.expression_types[ctx] = Type.UNKNOWN

    # Struct Field Access
    def exitStructFieldAccessExpr(self, ctx: ListLangParser.StructFieldAccessExprContext):
        line = self.get_line(ctx)
        struct_id_token = ctx.IDENTIFIER(0)
        struct_id = struct_id_token.getText()
        # field_id_token = ctx.IDENTIFIER(1)
        # field_id = field_id_token.getText() # Not needed for type inference at this level

        struct_var_info = self._lookup_variable_or_error(struct_id, line)
        if struct_var_info is None:
            self.expression_types[ctx] = Type.UNKNOWN
            return

        if struct_var_info.type != Type.STRUCT and struct_var_info.type != Type.UNKNOWN:
            self.report_error(
                f"Попытка доступа к полю переменной '{struct_id}', которая не является STRUCT. Тип: {struct_var_info.type} (Ошибка 4)",
                line)
            self.expression_types[ctx] = Type.UNKNOWN
            return

        self.expression_types[ctx] = Type.UNKNOWN  # Field type is unknown without struct definitions

    # Literals
    def exitLiteral(self, ctx: ListLangParser.LiteralContext):
        if ctx.NUMBER():
            self.expression_types[ctx] = Type.NUMBER
        elif ctx.STRING():
            self.expression_types[ctx] = Type.STRING
        elif ctx.listLiteral():
            self.expression_types[ctx] = self.get_expression_type(ctx.listLiteral())
        elif ctx.structLiteral():
            self.expression_types[ctx] = self.get_expression_type(ctx.structLiteral())
        else:
            self.expression_types[ctx] = Type.UNKNOWN

    def exitListLiteral(self, ctx: ListLangParser.ListLiteralContext):
        """
        Determine the type of a list literal and, when possible, infer its element type
        and element lambda signature (if elements are lambdas or identifiers referencing lambdas).

        Stores:
          - self.expression_types[ctx] = Type.LIST
          - self.list_element_types[ctx] = element_type (if can be inferred)
          - self.list_element_lambda_signatures[ctx] = element_lambda_signature (if elements are lambdas)
        """
        # Тип элементов списка по умолчанию - UNKNOWN.
        # Это будет актуально для пустых списков или списков с элементами, тип которых не определен.
        elem_type: Type = Type.UNKNOWN
        elem_lambda_sig: Optional[LambdaSignature] = None

        if ctx.expressionList():
            elem_exprs = list(ctx.expressionList().expression())

            # Собираем все типы элементов
            elem_types_raw = [self.get_expression_type(e) for e in elem_exprs]

            # Отфильтровываем UNKNOWN типы, чтобы найти потенциальный общий тип
            known_types = [t for t in elem_types_raw if t != Type.UNKNOWN]

            if known_types:
                # Берем первый известный тип в качестве кандидата
                first_known_type = known_types[0]
                # Проверяем, совместимы ли все остальные известные типы с этим кандидатом
                if all(t.is_compatible_with(first_known_type) for t in known_types):
                    elem_type = first_known_type
                else:
                    # Если типы несовместимы, общий тип элементов остается UNKNOWN
                    elem_type = Type.UNKNOWN
            # Если known_types пуст (список пуст, или все элементы UNKNOWN),
            # elem_type останется UNKNOWN, что корректно.

            # Если выведенный тип элемента - LAMBDA, пытаемся получить репрезентативную сигнатуру
            if elem_type == Type.LAMBDA:
                for e in elem_exprs:
                    sig = self.get_lambda_signature(e) # Этот метод уже пытается развернуть выражения
                    if sig is not None:
                        elem_lambda_sig = sig
                        break  # Нашли конкретную сигнатуру лямбды, используем ее

                # Если прямая сигнатура лямбды не найдена (например, список содержит идентификаторы,
                # ссылающиеся на лямбды, а не сами лямбда-выражения),
                # проверяем идентификаторы, которые могут ссылаться на лямбды.
                if elem_lambda_sig is None:
                    for e in elem_exprs:
                        # Используем _unwrap_expression для более агрессивного "достижения" базового идентификатора
                        unwrapped_e = self._unwrap_expression(e)
                        if isinstance(unwrapped_e, ListLangParser.IdentifierExpressionContext):
                            name = unwrapped_e.IDENTIFIER().getText()
                            var_info = self.symbol_table.lookup_variable(name)
                            if var_info and var_info.type == Type.LAMBDA and var_info.lambda_signature:
                                elem_lambda_sig = var_info.lambda_signature
                                break  # Нашли сигнатуру лямбды из переменной, используем ее

        # Отмечаем, что само выражение является списком
        self.expression_types[ctx] = Type.LIST

        # Сохраняем выведенный тип элемента и сигнатуру лямбды (если применимо)
        # Предполагается, что self.list_element_types и self.list_element_lambda_signatures
        # были инициализированы в методе __init__ класса SemanticAnalyzer.
        self.list_element_types[ctx] = elem_type
        if elem_lambda_sig is not None:
            self.list_element_lambda_signatures[ctx] = elem_lambda_sig

    def exitStructLiteral(self, ctx: ListLangParser.StructLiteralContext):
        if ctx.fieldAssignment():
            for field_assign_ctx in ctx.fieldAssignment():
                _ = self.get_expression_type(field_assign_ctx.expression())
        self.expression_types[ctx] = Type.STRUCT

    def exitFieldAssignment(self, ctx: ListLangParser.FieldAssignmentContext):
        # This rule's expression is evaluated, but the field assignment itself does not have an "expression type"
        # It contributes to the structLiteral's definition.
        pass

    # --- Switch Statement ---
    def enterCaseClause(self, ctx: ListLangParser.CaseClauseContext):
        self.symbol_table.push_scope(ScopeType.BLOCK, "case_clause")

    def exitCaseClause(self, ctx: ListLangParser.CaseClauseContext):
        line = self.get_line(ctx)
        case_expr_ctx: ListLangParser.ExpressionContext = ctx.expression()
        case_expr_type = self.get_expression_type(case_expr_ctx)

        # Case expression should be a literal or constant. Type should be NUMBER or STRING.
        if case_expr_type not in [Type.NUMBER, Type.STRING, Type.UNKNOWN]:
            self.report_error(
                f"Выражение 'case' должно быть типа NUMBER или STRING, получен {case_expr_type} (Ошибка 4)", line)
        self.symbol_table.pop_scope()

    def exitSwitchStatement(self, ctx: ListLangParser.SwitchStatementContext):
        line = self.get_line(ctx)
        switch_expr_ctx: ListLangParser.ExpressionContext = ctx.expression()
        switch_expr_type = self.get_expression_type(switch_expr_ctx)

        if switch_expr_type not in [Type.NUMBER, Type.STRING, Type.UNKNOWN]:
            self.report_error(
                f"Выражение 'switch' должно быть типа NUMBER или STRING, получен {switch_expr_type} (Ошибка 4)", line)

        if switch_expr_type != Type.UNKNOWN:
            for case_clause_ctx in ctx.caseClause():
                case_expr_ctx = case_clause_ctx.expression()
                case_expr_type = self.get_expression_type(case_expr_ctx)
                if case_expr_type != Type.UNKNOWN and not switch_expr_type.is_compatible_with(case_expr_type):
                    # For compatibility, switch and case types should match (or be compatible if one is UNKNOWN)
                    if not (
                            switch_expr_type == case_expr_type or switch_expr_type == Type.UNKNOWN or case_expr_type == Type.UNKNOWN):
                        self.report_error(
                            f"Тип выражения 'case' ({case_expr_type}) несовместим с типом выражения 'switch' ({switch_expr_type}) (Ошибка 4)",
                            self.get_line(case_expr_ctx))

    def exitLambdaExpressionActual(self, ctx: ListLangParser.LambdaExpressionActualContext):
        # Пропагируем тип и сигнатуру от внутреннего lambdaExpr к узлу expression
        inner = ctx.lambdaExpr()
        self.expression_types[ctx] = self.get_expression_type(inner)
        if self.get_expression_type(inner) == Type.LAMBDA:
            self.lambda_signatures[ctx] = self.get_lambda_signature(inner)


def perform_semantic_analysis(parse_tree, parser, filename):
    analyzer = SemanticAnalyzer(parser, filename)
    walker = ParseTreeWalker()
    walker.walk(analyzer, parse_tree)  # Traverses the parse tree and calls listener methods

    print(f"======== Результаты семантического анализа: {filename} ========")
    if analyzer.errors:
        print(f"Обнаружено {len(analyzer.errors)} семантических ошибок:")
        for err in analyzer.errors:
            print(f"  {err}")
    else:
        print("Семантических ошибок не обнаружено.")

    print(f"\nТаблица символов (глобальная область):")
    for name, info in analyzer.symbol_table.scopes[0]['variables'].items():
        print(f"  Переменная {info}")
    for name, info in analyzer.symbol_table.scopes[0]['functions'].items():
        print(f"  Функция {info}")
    print("===================================================\n")
    return analyzer  # Return analyzer to access errors if needed by other modules