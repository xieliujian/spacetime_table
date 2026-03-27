from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FieldType(Enum):
    """字段在表中的逻辑类型，用于代码生成与校验。"""

    INT = "int"
    INT64 = "int64"
    FLOAT = "float"
    BOOL = "bool"
    STRING = "string"
    BYTE = "byte"
    VECTOR2 = "vector2"
    VECTOR3 = "vector3"


class BelongType(Enum):
    """字段归属：决定导出到客户端、服务端或仅作键等。"""

    ALL = "A"
    CLIENT = "C"
    SERVER = "S"
    KEY = "K"
    NONE = "N"


class ExportTarget(Enum):
    """导出目标：按客户端、服务端或全量导出过滤字段。"""

    CLIENT = "client"
    SERVER = "server"
    ALL = "all"


@dataclass
class FieldInfo:
    """单列表头字段的元信息（名称、类型、归属、注释与列序）。"""

    name: str
    field_type: FieldType
    belong: BelongType
    comment: str
    column_index: int

    def is_belong_client(self) -> bool:
        """是否导出到客户端（键列、客户端列或双端列）。"""
        return self.belong in (BelongType.KEY, BelongType.CLIENT, BelongType.ALL)

    def is_belong_server(self) -> bool:
        """是否导出到服务端（键列、服务端列或双端列）。"""
        return self.belong in (BelongType.KEY, BelongType.SERVER, BelongType.ALL)

    def is_belong_target(self, target: ExportTarget) -> bool:
        """当前字段是否应包含在指定导出目标中。"""
        if target is ExportTarget.CLIENT:
            return self.is_belong_client()
        if target is ExportTarget.SERVER:
            return self.is_belong_server()
        return self.belong is not BelongType.NONE


@dataclass
class TableSchema:
    """整张配置表的解析结果：类名、字段定义、主键与行数据。"""

    file_name: str
    class_name: str
    fields: list[FieldInfo]
    key_field: FieldInfo | None
    rows: list[list[str]]

    def get_fields_for_target(self, target: ExportTarget) -> list[FieldInfo]:
        """按导出目标过滤后返回应输出的字段列表（顺序与 fields 一致）。"""
        return [f for f in self.fields if f.is_belong_target(target)]
