from __future__ import annotations

import logging
import os

from table_parser.types import TableSchema, ExportTarget, FieldInfo
from writer.base import IWriter

logger = logging.getLogger(__name__)

_UTF8_BOM = b"\xef\xbb\xbf"
_CRLF = b"\r\n"


class TxtWriter(IWriter):
    """将配置表导出为 TXT：UTF-8 BOM、Tab 分隔、CRLF 换行，表头三行（注释、类型、字段名）。"""

    def write(self, schema: TableSchema, output_dir: str, target: ExportTarget) -> None:
        """按导出目标过滤字段后写出 `{file_name}.txt`；无可用字段时仅记录警告并跳过。"""
        fields, rows = self.filter_fields(schema, target)
        if not fields:
            logger.warning(
                "跳过 TXT 导出：过滤后无字段，file=%s target=%s",
                schema.file_name,
                target.value,
            )
            return

        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"{schema.file_name}.txt")

        def _line(cells: list[str]) -> bytes:
            return "\t".join(cells).encode("utf-8") + _CRLF

        with open(out_path, "wb") as f:
            f.write(_UTF8_BOM)
            f.write(_line([f.comment for f in fields]))
            f.write(_line([f.field_type.value for f in fields]))
            f.write(_line([f.name for f in fields]))
            for row in rows:
                f.write(_line(row))
