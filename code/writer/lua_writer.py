from __future__ import annotations

import logging
import os

from table_parser.types import ExportTarget, FieldInfo, FieldType, TableSchema
from writer.base import IWriter

logger = logging.getLogger(__name__)


def _is_empty_cell(raw: str) -> bool:
    """判断单元格是否视为空（仅空白）。"""
    return raw.strip() == ""


def _escape_lua_string(s: str) -> str:
    """将字符串转为 Lua 双引号字面量内的转义形式。"""
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _is_lua_identifier(name: str) -> bool:
    """是否为合法 Lua 标识符（用于表字段等）。"""
    if not name:
        return False
    first, rest = name[0], name[1:]
    if not (first.isalpha() or first == "_"):
        return False
    return all(c.isalnum() or c == "_" for c in rest)


def _lua_table_field_lhs(name: str) -> str:
    """生成 Lua 表构造器中字段名的左侧写法（标识符或 [\"...\"]）。"""
    if _is_lua_identifier(name):
        return name
    return f'["{_escape_lua_string(name)}"]'


def _format_lua_bool(raw: str) -> str:
    """将单元格内容格式化为 Lua 布尔字面量。"""
    if _is_empty_cell(raw):
        return "false"
    v = raw.strip()
    if v == "1" or v.lower() == "true":
        return "true"
    return "false"


def _format_lua_scalar_number(raw: str, as_float: bool) -> str:
    """整数族或浮点数：空为 0，否则解析为数字字符串。"""
    if _is_empty_cell(raw):
        return "0"
    s = raw.strip()
    if as_float:
        return str(float(s))
    if s.startswith(("0x", "0X")):
        return str(int(s, 0))
    return str(int(s))


def _format_lua_string_value(raw: str) -> str:
    """string：双引号包裹并转义；空为 \"\""""
    if _is_empty_cell(raw):
        return '""'
    return f'"{_escape_lua_string(raw)}"'


def _format_lua_vector_value(raw: str) -> str:
    """vector2/vector3：整体作为 Lua 字符串字面量；空为 \"\""""
    if _is_empty_cell(raw):
        return '""'
    return f'"{_escape_lua_string(raw.strip())}"'


def _format_field_value(field: FieldInfo, raw: str) -> str:
    """按字段类型将单元格格式化为 Lua 表达式片段。"""
    ft = field.field_type
    if ft in (FieldType.INT, FieldType.INT64, FieldType.BYTE):
        return _format_lua_scalar_number(raw, as_float=False)
    if ft is FieldType.FLOAT:
        return _format_lua_scalar_number(raw, as_float=True)
    if ft is FieldType.BOOL:
        return _format_lua_bool(raw)
    if ft is FieldType.STRING:
        return _format_lua_string_value(raw)
    if ft in (FieldType.VECTOR2, FieldType.VECTOR3):
        return _format_lua_vector_value(raw)
    return _format_lua_string_value(raw)


def _format_primary_key_index_expr(key_field: FieldInfo, raw: str) -> str:
    """生成 data[...] 下标表达式：整型族为裸数字，字符串为带引号字面量。"""
    ft = key_field.field_type
    if ft in (FieldType.INT, FieldType.INT64, FieldType.BYTE):
        if _is_empty_cell(raw):
            return "0"
        s = raw.strip()
        return str(int(s, 0)) if s.startswith(("0x", "0X")) else str(int(s))
    if ft is FieldType.FLOAT:
        if _is_empty_cell(raw):
            return "0"
        return str(float(raw.strip()))
    if ft is FieldType.BOOL:
        return _format_lua_bool(raw)
    if ft in (FieldType.STRING, FieldType.VECTOR2, FieldType.VECTOR3):
        return _format_lua_string_value(raw)
    return _format_lua_string_value(raw)


class LuaWriter(IWriter):
    """将配置表导出为 Lua 表脚本：UTF-8 无 BOM、LF 换行，含 Key_* 列常量与 return data。"""

    def write(self, schema: TableSchema, output_dir: str, target: ExportTarget) -> None:
        """按导出目标过滤字段后写出 `{file_name}.lua`；无字段或无法在过滤列中定位主键时警告并跳过。"""
        fields, rows = self.filter_fields(schema, target)
        if not fields:
            logger.warning(
                "跳过 Lua 导出：过滤后无字段，file=%s target=%s",
                schema.file_name,
                target.value,
            )
            return

        key_field = schema.key_field
        if key_field is None:
            logger.warning(
                "跳过 Lua 导出：未定义主键，file=%s target=%s",
                schema.file_name,
                target.value,
            )
            return

        key_idx: int | None = None
        for i, f in enumerate(fields):
            if f.name == key_field.name:
                key_idx = i
                break
        if key_idx is None:
            logger.warning(
                "跳过 Lua 导出：主键列不在当前导出字段中，file=%s key=%s target=%s",
                schema.file_name,
                key_field.name,
                target.value,
            )
            return

        lines: list[str] = []
        lines.append("-- Auto Generated - DO NOT EDIT")
        lines.append(f"-- Source: {schema.file_name}.xlsx")
        lines.append("")
        lines.append("local data = {}")
        lines.append("")
        for i, f in enumerate(fields):
            lines.append(f"local Key_{f.name} = {i + 1}")
        lines.append("")

        for row in rows:
            key_raw = row[key_idx] if key_idx < len(row) else ""
            key_expr = _format_primary_key_index_expr(key_field, key_raw)
            parts: list[str] = []
            for col, f in enumerate(fields):
                cell = row[col] if col < len(row) else ""
                lhs = _lua_table_field_lhs(f.name)
                parts.append(f"{lhs} = {_format_field_value(f, cell)}")
            lines.append(f"data[{key_expr}] = {{ {', '.join(parts)} }}")

        lines.append("")
        lines.append("return data")

        text = "\n".join(lines) + "\n"
        out_path = self._get_output_path(output_dir, target, schema.file_name, "lua")
        with open(out_path, "w", encoding="utf-8", newline="\n") as fp:
            fp.write(text)

        logger.info("写出 Lua 文件: %s (%d 列, %d 行)", out_path, len(fields), len(rows))
