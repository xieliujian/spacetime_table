"""Go 代码生成器：根据 TableSchema 生成 Go 读表代码文件。"""

from __future__ import annotations

import os
import logging
from string import Template

from table_parser.types import TableSchema, FieldInfo, FieldType, ExportTarget
from table_parser.helper import format_class_name
from codegen.base import ICodeGenerator

logger = logging.getLogger(__name__)

# FieldType → Go 类型字符串
_GO_TYPE_MAP: dict[FieldType, str] = {
    FieldType.INT: "int32",
    FieldType.INT64: "int64",
    FieldType.FLOAT: "float32",
    FieldType.BOOL: "bool",
    FieldType.STRING: "string",
    FieldType.BYTE: "byte",
    FieldType.VECTOR2: "Vector2",
    FieldType.VECTOR3: "Vector3",
}

# FieldType → DataStreamReader 二进制读取方法名
_BIN_READ_MAP: dict[FieldType, str] = {
    FieldType.INT: "ReadInt32",
    FieldType.INT64: "ReadInt64",
    FieldType.FLOAT: "ReadFloat32",
    FieldType.BOOL: "ReadBool",
    FieldType.STRING: "ReadString",
    FieldType.BYTE: "ReadByte",
    FieldType.VECTOR2: "ReadVector2",
    FieldType.VECTOR3: "ReadVector3",
}

# 需要 strconv 包的类型集合
_NEEDS_STRCONV: set[FieldType] = {
    FieldType.INT, FieldType.INT64, FieldType.FLOAT, FieldType.BYTE,
}


class GolangGenerator(ICodeGenerator):
    """Go 代码生成器，为每张表生成 {file_name}_table.go 文件。

    生成的代码包含：数据行 struct、表管理器 struct、
    二进制读取 (ParseFromBin) 和文本读取 (ParseFromTxt) 方法。
    """

    def generate(self, schema: TableSchema, output_dir: str, template_dir: str) -> None:
        """根据 TableSchema 生成 Go 表代码文件。

        仅导出服务端字段（ExportTarget.SERVER），无服务端字段时跳过。
        """
        fields = schema.get_fields_for_target(ExportTarget.SERVER)
        if not fields:
            logger.warning("表 %s 无服务端字段，跳过 Go 代码生成", schema.file_name)
            return

        key_field = schema.key_field
        if key_field is None:
            logger.error("表 %s 无主键，跳过 Go 代码生成", schema.file_name)
            return

        struct_name = format_class_name(schema.file_name)
        key_type = self._get_go_type(key_field.field_type)
        key_name = key_field.name

        needs_strconv = any(f.field_type in _NEEDS_STRCONV for f in fields)

        variables = {
            "FILE_NAME": schema.file_name,
            "STRUCT_NAME": struct_name,
            "FIELDS_DECLARE": self._build_fields_declare(fields),
            "KEY_TYPE": key_type,
            "KEY_FIELD": key_name,
            "PARSE_BIN_BODY": self._build_parse_bin_body(fields),
            "PARSE_TXT_BODY": self._build_parse_txt_body(fields),
            "IMPORTS": self._build_imports(needs_strconv),
        }

        tmpl_text = self.load_template(template_dir, "golang/Table.tmpl")
        content = Template(tmpl_text).substitute(variables)

        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"{schema.file_name}_table.go")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("生成 Go 文件: %s", out_path)

    # ------------------------------------------------------------------
    # 内部构建方法
    # ------------------------------------------------------------------

    def _build_imports(self, needs_strconv: bool) -> str:
        """根据字段类型构建 Go import 语句。"""
        imports = ['"strings"']
        if needs_strconv:
            imports.append('"strconv"')
        if len(imports) == 1:
            return f"import {imports[0]}"
        lines = ["import ("]
        for imp in sorted(imports):
            lines.append(f"\t{imp}")
        lines.append(")")
        return "\n".join(lines)

    def _build_fields_declare(self, fields: list[FieldInfo]) -> str:
        """构建 Go struct 字段声明（PascalCase 字段名 + 类型 + 注释）。"""
        lines: list[str] = []
        for f in fields:
            go_type = self._get_go_type(f.field_type)
            comment = f.comment or f.name
            lines.append(f"\t{f.name} {go_type} // {comment}")
        return "\n".join(lines)

    def _build_parse_bin_body(self, fields: list[FieldInfo]) -> str:
        """构建 ParseFromBin 方法体中的逐字段读取语句。"""
        lines: list[str] = []
        for f in fields:
            lines.append(f"\t\t{self._get_bin_read(f.field_type, f.name)}")
        return "\n".join(lines)

    def _build_parse_txt_body(self, fields: list[FieldInfo]) -> str:
        """构建 ParseFromTxt 方法体中的逐字段解析语句。"""
        lines: list[str] = []
        for idx, f in enumerate(fields):
            for stmt in self._get_txt_parse(f.field_type, f.name, idx):
                lines.append(f"\t\t{stmt}")
        return "\n".join(lines)

    def _get_go_type(self, field_type: FieldType) -> str:
        """FieldType 转换为对应的 Go 类型字符串。"""
        return _GO_TYPE_MAP.get(field_type, "interface{}")

    def _get_bin_read(self, field_type: FieldType, field_name: str) -> str:
        """生成单个字段的二进制读取语句（如 data.Id = reader.ReadInt32()）。"""
        method = _BIN_READ_MAP.get(field_type, "ReadInt32")
        return f"data.{field_name} = reader.{method}()"

    def _get_txt_parse(self, field_type: FieldType, field_name: str, index: int) -> list[str]:
        """生成单个字段的文本解析语句，可能包含多行（需要类型转换时）。

        返回的每一行不含前导缩进，由调用方统一添加。
        """
        if field_type is FieldType.INT:
            v = f"v{index}"
            return [
                f"{v}, _ := strconv.ParseInt(fields[{index}], 10, 32)",
                f"data.{field_name} = int32({v})",
            ]
        if field_type is FieldType.INT64:
            return [
                f"data.{field_name}, _ = strconv.ParseInt(fields[{index}], 10, 64)",
            ]
        if field_type is FieldType.FLOAT:
            v = f"v{index}"
            return [
                f"{v}, _ := strconv.ParseFloat(fields[{index}], 32)",
                f"data.{field_name} = float32({v})",
            ]
        if field_type is FieldType.BOOL:
            return [
                f'data.{field_name} = fields[{index}] == "1" || fields[{index}] == "true"',
            ]
        if field_type is FieldType.STRING:
            return [
                f"data.{field_name} = fields[{index}]",
            ]
        if field_type is FieldType.BYTE:
            v = f"v{index}"
            return [
                f"{v}, _ := strconv.ParseInt(fields[{index}], 10, 8)",
                f"data.{field_name} = byte({v})",
            ]
        if field_type is FieldType.VECTOR2:
            return [
                f"data.{field_name} = ParseVector2(fields[{index}])",
            ]
        if field_type is FieldType.VECTOR3:
            return [
                f"data.{field_name} = ParseVector3(fields[{index}])",
            ]
        return [f"data.{field_name} = fields[{index}]"]
