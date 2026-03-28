from __future__ import annotations

import os
import struct
import logging

from table_parser.types import TableSchema, ExportTarget, FieldInfo, FieldType
from writer.base import IWriter

logger = logging.getLogger(__name__)

_HEADER_SIZE = 32
_MAGIC = b"STBL"
_VERSION = 1
_FLAGS = 0

_FIELD_TYPE_INDEX: dict[FieldType, int] = {
    FieldType.INT: 0,
    FieldType.INT64: 1,
    FieldType.FLOAT: 2,
    FieldType.BOOL: 3,
    FieldType.STRING: 4,
    FieldType.BYTE: 5,
    FieldType.VECTOR2: 6,
    FieldType.VECTOR3: 7,
}


class BinWriter(IWriter):
    """STBL 二进制格式写出器，将 TableSchema 编码为紧凑的二进制文件。"""

    def write(self, schema: TableSchema, output_dir: str, target: ExportTarget) -> None:
        """将表数据导出为 .bin 文件到指定目录。"""
        fields, rows = self.filter_fields(schema, target)

        schema_segment = self._build_schema(fields)
        data_segment = self._build_data(fields, rows)

        schema_offset = _HEADER_SIZE
        data_offset = schema_offset + len(schema_segment)

        header = struct.pack(
            "<4sHHHI II 10s",
            _MAGIC,
            _VERSION,
            _FLAGS,
            len(fields),
            len(rows),
            schema_offset,
            data_offset,
            b"\x00" * 10,
        )

        out_path = self._get_output_path(output_dir, target, schema.file_name, "bin")

        with open(out_path, "wb") as fp:
            fp.write(header)
            fp.write(schema_segment)
            fp.write(data_segment)

        logger.info("写出二进制文件: %s (%d 列, %d 行)", out_path, len(fields), len(rows))

    # ------------------------------------------------------------------
    # Schema 段
    # ------------------------------------------------------------------

    def _build_schema(self, fields: list[FieldInfo]) -> bytes:
        """构建 schema 段：每列依次写入 type(1B) + name(2B+UTF8) + comment(2B+UTF8)。"""
        buf = bytearray()
        for f in fields:
            buf.append(_FIELD_TYPE_INDEX[f.field_type])
            buf.extend(self._encode_string(f.name))
            buf.extend(self._encode_string(f.comment))
        return bytes(buf)

    # ------------------------------------------------------------------
    # Data 段
    # ------------------------------------------------------------------

    def _build_data(self, fields: list[FieldInfo], rows: list[list[str]]) -> bytes:
        """构建 data 段：先编码所有行数据并记录偏移，再在前部拼接偏移表。"""
        row_blobs: list[bytes] = []
        for row in rows:
            row_buf = bytearray()
            for idx, f in enumerate(fields):
                raw = row[idx] if idx < len(row) else ""
                row_buf.extend(self._encode_field(raw, f.field_type))
            row_blobs.append(bytes(row_buf))

        offset_table_size = len(rows) * 4
        current_offset = offset_table_size
        offsets = bytearray()
        for blob in row_blobs:
            offsets.extend(struct.pack("<I", current_offset))
            current_offset += len(blob)

        return bytes(offsets) + b"".join(row_blobs)

    # ------------------------------------------------------------------
    # 字段编码
    # ------------------------------------------------------------------

    def _encode_field(self, value: str, field_type: FieldType) -> bytes:
        """将原始字符串值按字段类型编码为二进制字节。"""
        v = value.strip()

        if field_type is FieldType.INT:
            n = int(v) if v else 0
            return self._encode_varint(self._zigzag_encode_32(n))

        if field_type is FieldType.INT64:
            n = int(v) if v else 0
            return self._encode_varint(self._zigzag_encode_64(n))

        if field_type is FieldType.FLOAT:
            return struct.pack("<f", float(v) if v else 0.0)

        if field_type is FieldType.BOOL:
            return b"\x01" if v.lower() in ("1", "true") else b"\x00"

        if field_type is FieldType.STRING:
            return self._encode_string(v)

        if field_type is FieldType.BYTE:
            return struct.pack("B", int(v) & 0xFF if v else 0)

        if field_type is FieldType.VECTOR2:
            return self._encode_vector(v, 2)

        if field_type is FieldType.VECTOR3:
            return self._encode_vector(v, 3)

        raise ValueError(f"不支持的字段类型: {field_type}")

    def _encode_vector(self, value: str, dim: int) -> bytes:
        """解析 "x,y" 或 "x,y,z" 格式并编码为 float32 序列。"""
        parts = value.split(",") if value else []
        components: list[float] = []
        for i in range(dim):
            try:
                components.append(float(parts[i].strip()) if i < len(parts) else 0.0)
            except (ValueError, IndexError):
                components.append(0.0)
        return struct.pack(f"<{dim}f", *components)

    # ------------------------------------------------------------------
    # 字符串编码
    # ------------------------------------------------------------------

    @staticmethod
    def _encode_string(value: str) -> bytes:
        """编码字符串：2 字节 uint16 LE 长度前缀 + UTF-8 字节。"""
        raw = value.encode("utf-8")
        return struct.pack("<H", len(raw)) + raw

    # ------------------------------------------------------------------
    # Varint / Zigzag
    # ------------------------------------------------------------------

    @staticmethod
    def _encode_varint(value: int) -> bytes:
        """将无符号整数编码为 unsigned varint（每字节低 7 位数据，最高位为延续标志）。"""
        buf = bytearray()
        while value > 0x7F:
            buf.append((value & 0x7F) | 0x80)
            value >>= 7
        buf.append(value & 0x7F)
        return bytes(buf)

    @staticmethod
    def _zigzag_encode_32(n: int) -> int:
        """32 位有符号整数的 zigzag 编码，将负数映射到正数空间。"""
        n &= 0xFFFFFFFF
        return (n << 1) ^ (n >> 31)

    @staticmethod
    def _zigzag_encode_64(n: int) -> int:
        """64 位有符号整数的 zigzag 编码，将负数映射到正数空间。"""
        n &= 0xFFFFFFFFFFFFFFFF
        return (n << 1) ^ (n >> 63)
