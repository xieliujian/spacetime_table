from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class Config:
    """表转换工具的运行时配置（多表合并、代码/Lua 导出规则）。"""

    need_more_sheet: list[str] = field(default_factory=list)
    """需要多 Sheet 合并导出的表名列表。"""

    ignore_output_code: list[str] = field(default_factory=list)
    """跳过代码生成的表名列表。"""

    need_lua_file: list[str] = field(default_factory=list)
    """仅导出 Lua 的表名白名单；为空表示全部导出。"""

    @staticmethod
    def load(path: str) -> Config:
        """从 JSON 文件加载配置；文件不存在时返回各列表均为空的默认配置。"""
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return Config()
        return Config(
            need_more_sheet=list(data.get("need_more_sheet", []) or []),
            ignore_output_code=list(data.get("ignore_output_code", []) or []),
            need_lua_file=list(data.get("need_lua_file", []) or []),
        )

    def should_generate_code(self, file_name: str) -> bool:
        """是否应为该表生成代码（不在忽略列表中则为 True）。"""
        return file_name not in self.ignore_output_code

    def should_generate_lua(self, file_name: str) -> bool:
        """是否应为该表生成 Lua：白名单为空则全部导出，否则仅白名单内为 True。"""
        if not self.need_lua_file:
            return True
        return file_name in self.need_lua_file

    def is_more_sheet(self, file_name: str) -> bool:
        """该表是否需要多 Sheet 合并处理。"""
        return file_name in self.need_more_sheet
