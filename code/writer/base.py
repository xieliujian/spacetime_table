from __future__ import annotations

import os
from abc import ABC, abstractmethod

from table_parser.types import ExportTarget, FieldInfo, TableSchema


class IWriter(ABC):
    """数据写出器抽象基类：将 TableSchema 导出为 bin / txt / lua 等格式。"""

    @abstractmethod
    def write(self, schema: TableSchema, output_dir: str, target: ExportTarget) -> None:
        """将表数据导出到指定目录。"""

    def _get_output_path(self, output_dir: str, target: ExportTarget, file_name: str, ext: str) -> str:
        """生成输出文件路径，格式：{output_dir}/{target}/{file_name}.{ext}"""
        target_dir = os.path.join(output_dir, target.value)
        os.makedirs(target_dir, exist_ok=True)
        return os.path.join(target_dir, f"{file_name}.{ext}")

    def filter_fields(
        self, schema: TableSchema, target: ExportTarget
    ) -> tuple[list[FieldInfo], list[list[str]]]:
        """按导出目标过滤字段，并同步裁剪每行数据中对应列；越界列视为空字符串。

        rows 中的元素顺序与 schema.fields 一一对应（而非按 Excel 列号索引），
        因此需要将 filtered_fields 映射回 schema.fields 中的位置。
        """
        filtered_fields = schema.get_fields_for_target(target)
        field_to_pos = {id(f): i for i, f in enumerate(schema.fields)}
        indices = [field_to_pos[id(f)] for f in filtered_fields]
        filtered_rows: list[list[str]] = []
        for row in schema.rows:
            filtered_rows.append([row[i] if i < len(row) else "" for i in indices])
        return filtered_fields, filtered_rows
