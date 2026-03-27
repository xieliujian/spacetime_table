from __future__ import annotations

import os
from abc import ABC, abstractmethod

from table_parser.types import TableSchema


class ICodeGenerator(ABC):
    """代码生成器抽象基类（如 C#、Go 等）。"""

    @abstractmethod
    def generate(self, schema: TableSchema, output_dir: str, template_dir: str) -> None:
        """根据 TableSchema 在输出目录生成代码文件。"""

    def load_template(self, template_dir: str, name: str) -> str:
        """加载模板文件并以 UTF-8 解码为字符串。"""
        path = os.path.join(template_dir, name)
        with open(path, encoding="utf-8") as f:
            return f.read()
