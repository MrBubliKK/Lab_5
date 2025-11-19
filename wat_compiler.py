import os
import sys
from antlr4 import *
from antlr4.tree.Tree import ParseTreeWalker
from typing import Dict, List, Optional, Tuple, Any, Set

from gen.ListLangParser import ListLangParser
from gen.ListLangListener import ListLangListener

from semantic_analyzer import Type, VariableInfo, FunctionInfo, LambdaSignature, Parameter


class WatCompiler(ListLangListener):
    GENERIC_I32_TEMPS = 2
    GENERIC_F64_TEMPS = 2

    def __init__(self, parser: ListLangParser, semantic_analyzer):
        self.parser = parser
        self.semantic_analyzer = semantic_analyzer
        self.symbol_table = semantic_analyzer.symbol_table

        # Refactored output buffers for better organization
        self.wat_prelude: List[str] = []
        self.wat_globals: List[str] = []
        self.wat_functions: List[str] = []  # For user functions and main logic
        self.wat_lambdas: List[str] = []  # For generated lambdas

        self.current_wat_buffer: List[str] = self.wat_functions  # Default to functions buffer

        self.wat_data_segments: List[str] = []
        self.function_all_locals: Dict[str, Dict[str, str]] = {}
        self.current_function_name: Optional[str] = None
        self.label_counter = 0
        self.loop_stack: List[Dict[str, str]] = []
        self.memory_size_pages = 1
        self.next_data_address = 0

        self.lambda_function_id_counter = 0
        self.generated_lambda_wats: Dict[int, List[str]] = {}
        self.lambda_context_stack: List[Optional[LambdaSignature]] = []
        self.unique_lambda_types_wat: Set[str] = set()

        self._add_wat_prelude()

    def _get_unique_label(self, prefix="label"):
        self.label_counter += 1
        return f"${prefix}_{self.label_counter}"

    def _add_wat_prelude(self):
        self.wat_prelude.append('(module')
        self.wat_prelude.append('  (import "env" "write_num" (func $write_num (param f64)))')
        self.wat_prelude.append('  (import "env" "write_char" (func $write_char (param i32)))')
        self.wat_prelude.append('  (import "env" "read_num" (func $read_num (result f64)))')
        self.wat_prelude.append('  (import "env" "f64_to_string" (func $f64_to_string (param f64) (result i32)))')

        self.wat_prelude.append(f'  (memory (export "memory") {self.memory_size_pages})')
        self.wat_prelude.append('  (global $next_mem_addr (mut i32) (i32.const 0))')

        self.wat_prelude.append("""
  (func $alloc (param $size i32) (result i32)
    (local $ptr i32)
    (global.get $next_mem_addr)
    (local.set $ptr)
    (global.get $next_mem_addr)
    (local.get $size)
    (i32.add)
    (global.set $next_mem_addr)
    (local.get $ptr)
  )
        """)

        self.wat_prelude.append("""
  (func $string_len (param $ptr i32) (result i32)
    (local $len i32)
    (local.set $len (i32.const 0))
    (loop $len_loop
      (block
        (i32.load8_u (i32.add (local.get $ptr) (local.get $len)))
        (i32.const 0)
        (i32.eq)
        (br_if 1)
      )
      (local.set $len (i32.add (local.get $len) (i32.const 1)))
      (br $len_loop)
    )
    (local.get $len)
  )
        """)

        self.wat_prelude.append("""
  (func $string_compare (param $ptr1 i32) (param $ptr2 i32) (result i32)
    (local $len1 i32) (local $len2 i32) (local $i i32)
    (local.set $len1 (call $string_len (local.get $ptr1)))
    (local.set $len2 (call $string_len (local.get $ptr2)))
    (local.get $len1) (local.get $len2) (i32.ne) (if (then (i32.const 0) (return)))
    (local.set $i (i32.const 0))
    (loop $compare_loop
      (local.get $i) (local.get $len1) (i32.ge_s) (if (then (i32.const 1) (return)))
      (i32.load8_u (i32.add (local.get $ptr1) (local.get $i)))
      (i32.load8_u (i32.add (local.get $ptr2) (local.get $i)))
      (i32.ne) (if (then (i32.const 0) (return)))
      (local.set $i (i32.add (local.get $i) (i32.const 1)))
      (br $compare_loop)
    )
    (i32.const 0)
  )
        """)

        self.wat_prelude.append("""
  (func $string_concat (param $val1 f64) (param $val2 f64) (result i32)
    (local $ptr1 i32) (local $ptr2 i32) (local $len1 i32) (local $len2 i32) (local $new_ptr i32) (local $i i32)

    ;; Heuristic: if val in [1..2^32-1], treat it as pointer; else convert number to string
    (local.get $val1) (i32.trunc_f64_s) (local.set $ptr1)
    (local.get $val1) (f64.convert_i32_u) (f64.eq) (if (else
      (local.get $val1) (call $f64_to_string) (local.set $ptr1)
    ))

    (local.get $val2) (i32.trunc_f64_s) (local.set $ptr2)
    (local.get $val2) (f64.convert_i32_u) (f64.eq) (if (else
      (local.get $val2) (call $f64_to_string) (local.set $ptr2)
    ))

    (local.set $len1 (call $string_len (local.get $ptr1)))
    (local.set $len2 (call $string_len (local.get $ptr2)))
    (call $alloc (i32.add (local.get $len1) (i32.add (local.get $len2) (i32.const 1))))
    (local.set $new_ptr)
    (local.set $i (i32.const 0))
    (loop $copy_loop_1
      (local.get $i) (local.get $len1) (i32.lt_s)
      (if (then
        (i32.store8 (i32.add (local.get $new_ptr) (local.get $i)) (i32.load8_u (i32.add (local.get $ptr1) (local.get $i))))
        (local.set $i (i32.add (local.get $i) (i32.const 1)))
        (br $copy_loop_1)
      ))
    )
    (local.set $i (i32.const 0))
    (loop $copy_loop_2
      (local.get $i) (local.get $len2) (i32.lt_s)
      (if (then
        (i32.store8 (i32.add (local.get $new_ptr) (i32.add (local.get $len1) (local.get $i))) (i32.load8_u (i32.add (local.get $ptr2) (local.get $i))))
        (local.set $i (i32.add (local.get $i) (i32.const 1)))
        (br $copy_loop_2)
      ))
    )
    (i32.store8 (i32.add (local.get $new_ptr) (i32.add (local.get $len1) (local.get $len2))) (i32.const 0))
    (local.get $new_ptr)
  )
        """)

        self.wat_prelude.append("""
  (func $string_repeat (param $ptr i32) (param $count f64) (result i32)
    (local $len i32) (local $total_len i32) (local $new_ptr i32) (local $i i32) (local $j i32)
    (local.set $len (call $string_len (local.get $ptr)))
    (local.set $total_len (i32.mul (local.get $len) (i32.trunc_f64_s (local.get $count))))
    (call $alloc (i32.add (local.get $total_len) (i32.const 1)))
    (local.set $new_ptr)
    (local.set $i (i32.const 0))
    (loop $repeat_loop
      (local.get $i) (i32.trunc_f64_s (local.get $count)) (i32.lt_s)
      (if (then
        (local.set $j (i32.const 0))
        (loop $copy_char_loop
          (local.get $j) (local.get $len) (i32.lt_s)
          (if (then
            (i32.store8
              (i32.add (local.get $new_ptr) (i32.add (i32.mul (local.get $i) (local.get $len)) (local.get $j)))
              (i32.load8_u (i32.add (local.get $ptr) (local.get $j)))
            )
            (local.set $j (i32.add (local.get $j) (i32.const 1)))
            (br $copy_char_loop)
          ))
        )
        (local.set $i (i32.add (local.get $i) (i32.const 1)))
        (br $repeat_loop)
      ))
    )
    (i32.store8 (i32.add (local.get $new_ptr) (local.get $total_len)) (i32.const 0))
    (local.get $new_ptr)
  )
        """)

        self.wat_prelude.append("""
  ;; For lists: header layout [len:i32][elem_size:i32][capacity:i32][data...]
  (func $len_list (param $ptr i32) (result f64)
    (f64.convert_i32_u (i32.load (local.get $ptr)))
  )
        """)

        self.wat_prelude.append("""
  (func $dequeue_op (param $list_ptr i32) (result f64)
    (local $len i32) (local $elem_size i32) (local $first_elem_val f64)
    (local.set $len (i32.load (local.get $list_ptr)))
    (local.set $elem_size (i32.load (i32.add (local.get $list_ptr) (i32.const 4))))
    (local.get $len) (i32.const 0) (i32.eq) (if (then (f64.const 0) (return)))

    (local.set $first_elem_val (f64.load (i32.add (local.get $list_ptr) (i32.const 12))))

    (local $new_start i32) (local $old_start i32) (local $num_bytes_to_move i32)
    (local.set $new_start (i32.add (local.get $list_ptr) (i32.const 12)))
    (local.set $old_start (i32.add (local.get $new_start) (local.get $elem_size)))
    (local.set $num_bytes_to_move (i32.mul (i32.sub (local.get $len) (i32.const 1)) (local.get $elem_size)))

    (memory.copy (local.get $new_start) (local.get $old_start) (local.get $num_bytes_to_move))
    (i32.store (local.get $list_ptr) (i32.sub (local.get $len) (i32.const 1)))
    (local.get $first_elem_val)
  )
        """)

        self.wat_prelude.append("""
  (func $list_append (param $list_ptr i32) (param $value f64) (result i32)
    (local $len i32) (local $elem_size i32) (local $capacity i32) (local $new_list_ptr i32)
    (local.set $len (i32.load (local.get $list_ptr)))
    (local.set $elem_size (i32.load (i32.add (local.get $list_ptr) (i32.const 4))))
    (local.set $capacity (i32.load (i32.add (local.get $list_ptr) (i32.const 8))))

    (local.get $len) (local.get $capacity) (i32.ge_s)
    (if (then
      (local.get $capacity) (i32.const 0) (i32.eq) (if (then (local.set $capacity (i32.const 4))))
      (local.set $capacity (i32.mul (local.get $capacity) (i32.const 2)))

      (call $alloc (i32.add (i32.const 12) (i32.mul (local.get $capacity) (local.get $elem_size))))
      (local.set $new_list_ptr)

      (memory.copy
        (local.get $new_list_ptr)
        (local.get $list_ptr)
        (i32.add (i32.const 12) (i32.mul (local.get $len) (local.get $elem_size)))
      )
      (i32.store (i32.add (local.get $new_list_ptr) (i32.const 8)) (local.get $capacity))
      (local.set $list_ptr (local.get $new_list_ptr))
    ))

    (local.get $list_ptr)
    (i32.const 12) (i32.add)
    (local.get $len) (local.get $elem_size) (i32.mul) (i32.add)
    (local.get $value)
    (f64.store)
    (i32.store (local.get $list_ptr) (i32.add (local.get $len) (i32.const 1)))
    (local.get $list_ptr)
  )
        """)

        self.wat_prelude.append('  (table (export "table") 10 funcref)')
        self.wat_prelude.append('  (global $next_table_idx (mut i32) (i32.const 0))')

    def get_wat_type(self, list_lang_type: Type) -> str:
        if list_lang_type in (Type.NUMBER, Type.BOOL):
            return "f64"
        elif list_lang_type in (Type.STRING, Type.LIST, Type.LAMBDA, Type.STRUCT, Type.NULL):
            return "i32"
        elif list_lang_type == Type.VOID:
            return ""
        elif list_lang_type == Type.UNKNOWN:
            return "f64"
        return "f64"

    def _get_element_wat_size(self, elem_type: Type) -> int:
        return 8

    def _get_generic_temp(self, wat_type: str, index: int = 0) -> str:
        if wat_type == "i32":
            if index < self.GENERIC_I32_TEMPS: return f"$tmp_i32_{index}"
        elif wat_type == "f64":
            if index < self.GENERIC_F64_TEMPS: return f"$tmp_f64_{index}"
        raise Exception(f"Compiler Error: No generic temporary of type {wat_type} at index {index}")

    def _collect_function_locals_and_params(self, func_name: str, parameters: List[Parameter],
                                            func_body_ctx: ParserRuleContext):
        if func_name not in self.function_all_locals:
            self.function_all_locals[func_name] = {}

        for param in parameters:
            self.function_all_locals[func_name][param.name] = self.get_wat_type(param.type)

        def walk(ctx):
            if isinstance(ctx, ListLangParser.IdentifierExpressionContext):
                var_name = ctx.IDENTIFIER().getText()
                self._record_local_if_not_global(func_name, var_name)
            elif isinstance(ctx, (ListLangParser.IdentifierAssignExpressionContext,
                                  ListLangParser.ExpressionRightAssignmentContext,
                                  ListLangParser.IdentifierLeftAssignmentContext)):
                var_name = ctx.IDENTIFIER().getText()
                self._record_local_if_not_global(func_name, var_name)
            elif isinstance(ctx, ListLangParser.MultiAssignmentContext):
                if ctx.identifierList():
                    for id_tok in ctx.identifierList().IDENTIFIER():
                        var_name = id_tok.getText()
                        self._record_local_if_not_global(func_name, var_name)
            elif isinstance(ctx, (ListLangParser.ListElementAssignmentContext,
                                  ListLangParser.ListElementAssignExpressionContext)):
                list_expr = ctx.expression(0)
                if isinstance(list_expr, ListLangParser.IdentifierExpressionContext):
                    var_name = list_expr.IDENTIFIER().getText()
                    self._record_local_if_not_global(func_name, var_name)
            elif isinstance(ctx, (ListLangParser.StructFieldAssignmentContext,
                                  ListLangParser.StructFieldAssignExpressionContext)):
                var_name = ctx.IDENTIFIER(0).getText()
                self._record_local_if_not_global(func_name, var_name)
            elif isinstance(ctx, ListLangParser.ForStatementContext):
                var_name = ctx.IDENTIFIER().getText()
                self._record_local_if_not_global(func_name, var_name)

            for i in range(ctx.getChildCount()):
                child = ctx.getChild(i)
                if isinstance(child, ParserRuleContext):
                    walk(child)

        if func_body_ctx:
            walk(func_body_ctx)

    def _record_local_if_not_global(self, func_name: str, var_name: str):
        var_info = self._lookup_var_info_in_flat_table(var_name, func_name)
        if var_info and var_info.scope_name == "global":
            return

        if func_name not in self.function_all_locals:
            self.function_all_locals[func_name] = {}
        if var_name in self.function_all_locals[func_name]:
            return

        wat_type = self.get_wat_type(var_info.type) if var_info else "f64"
        self.function_all_locals[func_name][var_name] = wat_type

    def _build_flat_symbol_table(self):
        """Creates a flat, immutable copy of the symbol table for WAT generation."""
        self.flat_vars: Dict[str, VariableInfo] = {}
        self.flat_funcs: Dict[str, FunctionInfo] = {}

        # 1) Снимаем все функции из глобального скоупа
        for scope in self.semantic_analyzer.symbol_table.scopes:
            for func_name, func_info in scope["functions"].items():
                self.flat_funcs[func_name] = func_info

        # 2) Переносим глобальные переменные (только неквалифицированные имена)
        for scope in self.semantic_analyzer.symbol_table.scopes:
            scope_name = scope["name"]
            scope_type = scope["type"]
            prefix = "" if scope_type.value == "global" else f"{scope_name}::"

            for var_name, var_info in scope["variables"].items():
                qualified_name = f"{prefix}{var_name}"
                self.flat_vars[qualified_name] = var_info

        # 3) ДОБАВЛЕНИЕ: включаем параметры всех функций как локальные переменные
        #    с квалифицированным именем "<func_name>::<param_name>"
        for func_name, func_info in self.flat_funcs.items():
            for p in func_info.parameters:
                # Сконструируем VariableInfo для параметра
                vi = VariableInfo(
                    name=p.name,
                    var_type=p.type,
                    scope_name=func_name,  # квалифицированный скоуп
                    line=func_info.line,
                    is_parameter=True,
                    initialized=True,
                    lambda_signature=p.lambda_signature if p.type == Type.LAMBDA else None
                )
                qualified_name = f"{func_name}::{p.name}"
                # Если вдруг уже есть запись — не затираем, но здесь параметров быть не должно ранее
                self.flat_vars[qualified_name] = vi

    def _lookup_var_info_in_flat_table(self, var_name: str, current_func_name: Optional[str] = None) -> Optional[
        VariableInfo]:
        """Looks up a variable in the flat symbol table, respecting scope."""
        # 1. Локальная переменная/параметр текущей функции
        if current_func_name and current_func_name != "$main":
            qualified_local_name = f"{current_func_name}::{var_name}"
            if qualified_local_name in self.flat_vars:
                return self.flat_vars[qualified_local_name]

        # 2. Глобальная переменная
        if var_name in self.flat_vars:
            return self.flat_vars[var_name]

        # 3. Fallback: любой квалифицированный ключ, оканчивающийся на ::var_name
        for qualified, info in self.flat_vars.items():
            if qualified.endswith(f"::{var_name}"):
                return info

        return None

    def _resolve_variable_access(self, var_name: str) -> Tuple[str, str]:
        """
        Возвращает WAT‑операцию для доступа к переменной (local.get/global.get).
        Если переменная не найдена в таблице символов — создаём её на лету.
        """
        var_info = self._lookup_var_info_in_flat_table(var_name, self.current_function_name)

        if not var_info:
            wat_type = "f64"  # по умолчанию число
            if self.current_function_name and self.current_function_name != "$main":
                # Локальная переменная
                if self.current_function_name not in self.function_all_locals:
                    self.function_all_locals[self.current_function_name] = {}
                if var_name not in self.function_all_locals[self.current_function_name]:
                    self.function_all_locals[self.current_function_name][var_name] = wat_type
                return f"local.get ${var_name}", wat_type
            else:
                # Глобальная переменная
                if f'(global ${var_name} ' not in "".join(self.wat_globals):
                    default_value = "(f64.const 0.0)"
                    self.wat_globals.append(f'  (global ${var_name} (mut {wat_type}) {default_value})')
                return f"global.get ${var_name}", wat_type

        # Если переменная найдена — стандартная логика
        wat_type = self.get_wat_type(var_info.type)
        if self.current_function_name and self.current_function_name != "$main" and var_info.scope_name != "global":
            if self.current_function_name not in self.function_all_locals:
                self.function_all_locals[self.current_function_name] = {}
            if var_name not in self.function_all_locals[self.current_function_name]:
                self.function_all_locals[self.current_function_name][var_name] = wat_type
            return f"local.get ${var_name}", wat_type
        else:
            if f'(global ${var_name} ' not in "".join(self.wat_globals):
                default_value = "(f64.const 0.0)" if wat_type == "f64" else "(i32.const 0)"
                self.wat_globals.append(f'  (global ${var_name} (mut {wat_type}) {default_value})')
            return f"global.get ${var_name}", wat_type

    def _resolve_variable_assignment(self, var_name: str) -> str:
        """
        Возвращает WAT‑операцию для присваивания переменной (local.set/global.set).
        Если переменная не найдена в таблице символов — создаём её на лету.
        """
        var_info = self._lookup_var_info_in_flat_table(var_name, self.current_function_name)

        if not var_info:
            wat_type = "f64"  # по умолчанию число
            if self.current_function_name and self.current_function_name != "$main":
                # Локальная переменная
                if self.current_function_name not in self.function_all_locals:
                    self.function_all_locals[self.current_function_name] = {}
                if var_name not in self.function_all_locals[self.current_function_name]:
                    self.function_all_locals[self.current_function_name][var_name] = wat_type
                return f"local.set ${var_name}"
            else:
                # Глобальная переменная
                if f'(global ${var_name} ' not in "".join(self.wat_globals):
                    default_value = "(f64.const 0.0)"
                    self.wat_globals.append(f'  (global ${var_name} (mut {wat_type}) {default_value})')
                return f"global.set ${var_name}"

        # Если переменная найдена — стандартная логика
        wat_type = self.get_wat_type(var_info.type)
        if self.current_function_name and self.current_function_name != "$main" and var_info.scope_name != "global":
            if self.current_function_name not in self.function_all_locals:
                self.function_all_locals[self.current_function_name] = {}
            if var_name not in self.function_all_locals[self.current_function_name]:
                self.function_all_locals[self.current_function_name][var_name] = wat_type
            return f"local.set ${var_name}"
        else:
            if f'(global ${var_name} ' not in "".join(self.wat_globals):
                default_value = "(f64.const 0.0)" if wat_type == "f64" else "(i32.const 0)"
                self.wat_globals.append(f'  (global ${var_name} (mut {wat_type}) {default_value})')
            return f"global.set ${var_name}"

    def _compile_string_literal(self, s: str):
        escaped_s = ''.join([f'\\{ord(c):02x}' if ord(c) < 32 or ord(c) > 126 or c in ['"', '\\'] else c for c in s])
        current_addr = self.next_data_address
        byte_length = len(s.encode('utf-8')) + 1
        self.wat_data_segments.append(f'  (data (i32.const {current_addr}) "{escaped_s}\\00")')
        self.next_data_address += byte_length
        self.current_wat_buffer.append(f'    (i32.const {current_addr})')

    def _ensure_i32_ptr_on_stack(self, expr_type: Type):
        if self.get_wat_type(expr_type) == "f64":
            self.current_wat_buffer.append('    (i32.trunc_f64_s)')

    def _ensure_f64_on_stack(self, expr_type: Type):
        if self.get_wat_type(expr_type) == "i32":
            self.current_wat_buffer.append('    (f64.convert_i32_u)')

    def enterProgram(self, ctx: ListLangParser.ProgramContext):
        # Build the static symbol table once, before any walking
        self._build_flat_symbol_table()

        self.current_function_name = "$main"
        self.current_wat_buffer.append('  (func $main')

        for i in range(self.GENERIC_I32_TEMPS):
            self.current_wat_buffer.append(f'    (local {self._get_generic_temp("i32", i)} i32)')
        for i in range(self.GENERIC_F64_TEMPS):
            self.current_wat_buffer.append(f'    (local {self._get_generic_temp("f64", i)} f64)')

        # Pre-declare known global variables from the flat table
        for var_name, var_info in self.flat_vars.items():
            # Only declare true globals, not locals with qualified names
            if "::" not in var_name:
                wat_type = self.get_wat_type(var_info.type)
                default_value = "(f64.const 0.0)" if wat_type == "f64" else "(i32.const 0)"
                self.wat_globals.append(f'  (global ${var_name} (mut {wat_type}) {default_value})')

    def exitProgram(self, ctx: ListLangParser.ProgramContext):
        self.current_wat_buffer.append('    (return)')
        self.current_wat_buffer.append('  )')
        self.wat_functions.append('(export "run" (func $main))')

        final_output = []
        final_output.extend(self.wat_prelude)
        final_output.extend(self.wat_globals)

        memory_idx = -1
        for i, line in enumerate(final_output):
            if '(memory ' in line: memory_idx = i; break
        if memory_idx != -1:
            final_output[memory_idx + 1:memory_idx + 1] = self.wat_data_segments

        insert_point = 1
        for type_def in sorted(list(self.unique_lambda_types_wat)):
            final_output.insert(insert_point, f'  {type_def}')
            insert_point += 1

        final_output.extend(self.wat_lambdas)
        final_output.extend(self.wat_functions)
        final_output.append(')')

        self.final_wat_code = "\n".join(final_output)

    def enterFunctionDecl(self, ctx: ListLangParser.FunctionDeclContext):
        func_name = ctx.IDENTIFIER().getText()
        self.current_function_name = func_name
        self.current_wat_buffer = self.wat_functions

        func_info = self.flat_funcs.get(func_name)
        if not func_info:
            raise Exception(f"Compiler Error: Function '{func_name}' info not found in flat symbol table.")

        self.function_all_locals[func_name] = {}
        for p in func_info.parameters:
            self.function_all_locals[func_name][p.name] = self.get_wat_type(p.type)

        self._collect_function_locals_and_params(func_name, func_info.parameters, ctx.statementBlock())

        params_wat = [f"(param ${p.name} {self.get_wat_type(p.type)})" for p in func_info.parameters]
        locals_wat = []
        for var_name, wat_type in self.function_all_locals[func_name].items():
            if not any(p.name == var_name for p in func_info.parameters):
                locals_wat.append(f"(local ${var_name} {wat_type})")

        for i in range(self.GENERIC_I32_TEMPS):
            locals_wat.append(f"(local {self._get_generic_temp('i32', i)} i32)")
        for i in range(self.GENERIC_F64_TEMPS):
            locals_wat.append(f"(local {self._get_generic_temp('f64', i)} f64)")

        result_wat = ""
        if func_info.return_type != Type.VOID:
            result_wat = f"(result {self.get_wat_type(func_info.return_type)})"

        export_clause = f'(export "{func_name}")' if func_name == "main" else ""
        self.current_wat_buffer.append(f'  (func ${func_name} {export_clause} {" ".join(params_wat)} {result_wat}')
        for local_decl in locals_wat:
            self.current_wat_buffer.append(f'    {local_decl}')

    def exitFunctionDecl(self, ctx: ListLangParser.FunctionDeclContext):
        self.current_wat_buffer.append('  )')
        self.current_function_name = None
        self.current_wat_buffer = self.wat_functions

    def exitLiteral(self, ctx: ListLangParser.LiteralContext):
        if ctx.NUMBER():
            num_val = float(ctx.NUMBER().getText())
            self.current_wat_buffer.append(f'    (f64.const {num_val})')
        elif ctx.STRING():
            string_val = ctx.STRING().getText()[1:-1]
            self._compile_string_literal(string_val)
        elif ctx.listLiteral():
            self._compile_list_literal(ctx.listLiteral())
        elif ctx.structLiteral():
            self.current_wat_buffer.append(f'    (i32.const 0)')

    def _compile_list_literal(self, ctx: ListLangParser.ListLiteralContext):
        elements_ctx = ctx.expressionList().expression() if ctx.expressionList() else []
        num_elements = len(elements_ctx)
        elem_size = self._get_element_wat_size(Type.NUMBER)
        initial_capacity = max(num_elements, 4)
        total_size_with_capacity = 12 + initial_capacity * elem_size

        self.current_wat_buffer.append(f'    (i32.const {total_size_with_capacity})')
        self.current_wat_buffer.append(f'    (call $alloc)')
        temp_list_ptr = self._get_generic_temp("i32", 0)
        self.current_wat_buffer.append(f'    (local.set {temp_list_ptr})')

        self.current_wat_buffer.append(f'    (local.get {temp_list_ptr})')
        self.current_wat_buffer.append(f'    (i32.const {num_elements})')
        self.current_wat_buffer.append(f'    (i32.store)')

        self.current_wat_buffer.append(f'    (local.get {temp_list_ptr})')
        self.current_wat_buffer.append(f'    (i32.const 4)')
        self.current_wat_buffer.append(f'    (i32.add)')
        self.current_wat_buffer.append(f'    (i32.const {elem_size})')
        self.current_wat_buffer.append(f'    (i32.store)')

        self.current_wat_buffer.append(f'    (local.get {temp_list_ptr})')
        self.current_wat_buffer.append(f'    (i32.const 8)')
        self.current_wat_buffer.append(f'    (i32.add)')
        self.current_wat_buffer.append(f'    (i32.const {initial_capacity})')
        self.current_wat_buffer.append(f'    (i32.store)')

        for i, elem_ctx in enumerate(elements_ctx):
            elem_type = self.semantic_analyzer.get_expression_type(elem_ctx)
            self.current_wat_buffer.append(f'    (local.get {temp_list_ptr})')
            self.current_wat_buffer.append(f'    (i32.const {12 + i * elem_size})')
            self.current_wat_buffer.append(f'    (i32.add)')
            self._ensure_f64_on_stack(elem_type)
            self.current_wat_buffer.append(f'    (f64.store)')

        self.current_wat_buffer.append(f'    (local.get {temp_list_ptr})')

    def exitIdentifierExpression(self, ctx: ListLangParser.IdentifierExpressionContext):
        var_name = ctx.IDENTIFIER().getText()
        access_op, _ = self._resolve_variable_access(var_name)
        self.current_wat_buffer.append(f'    ({access_op})')

    def exitUnaryMinus(self, ctx: ListLangParser.UnaryMinusContext):
        expr_type = self.semantic_analyzer.get_expression_type(ctx.expression())
        self._ensure_f64_on_stack(expr_type)
        self.current_wat_buffer.append('    (f64.neg)')

    def exitUnaryNot(self, ctx: ListLangParser.UnaryNotContext):
        expr_type = self.semantic_analyzer.get_expression_type(ctx.expression())
        self._ensure_f64_on_stack(expr_type)
        self.current_wat_buffer.append('    (f64.const 0.0)')
        self.current_wat_buffer.append('    (f64.eq)')
        self.current_wat_buffer.append('    (f64.convert_i32_u)')

    def _compile_binary_op(self, ctx, op_wat_f64=None, custom_call=None):
        left_type = self.semantic_analyzer.get_expression_type(ctx.expression(0))
        right_type = self.semantic_analyzer.get_expression_type(ctx.expression(1))
        if custom_call:
            self._ensure_f64_on_stack(left_type)
            self._ensure_f64_on_stack(right_type)
            self.current_wat_buffer.append(f'    (call {custom_call})')
        elif op_wat_f64:
            self._ensure_f64_on_stack(left_type)
            self._ensure_f64_on_stack(right_type)
            self.current_wat_buffer.append(f'    ({op_wat_f64})')
        else:
            raise Exception("Compiler Error: Unsupported binary op")

    def exitMultiplyExpr(self, ctx: ListLangParser.MultiplyExprContext):
        left_type = self.semantic_analyzer.get_expression_type(ctx.expression(0))
        right_type = self.semantic_analyzer.get_expression_type(ctx.expression(1))
        if left_type == Type.STRING and right_type in (Type.NUMBER, Type.BOOL):
            self.current_wat_buffer.append('    (i32.trunc_f64_s)')
            self.current_wat_buffer.append('    (call $string_repeat)')
        else:
            self._compile_binary_op(ctx, "f64.mul")

    def exitDivideExpr(self, ctx: ListLangParser.DivideExprContext):
        self._compile_binary_op(ctx, "f64.div")

    def exitPlusExpr(self, ctx: ListLangParser.PlusExprContext):
        left_type = self.semantic_analyzer.get_expression_type(ctx.expression(0))
        right_type = self.semantic_analyzer.get_expression_type(ctx.expression(1))
        if left_type == Type.STRING or right_type == Type.STRING:
            self._compile_binary_op(ctx, custom_call="$string_concat")
        else:
            self._compile_binary_op(ctx, "f64.add")

    def exitMinusExpr(self, ctx: ListLangParser.MinusExprContext):
        self._compile_binary_op(ctx, "f64.sub")

    def exitAppendExpr(self, ctx: ListLangParser.AppendExprContext):
        list_type = self.semantic_analyzer.get_expression_type(ctx.expression(0))
        self._ensure_i32_ptr_on_stack(list_type)
        self.current_wat_buffer.append('    (call $list_append)')

    def exitComparisonExpr(self, ctx: ListLangParser.ComparisonExprContext):
        op_token_type = ctx.getChild(1).getSymbol().type
        left_type = self.semantic_analyzer.get_expression_type(ctx.expression(0))
        right_type = self.semantic_analyzer.get_expression_type(ctx.expression(1))

        if left_type == Type.STRING and right_type == Type.STRING and op_token_type in (
        ListLangParser.EQ, ListLangParser.NE):
            self.current_wat_buffer.append('    (i32.trunc_f64_s)')
            self.current_wat_buffer.append('    (i32.trunc_f64_s)')
            self.current_wat_buffer.append('    (call $string_compare)')
            if op_token_type == ListLangParser.EQ:
                self.current_wat_buffer.append('    (f64.convert_i32_u)')
            else:
                self.current_wat_buffer.append('    (i32.const 0)')
                self.current_wat_buffer.append('    (i32.eq)')
                self.current_wat_buffer.append('    (f64.convert_i32_u)')
            return

        self._ensure_f64_on_stack(left_type)
        self._ensure_f64_on_stack(right_type)
        if op_token_type == ListLangParser.LT:
            op = "f64.lt"
        elif op_token_type == ListLangParser.LE:
            op = "f64.le"
        elif op_token_type == ListLangParser.GT:
            op = "f64.gt"
        elif op_token_type == ListLangParser.GE:
            op = "f64.ge"
        elif op_token_type == ListLangParser.EQ:
            op = "f64.eq"
        else:
            op = "f64.ne"
        self.current_wat_buffer.append(f'    ({op})')
        self.current_wat_buffer.append('    (f64.convert_i32_u)')

    def exitLogicalExpr(self, ctx: ListLangParser.LogicalExprContext):
        op_token_type = ctx.getChild(1).getSymbol().type
        left_type = self.semantic_analyzer.get_expression_type(ctx.expression(0))
        right_type = self.semantic_analyzer.get_expression_type(ctx.expression(1))
        self._ensure_f64_on_stack(left_type)
        self.current_wat_buffer.append('    (f64.const 0.0)')
        self.current_wat_buffer.append('    (f64.ne)')
        self._ensure_f64_on_stack(right_type)
        self.current_wat_buffer.append('    (f64.const 0.0)')
        self.current_wat_buffer.append('    (f64.ne)')
        if op_token_type == ListLangParser.AND:
            self.current_wat_buffer.append('    (i32.and)')
        else:
            self.current_wat_buffer.append('    (i32.or)')
        self.current_wat_buffer.append('    (f64.convert_i32_u)')

    def exitListAccessExpr(self, ctx: ListLangParser.ListAccessExprContext):
        list_expr_ctx = ctx.expression(0)
        index_expr_ctx = ctx.expression(1)
        element_type = self.semantic_analyzer.expression_types.get(ctx, Type.UNKNOWN)
        list_base_type = self.semantic_analyzer.get_expression_type(list_expr_ctx)

        temp_idx = self._get_generic_temp("f64", 0)
        temp_list_ptr = self._get_generic_temp("i32", 0)

        self._ensure_f64_on_stack(self.semantic_analyzer.get_expression_type(index_expr_ctx))
        self.current_wat_buffer.append(f'    (local.set {temp_idx})')

        if self.get_wat_type(list_base_type) == "f64":
            self.current_wat_buffer.append('    (i32.trunc_f64_s)')
        self.current_wat_buffer.append(f'    (local.set {temp_list_ptr})')

        elem_size = self._get_element_wat_size(element_type)
        self.current_wat_buffer.append(f'    (local.get {temp_list_ptr})')
        self.current_wat_buffer.append('    (i32.const 12)')
        self.current_wat_buffer.append('    (i32.add)')
        self.current_wat_buffer.append(f'    (local.get {temp_idx})')
        self.current_wat_buffer.append('    (i32.trunc_f64_s)')
        self.current_wat_buffer.append(f'    (i32.const {elem_size})')
        self.current_wat_buffer.append('    (i32.mul)')
        self.current_wat_buffer.append('    (i32.add)')
        self.current_wat_buffer.append('    (f64.load)')

    def exitStructFieldAccessExpr(self, ctx: ListLangParser.StructFieldAccessExprContext):
        struct_type = self.semantic_analyzer.get_expression_type(ctx.IDENTIFIER(0))
        self._ensure_f64_on_stack(struct_type)
        self.current_wat_buffer.append('    (drop)')
        self.current_wat_buffer.append('    (f64.const 0.0)')

    def _handle_assignment_to_identifier(self, var_name: str, expr_ctx: ParserRuleContext):
        assign_op = self._resolve_variable_assignment(var_name)
        expr_type = self.semantic_analyzer.get_expression_type(expr_ctx)

        var_info = self._lookup_var_info_in_flat_table(var_name, self.current_function_name)
        target_wat_type = self.get_wat_type(var_info.type) if var_info else self.get_wat_type(expr_type)
        expr_wat_type = self.get_wat_type(expr_type)

        if target_wat_type == "f64" and expr_wat_type == "i32":
            self.current_wat_buffer.append('    (f64.convert_i32_u)')
        elif target_wat_type == "i32" and expr_wat_type == "f64":
            self.current_wat_buffer.append('    (i32.trunc_f64_s)')
        self.current_wat_buffer.append(f'    ({assign_op})')

    def exitIdentifierAssignExpression(self, ctx: ListLangParser.IdentifierAssignExpressionContext):
        self._handle_assignment_to_identifier(ctx.IDENTIFIER().getText(), ctx.expression())

    def exitExpressionRightAssignment(self, ctx: ListLangParser.ExpressionRightAssignmentContext):
        self._handle_assignment_to_identifier(ctx.IDENTIFIER().getText(), ctx.expression())

    def exitIdentifierLeftAssignment(self, ctx: ListLangParser.IdentifierLeftAssignmentContext):
        self._handle_assignment_to_identifier(ctx.IDENTIFIER().getText(), ctx.expression())

    def exitListElementAssignment(self, ctx: ListLangParser.ListElementAssignmentContext):
        list_expr_ctx = ctx.expression(0)
        value_expr_ctx = ctx.expression(2)

        temp_value = self._get_generic_temp("f64", 0)
        temp_index = self._get_generic_temp("f64", 1)
        temp_list_ptr = self._get_generic_temp("i32", 0)

        value_type = self.semantic_analyzer.get_expression_type(value_expr_ctx)
        list_base_type = self.semantic_analyzer.get_expression_type(list_expr_ctx)

        self._ensure_f64_on_stack(value_type)
        self.current_wat_buffer.append(f'    (local.set {temp_value})')

        self._ensure_f64_on_stack(self.semantic_analyzer.get_expression_type(ctx.expression(1)))
        self.current_wat_buffer.append(f'    (local.set {temp_index})')

        if self.get_wat_type(list_base_type) == "f64":
            self.current_wat_buffer.append('    (i32.trunc_f64_s)')
        self.current_wat_buffer.append(f'    (local.set {temp_list_ptr})')

        elem_size = self._get_element_wat_size(Type.NUMBER)
        self.current_wat_buffer.append(f'    (local.get {temp_list_ptr})')
        self.current_wat_buffer.append('    (i32.const 12)')
        self.current_wat_buffer.append('    (i32.add)')
        self.current_wat_buffer.append(f'    (local.get {temp_index})')
        self.current_wat_buffer.append('    (i32.trunc_f64_s)')
        self.current_wat_buffer.append(f'    (i32.const {elem_size})')
        self.current_wat_buffer.append('    (i32.mul)')
        self.current_wat_buffer.append('    (i32.add)')
        self.current_wat_buffer.append(f'    (local.get {temp_value})')
        self.current_wat_buffer.append(f'    (f64.store)')

    def exitListElementAssignExpression(self, ctx: ListLangParser.ListElementAssignExpressionContext):
        self.exitListElementAssignment(ctx)

    def exitStructFieldAssignment(self, ctx: ListLangParser.StructFieldAssignmentContext):
        value_expr_ctx = ctx.expression()
        temp_value = self._get_generic_temp("f64", 0)
        temp_struct_ptr = self._get_generic_temp("i32", 0)
        value_type = self.semantic_analyzer.get_expression_type(value_expr_ctx)

        self._ensure_f64_on_stack(value_type)
        self.current_wat_buffer.append(f'    (local.set {temp_value})')

        var_info = self._lookup_var_info_in_flat_table(ctx.IDENTIFIER(0).getText(), self.current_function_name)
        self._ensure_f64_on_stack(var_info.type if var_info else Type.UNKNOWN)
        self.current_wat_buffer.append(f'    (local.set {temp_struct_ptr})')

        self.current_wat_buffer.append(f'    (local.get {temp_struct_ptr})')
        self.current_wat_buffer.append(f'    (i32.const 0)')
        self.current_wat_buffer.append(f'    (i32.add)')
        self.current_wat_buffer.append(f'    (local.get {temp_value})')
        self.current_wat_buffer.append(f'    (f64.store)')

    def exitStructFieldAssignExpression(self, ctx: ListLangParser.StructFieldAssignExpressionContext):
        self.exitStructFieldAssignment(ctx)

    def exitMultiAssignment(self, ctx: ListLangParser.MultiAssignmentContext):
        identifiers = [id_token.getText() for id_token in ctx.identifierList().IDENTIFIER()]
        expressions = ctx.expressionList().expression()

        temp_f64_idx = 0
        temp_i32_idx = 0
        temp_assignment_locals = []

        for expr_ctx in expressions:
            expr_type = self.semantic_analyzer.get_expression_type(expr_ctx)
            wat_type = self.get_wat_type(expr_type)
            if wat_type == "f64":
                temp_name = self._get_generic_temp("f64", temp_f64_idx); temp_f64_idx += 1
            else:
                temp_name = self._get_generic_temp("i32", temp_i32_idx); temp_i32_idx += 1
            self.current_wat_buffer.append(f'    (local.set {temp_name})')
            temp_assignment_locals.append((temp_name, expr_type))

        for i, var_name in enumerate(identifiers):
            temp_name, expr_type_from_temp = temp_assignment_locals[i]
            assign_op = self._resolve_variable_assignment(var_name)
            self.current_wat_buffer.append(f'    (local.get {temp_name})')

            var_info = self._lookup_var_info_in_flat_table(var_name, self.current_function_name)
            if not var_info:
                raise Exception(f"Compiler Error: Variable '{var_name}' not found for multi-assignment.")
            target_wat_type = self.get_wat_type(var_info.type)
            expr_wat_type = self.get_wat_type(expr_type_from_temp)

            if target_wat_type == "f64" and expr_wat_type == "i32":
                self.current_wat_buffer.append('    (f64.convert_i32_u)')
            elif target_wat_type == "i32" and expr_wat_type == "f64":
                self.current_wat_buffer.append('    (i32.trunc_f64_s)')
            self.current_wat_buffer.append(f'    ({assign_op})')

    def exitIfStatement(self, ctx: ListLangParser.IfStatementContext):
        cond_expr_type = self.semantic_analyzer.get_expression_type(ctx.expression())
        self._ensure_f64_on_stack(cond_expr_type)
        self.current_wat_buffer.append('    (f64.const 0.0)')
        self.current_wat_buffer.append('    (f64.ne)')
        self.current_wat_buffer.append('    (if')
        self.current_wat_buffer.append('      (then')
        self.current_wat_buffer.append('      )')
        if ctx.ELSE():
            self.current_wat_buffer.append('      (else')
            self.current_wat_buffer.append('      )')
        self.current_wat_buffer.append('    )')

    def enterWhileStatement(self, ctx: ListLangParser.WhileStatementContext):
        block_label = self._get_unique_label("while_block")
        loop_label = self._get_unique_label("while_loop")
        self.loop_stack.append({'block': block_label, 'loop': loop_label})
        self.current_wat_buffer.append(f'    (block {block_label}')
        self.current_wat_buffer.append(f'      (loop {loop_label}')

    def exitWhileStatement(self, ctx: ListLangParser.WhileStatementContext):
        cond_expr_type = self.semantic_analyzer.get_expression_type(ctx.expression())
        self._ensure_f64_on_stack(cond_expr_type)
        self.current_wat_buffer.append('        (f64.const 0.0)')
        self.current_wat_buffer.append('        (f64.eq)')
        self.current_wat_buffer.append(f'        (br_if {self.loop_stack[-1]["block"]})')
        self.current_wat_buffer.append(f'        (br {self.loop_stack[-1]["loop"]})')
        self.current_wat_buffer.append('      )')
        self.current_wat_buffer.append('    )')
        self.loop_stack.pop()

    def enterDoUntilStatement(self, ctx: ListLangParser.DoUntilStatementContext):
        block_label = self._get_unique_label("dountil_block")
        loop_label = self._get_unique_label("dountil_loop")
        self.loop_stack.append({'block': block_label, 'loop': loop_label})
        self.current_wat_buffer.append(f'    (block {block_label}')
        self.current_wat_buffer.append(f'      (loop {loop_label}')

    def exitDoUntilStatement(self, ctx: ListLangParser.DoUntilStatementContext):
        cond_expr_type = self.semantic_analyzer.get_expression_type(ctx.expression())
        self._ensure_f64_on_stack(cond_expr_type)
        self.current_wat_buffer.append('        (f64.const 0.0)')
        self.current_wat_buffer.append('        (f64.ne)')
        self.current_wat_buffer.append(f'        (br_if {self.loop_stack[-1]["block"]})')
        self.current_wat_buffer.append(f'        (br {self.loop_stack[-1]["loop"]})')
        self.current_wat_buffer.append('      )')
        self.current_wat_buffer.append('    )')
        self.loop_stack.pop()

    def enterForStatement(self, ctx: ListLangParser.ForStatementContext):
        loop_var_name = ctx.IDENTIFIER().getText()
        if self.current_function_name:
            if self.current_function_name not in self.function_all_locals:
                self.function_all_locals[self.current_function_name] = {}
            self.function_all_locals[self.current_function_name][loop_var_name] = "f64"

        temp_for_to = self._get_generic_temp("f64", 0)
        block_label = self._get_unique_label("for_block")
        loop_label = self._get_unique_label("for_loop")
        self.loop_stack.append({'block': block_label, 'loop': loop_label})

        self._ensure_f64_on_stack(self.semantic_analyzer.get_expression_type(ctx.expression(1)))
        self.current_wat_buffer.append(f'    (local.set {temp_for_to})')
        self._ensure_f64_on_stack(self.semantic_analyzer.get_expression_type(ctx.expression(0)))
        self.current_wat_buffer.append(f'    (local.set ${loop_var_name})')
        self.current_wat_buffer.append(f'    (block {block_label}')
        self.current_wat_buffer.append(f'      (loop {loop_label}')
        self.current_wat_buffer.append(f'        (local.get ${loop_var_name})')
        self.current_wat_buffer.append(f'        (local.get {temp_for_to})')
        self.current_wat_buffer.append(f'        (f64.gt)')
        self.current_wat_buffer.append(f'        (br_if {block_label})')

    def exitForStatement(self, ctx: ListLangParser.ForStatementContext):
        loop_var_name = ctx.IDENTIFIER().getText()
        self.current_wat_buffer.append(f'        (local.get ${loop_var_name})')
        self.current_wat_buffer.append('        (f64.const 1.0)')
        self.current_wat_buffer.append('        (f64.add)')
        self.current_wat_buffer.append(f'        (local.set ${loop_var_name})')
        self.current_wat_buffer.append(f'        (br {self.loop_stack[-1]["loop"]})')
        self.current_wat_buffer.append('      )')
        self.current_wat_buffer.append('    )')
        self.loop_stack.pop()

    def exitBreakStatement(self, ctx: ListLangParser.BreakStatementContext):
        if self.loop_stack:
            self.current_wat_buffer.append(f'    (br {self.loop_stack[-1]["block"]})')
        else:
            raise Exception("Compiler Error: 'break' outside of loop.")

    def exitContinueStatement(self, ctx: ListLangParser.ContinueStatementContext):
        if self.loop_stack:
            self.current_wat_buffer.append(f'    (br {self.loop_stack[-1]["loop"]})')
        else:
            raise Exception("Compiler Error: 'continue' outside of loop.")

    def exitReturnStatement(self, ctx: ListLangParser.ReturnStatementContext):
        ret_type = Type.VOID
        if ctx.expression():
            ret_type = self.semantic_analyzer.get_expression_type(ctx.expression())
            self._ensure_f64_on_stack(ret_type)
        elif ctx.lambdaExpr():
            ret_type = Type.LAMBDA
            self.current_wat_buffer.append('    (f64.convert_i32_u)')
        self.current_wat_buffer.append('    (return)')

    def exitWriteStatement(self, ctx: ListLangParser.WriteStatementContext):
        if ctx.argumentList():
            tmp_ptr = self._get_generic_temp("i32", 0)
            tmp_len = self._get_generic_temp("i32", 1)
            for arg_ctx in ctx.argumentList().argument():
                expr_type = self.semantic_analyzer.get_expression_type(arg_ctx.expression())
                if expr_type in (Type.NUMBER, Type.BOOL):
                    self._ensure_f64_on_stack(expr_type)
                    self.current_wat_buffer.append('    (call $write_num)')
                elif expr_type == Type.STRING:
                    self._ensure_f64_on_stack(expr_type)
                    self.current_wat_buffer.append('    (i32.trunc_f64_s)')
                    self.current_wat_buffer.append(f'    (local.set {tmp_ptr})')
                    self.current_wat_buffer.append(
                        f'    (local.set {tmp_len} (call $string_len (local.get {tmp_ptr})))')
                    counter = self._get_generic_temp("i32", 0)
                    self.current_wat_buffer.append(f'    (local.set {counter} (i32.const 0))')
                    self.current_wat_buffer.append(f'    (loop $print_char_loop')
                    self.current_wat_buffer.append(f'      (local.get {counter}) (local.get {tmp_len}) (i32.lt_s)')
                    self.current_wat_buffer.append('      (if (then')
                    self.current_wat_buffer.append(
                        f'        (call $write_char (i32.load8_u (i32.add (local.get {tmp_ptr}) (local.get {counter}))))')
                    self.current_wat_buffer.append(
                        f'        (local.set {counter} (i32.add (local.get {counter}) (i32.const 1)))')
                    self.current_wat_buffer.append('        (br $print_char_loop)')
                    self.current_wat_buffer.append('      ))')
                    self.current_wat_buffer.append('    )')
                else:
                    self.current_wat_buffer.append('    (drop)')

    def exitReadCall(self, ctx: ListLangParser.ReadCallContext):
        self.current_wat_buffer.append('    (call $read_num)')

    def exitLenCall(self, ctx: ListLangParser.LenCallContext):
        arg_type = self.semantic_analyzer.get_expression_type(ctx.expression())
        if arg_type == Type.STRING:
            self._ensure_f64_on_stack(arg_type)
            self.current_wat_buffer.append('    (i32.trunc_f64_s)')
            self.current_wat_buffer.append('    (call $string_len)')
            self.current_wat_buffer.append('    (f64.convert_i32_u)')
        else:
            self._ensure_f64_on_stack(arg_type)
            self.current_wat_buffer.append('    (i32.trunc_f64_s)')
            self.current_wat_buffer.append('    (call $len_list)')

    def exitDequeueCall(self, ctx: ListLangParser.DequeueCallContext):
        arg_type = self.semantic_analyzer.get_expression_type(ctx.expression())
        self._ensure_f64_on_stack(arg_type)
        self.current_wat_buffer.append('    (i32.trunc_f64_s)')
        self.current_wat_buffer.append('    (call $dequeue_op)')

    def exitFunctionCall(self, ctx: ListLangParser.FunctionCallContext):
        """
        Обработка вызова функции или переменной‑лямбды (включая параметры функций).
        """
        func_name = ctx.IDENTIFIER().getText()

        # Извлекаем аргументы: ArgumentListContext -> [ArgumentContext]
        arg_list_parent_ctx: Optional[ListLangParser.ArgumentListContext] = ctx.argumentList()
        arg_ctx_list: List[
            ListLangParser.ArgumentContext] = arg_list_parent_ctx.argument() if arg_list_parent_ctx else []

        # --- Встроенные функции ---
        if func_name == "read":
            if arg_ctx_list:
                raise Exception("Compiler Error: 'read' function does not take arguments.")
            self.current_wat_buffer.append('    (call $read_num)')
            return
        elif func_name == "write":
            # write обрабатывается отдельным правилом exitWriteStatement
            self.current_wat_buffer.append('    (nop)')
            return
        elif func_name in ("len", "dequeue"):
            # Эти встроенные обрабатываются в exitLenCall/exitDequeueCall
            return

        # --- Попытка вызвать глобальную пользовательскую функцию ---
        func_info = self.flat_funcs.get(func_name)
        if func_info:
            for i, param in enumerate(func_info.parameters):
                if i < len(arg_ctx_list):
                    arg_expr_type = self.semantic_analyzer.get_expression_type(arg_ctx_list[i].expression())
                    if self.get_wat_type(param.type) == "f64":
                        self._ensure_f64_on_stack(arg_expr_type)
                    else:
                        if self.get_wat_type(arg_expr_type) == "f64":
                            self.current_wat_buffer.append('    (i32.trunc_f64_s)')
            self.current_wat_buffer.append(f'    (call ${func_name})')
            return

        # --- Попытка вызвать переменную‑лямбду (локальную/глобальную/параметр) ---
        var_info = self._lookup_var_info_in_flat_table(func_name, self.current_function_name)

        # Fallback: если не нашли по текущей функции/глобально, попробуем найти любой квалифицированный ключ вида "<scope>::func_name"
        if not var_info:
            for qualified, info in self.flat_vars.items():
                if qualified.endswith(f"::{func_name}"):
                    var_info = info
                    break

        if var_info and var_info.type == Type.LAMBDA:
            lambda_sig = var_info.lambda_signature

            # 1) Подготовка аргументов под ожидаемые типы (если есть сигнатура)
            if lambda_sig:
                for i, param in enumerate(lambda_sig.params):
                    if i < len(arg_ctx_list):
                        arg_expr_type = self.semantic_analyzer.get_expression_type(arg_ctx_list[i].expression())
                        if self.get_wat_type(param.type) == "f64":
                            self._ensure_f64_on_stack(arg_expr_type)
                        else:
                            if self.get_wat_type(arg_expr_type) == "f64":
                                self.current_wat_buffer.append('    (i32.trunc_f64_s)')
            else:
                # Нет сигнатуры — дефолт: приводим все аргументы к f64
                for a in arg_ctx_list:
                    arg_expr_type = self.semantic_analyzer.get_expression_type(a.expression())
                    self._ensure_f64_on_stack(arg_expr_type)

            # 2) Положить на стек индекс функции из самой переменной (local/global)
            access_op, idx_wat_type = self._resolve_variable_access(func_name)
            self.current_wat_buffer.append(f'    ({access_op})')
            if idx_wat_type == "f64":
                self.current_wat_buffer.append('    (i32.trunc_f64_s)')

            # 3) Тип для call_indirect — из сигнатуры; иначе дефолт: все параметры f64, результат f64
            if lambda_sig:
                param_types_wat = [self.get_wat_type(p.type) for p in lambda_sig.params]
                result_type_wat = self.get_wat_type(lambda_sig.return_type)
                type_key = hash(lambda_sig)
            else:
                param_types_wat = ["f64"] * len(arg_ctx_list)
                result_type_wat = "f64"
                type_key = 0

            func_type_name = f"$func_type_{type_key}"
            func_type_def = f'(type {func_type_name} (func {" ".join([f"(param {t})" for t in param_types_wat])}'
            if result_type_wat:
                func_type_def += f' (result {result_type_wat})'
            func_type_def += '))'
            self.unique_lambda_types_wat.add(func_type_def)

            # 4) Непрямой вызов по индексу
            self.current_wat_buffer.append(f'    (call_indirect (type {func_type_name}))')
            return

        # --- Если ни функция, ни лямбда ---
        raise Exception(f"Compiler Error: Unknown function or non-callable variable '{func_name}'.")

    def enterLambdaReturn(self, ctx: ListLangParser.LambdaReturnContext):
        self._enter_lambda_common(ctx)

    def exitLambdaReturn(self, ctx: ListLangParser.LambdaReturnContext):
        expr_type = self.semantic_analyzer.get_expression_type(ctx.expression())
        self._ensure_f64_on_stack(expr_type)
        self.current_wat_buffer.append('    (return)')
        self._exit_lambda_common(ctx)

    def enterLambdaBlock(self, ctx: ListLangParser.LambdaBlockContext):
        self._enter_lambda_common(ctx)

    def exitLambdaBlock(self, ctx: ListLangParser.LambdaBlockContext):
        current_lambda_sig = self.lambda_context_stack[-1]
        if current_lambda_sig and current_lambda_sig.return_type != Type.VOID:
            if current_lambda_sig.return_type in (Type.NUMBER, Type.BOOL):
                self.current_wat_buffer.append('    (f64.const 0.0)')
            else:
                self.current_wat_buffer.append('    (i32.const 0)')
        self.current_wat_buffer.append('    (return)')
        self._exit_lambda_common(ctx)

    def _enter_lambda_common(self, ctx: Any):
        self.lambda_function_id_counter += 1
        lambda_id = self.lambda_function_id_counter
        lambda_sig: Optional[LambdaSignature] = self.semantic_analyzer.lambda_signatures.get(ctx) or LambdaSignature([],
                                                                                                                     Type.VOID)
        lambda_sig.id = lambda_id

        self._previous_function_name = self.current_function_name
        self._previous_wat_buffer = self.current_wat_buffer

        self.lambda_context_stack.append(lambda_sig)
        self.current_function_name = f"lambda_{lambda_id}"
        self.current_wat_buffer = self.wat_lambdas

        params_wat = [f"(param ${p.name} {self.get_wat_type(p.type)})" for p in lambda_sig.params]

        self.function_all_locals[self.current_function_name] = {}
        locals_wat = []

        lambda_scope = None
        # Find the scope corresponding to this lambda to capture its locals
        # This is a bit tricky because scopes are popped. A robust way is to match by name if possible.
        # Let's assume the semantic analyzer assigns unique names or we rely on the stack order.
        # A better approach would be for the semantic analyzer to pass scope info to the listener.
        # For now, let's find the last lambda scope as a proxy.
        for scope in reversed(self.semantic_analyzer.symbol_table.scopes):
            if scope["type"].value == "lambda":
                lambda_scope = scope
                break

        if lambda_scope:
            for var_name, var_info in lambda_scope["variables"].items():
                if any(p.name == var_name for p in lambda_sig.params): continue
                wat_type = self.get_wat_type(var_info.type)
                locals_wat.append(f"(local ${var_name} {wat_type})")
                self.function_all_locals[self.current_function_name][var_name] = wat_type

        for i in range(self.GENERIC_I32_TEMPS):
            locals_wat.append(f"(local {self._get_generic_temp('i32', i)} i32)")
        for i in range(self.GENERIC_F64_TEMPS):
            locals_wat.append(f"(local {self._get_generic_temp('f64', i)} f64)")

        result_wat = f"(result {self.get_wat_type(lambda_sig.return_type)})" if lambda_sig.return_type != Type.VOID else ""

        self.current_wat_buffer.append(f'  (func $lambda_{lambda_id} {" ".join(params_wat)} {result_wat}')
        for local_decl in locals_wat:
            self.current_wat_buffer.append(f'    {local_decl}')

    def _exit_lambda_common(self, ctx: Any):
        current_lambda_sig = self.lambda_context_stack.pop()
        self.current_wat_buffer.append('  )')
        self.wat_lambdas.append(f'  (elem (global.get $next_table_idx) (ref.func $lambda_{current_lambda_sig.id}))')
        self.wat_lambdas.append('  (global.set $next_table_idx (i32.add (global.get $next_table_idx) (i32.const 1)))')

        self.current_function_name = self._previous_function_name
        self.current_wat_buffer = self._previous_wat_buffer

        self.current_wat_buffer.append(f'    (i32.const {current_lambda_sig.id})')
        self.current_wat_buffer.append('    (f64.convert_i32_u)')

    def enterStatementBlock(self, ctx: ListLangParser.StatementBlockContext):
        pass


def compile_listlang_to_wat(parse_tree, parser, semantic_analyzer, filename):
    compiler = WatCompiler(parser, semantic_analyzer)
    walker = ParseTreeWalker()
    walker.walk(compiler, parse_tree)
    return getattr(compiler, 'final_wat_code', '')
