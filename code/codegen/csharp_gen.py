"""C# 代码生成器：根据 TableSchema 生成 Unity C# 读表代码。

每张表生成两个文件：
  - TD_{ClassName}.cs     数据行类（字段声明、二进制/文本解析）
  - TD_{ClassName}Table.cs 表管理器（字典索引、批量加载）
"""

from __future__ import annotations

import logging
import os
from string import Template

from table_parser.types import TableSchema, FieldInfo, FieldType, ExportTarget
from table_parser.helper import to_camel_case, to_private_field, format_class_name
from codegen.base import ICodeGenerator

# ---------- C# 类型映射表 ----------

_CS_TYPE_MAP: dict[FieldType, str] = {
    FieldType.INT: "int",
    FieldType.INT64: "long",
    FieldType.FLOAT: "float",
    FieldType.BOOL: "bool",
    FieldType.STRING: "string",
    FieldType.BYTE: "byte",
    FieldType.VECTOR2: "Vector2",
    FieldType.VECTOR3: "Vector3",
}

_CS_DEFAULT_MAP: dict[FieldType, str] = {
    FieldType.INT: "0",
    FieldType.INT64: "0L",
    FieldType.FLOAT: "0f",
    FieldType.BOOL: "false",
    FieldType.STRING: "string.Empty",
    FieldType.BYTE: "0",
    FieldType.VECTOR2: "Vector2.zero",
    FieldType.VECTOR3: "Vector3.zero",
}

_CS_BIN_READ_MAP: dict[FieldType, str] = {
    FieldType.INT: "reader.ReadInt()",
    FieldType.INT64: "reader.ReadInt64()",
    FieldType.FLOAT: "reader.ReadFloat()",
    FieldType.BOOL: "reader.ReadBool()",
    FieldType.STRING: "reader.ReadString()",
    FieldType.BYTE: "reader.ReadByte()",
    FieldType.VECTOR2: "reader.ReadVector2()",
    FieldType.VECTOR3: "reader.ReadVector3()",
}

# 文本解析表达式模板，{i} 由调用方填充为列序号
_CS_TXT_PARSE_MAP: dict[FieldType, str] = {
    FieldType.INT: "int.Parse(fields[{i}])",
    FieldType.INT64: "long.Parse(fields[{i}])",
    FieldType.FLOAT: "float.Parse(fields[{i}])",
    FieldType.BOOL: 'fields[{i}] == "1" || fields[{i}].ToLower() == "true"',
    FieldType.STRING: "fields[{i}]",
    FieldType.BYTE: "byte.Parse(fields[{i}])",
    FieldType.VECTOR2: "ParseVector2(fields[{i}])",
    FieldType.VECTOR3: "ParseVector3(fields[{i}])",
}


class CSharpGenerator(ICodeGenerator):
    """C# 代码生成器，使用 string.Template 将字段信息填入 .tmpl 模板。"""

    def generate(self, schema: TableSchema, output_dir: str, template_dir: str) -> None:
        """生成 TD_{ClassName}.cs 与 TD_{ClassName}Table.cs。"""
        client_fields = schema.get_fields_for_target(ExportTarget.CLIENT)
        if not client_fields:
            return

        class_name = schema.class_name
        key_field = schema.key_field
        key_cs_type = self._get_cs_type(key_field.field_type) if key_field else "int"
        key_prop = to_camel_case(key_field.name) if key_field else "id"

        variables = {
            "FILE_NAME": schema.file_name,
            "CLASS_NAME": class_name,
            "KEY_TYPE": key_cs_type,
            "KEY_PROP": key_prop,
            "FIELDS_DECLARE": self._build_fields_declare(client_fields),
            "PROPERTIES_DECLARE": self._build_properties_declare(client_fields),
            "PARSE_BIN_BODY": self._build_parse_bin_body(client_fields),
            "PARSE_TXT_BODY": self._build_parse_txt_body(client_fields),
        }

        os.makedirs(output_dir, exist_ok=True)

        data_tmpl = self.load_template(template_dir, "csharp/Data.tmpl")
        table_tmpl = self.load_template(template_dir, "csharp/DataTable.tmpl")

        data_code = Template(data_tmpl).substitute(variables)
        table_code = Template(table_tmpl).substitute(variables)

        data_path = os.path.join(output_dir, f"TD_{class_name}.cs")
        table_path = os.path.join(output_dir, f"TD_{class_name}Table.cs")

        self._write_file(data_path, data_code)
        self._write_file(table_path, table_code)

    # ---------- 代码块构建 ----------

    def _build_fields_declare(self, fields: list[FieldInfo]) -> str:
        """构建私有字段声明块（8 空格缩进，省略 private 关键字）。"""
        lines: list[str] = []
        for f in fields:
            cs_type = self._get_cs_type(f.field_type)
            priv_name = to_private_field(f.name)
            default = self._get_default_value(f.field_type)
            lines.append(f"        {cs_type} {priv_name} = {default};")
        return "\n".join(lines)

    def _build_properties_declare(self, fields: list[FieldInfo]) -> str:
        """构建公开属性声明块（8 空格缩进，含 xml 注释）。"""
        lines: list[str] = []
        for f in fields:
            cs_type = self._get_cs_type(f.field_type)
            prop_name = to_camel_case(f.name)
            priv_name = to_private_field(f.name)
            comment = f.comment or f.name
            lines.append(f"        /// <summary>{comment}</summary>")
            lines.append(f"        public {cs_type} {prop_name} => {priv_name};")
        return "\n".join(lines)

    def _build_parse_bin_body(self, fields: list[FieldInfo]) -> str:
        """构建二进制解析方法体（12 空格缩进）。"""
        lines: list[str] = []
        for f in fields:
            priv_name = to_private_field(f.name)
            read_expr = self._get_bin_read(f.field_type)
            lines.append(f"            {priv_name} = {read_expr};")
        return "\n".join(lines)

    def _build_parse_txt_body(self, fields: list[FieldInfo]) -> str:
        """构建文本解析方法体（12 空格缩进，按序号索引 fields 数组）。"""
        lines: list[str] = []
        for idx, f in enumerate(fields):
            priv_name = to_private_field(f.name)
            parse_expr = self._get_txt_parse(f.field_type, idx)
            lines.append(f"            {priv_name} = {parse_expr};")
        return "\n".join(lines)

    # ---------- 类型映射查询 ----------

    @staticmethod
    def _get_cs_type(field_type: FieldType) -> str:
        """FieldType → C# 类型字符串。"""
        return _CS_TYPE_MAP.get(field_type, "object")

    @staticmethod
    def _get_default_value(field_type: FieldType) -> str:
        """FieldType → C# 默认值字符串。"""
        return _CS_DEFAULT_MAP.get(field_type, "default")

    @staticmethod
    def _get_bin_read(field_type: FieldType) -> str:
        """FieldType → 二进制读取表达式。"""
        return _CS_BIN_READ_MAP.get(field_type, "reader.ReadInt()")

    @staticmethod
    def _get_txt_parse(field_type: FieldType, index: int) -> str:
        """FieldType → 文本解析表达式（填入列序号）。"""
        pattern = _CS_TXT_PARSE_MAP.get(field_type, "fields[{i}]")
        return pattern.format(i=index)

    # ---------- 文件写出 ----------

    @staticmethod
    def _write_file(path: str, content: str) -> None:
        """以 UTF-8 编码写出文件。"""
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)


def generate_runtime(runtime_out: str, template_dir: str) -> None:
    """将运行时支持库输出到 runtime_out 目录，仅在文件不存在时生成。

    生成文件：DataStreamReader.cs / StblReader.cs / TableLoader.cs
    模板路径：{template_dir}/csharp/runtime/{Name}.tmpl
    """
    _runtime_logger = logging.getLogger(__name__)
    _RUNTIME_FILES = ["DataStreamReader", "StblReader", "TableLoader"]

    os.makedirs(runtime_out, exist_ok=True)

    for name in _RUNTIME_FILES:
        dest_path = os.path.join(runtime_out, f"{name}.cs")
        if os.path.exists(dest_path):
            _runtime_logger.info("[Runtime] 跳过（已存在）: %s", dest_path)
            continue

        tmpl_path = os.path.join(template_dir, "csharp", "runtime", f"{name}.tmpl")
        with open(tmpl_path, encoding="utf-8") as f:
            content = f.read()

        with open(dest_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

        _runtime_logger.info("[Runtime] 生成: %s", dest_path)
