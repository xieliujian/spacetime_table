# TableConv Python 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 Python 重写配表转换工具，支持 bin/txt/lua 数据导出和 C#/Go 代码生成。

**Architecture:** 模块化管道架构 — ExcelParser 将 xlsx 解析为 TableSchema 中间模型，Writer 和 CodeGenerator 各自从模型输出不同格式。模板使用 Python 内置字符串方案。

**Tech Stack:** Python 3.9+, openpyxl (xlsx 读取)

**Design Spec:** `docs/2026-03-27-tableconv-design.md`

**Target Directory:** `D:\xieliujian\spacetime_table\code\`

---

## 文件结构

Python 代码放在项目根目录，与现有 Go 代码（仅作参考）并存。

| 文件 | 职责 |
|------|------|
| `main.py` | CLI 入口，参数解析，调度 |
| `config.json` | 配置文件（已存在，需更新） |
| `requirements.txt` | Python 依赖 |
| `install.bat` | 一键安装依赖 |
| `parser/__init__.py` | 包导出 |
| `parser/types.py` | FieldType, BelongType, ExportTarget, FieldInfo, TableSchema |
| `parser/helper.py` | snake_case→PascalCase, camelCase, 文件名校验等 |
| `parser/excel_parser.py` | openpyxl 读取 xlsx → TableSchema |
| `writer/__init__.py` | 包导出 |
| `writer/base.py` | IWriter 抽象基类 |
| `writer/txt_writer.py` | UTF-8 BOM Tab 分隔文本 |
| `writer/bin_writer.py` | STBL 二进制格式 |
| `writer/lua_writer.py` | Lua table 格式 |
| `codegen/__init__.py` | 包导出 |
| `codegen/base.py` | ICodeGenerator 抽象基类 |
| `codegen/csharp_gen.py` | C# 代码生成（TD_{Class}.cs + TD_{Class}Table.cs） |
| `codegen/golang_gen.py` | Go 代码生成（{name}_table.go） |
| `templates/csharp/Data.tmpl` | C# 数据类模板（重写） |
| `templates/csharp/DataTable.tmpl` | C# 表管理类模板（重写） |
| `templates/golang/Table.tmpl` | Go 表文件模板（重写） |

---

## Task 1: 项目骨架与依赖

**Files:**
- Create: `requirements.txt`
- Create: `install.bat`
- Create: `parser/__init__.py`
- Create: `writer/__init__.py`
- Create: `codegen/__init__.py`

- [ ] **Step 1: 创建 `requirements.txt`**

```
openpyxl>=3.1.0
```

- [ ] **Step 2: 创建 `install.bat`**

```bat
@echo off
pip install -r requirements.txt
pause
```

- [ ] **Step 3: 创建包的 `__init__.py` 文件**

为 `parser/`、`writer/`、`codegen/` 各创建空的 `__init__.py`。

- [ ] **Step 4: 验证**

Run: `pip install -r requirements.txt`
Expected: openpyxl 安装成功

---

## Task 2: 数据模型与类型定义

**Files:**
- Create: `parser/types.py`

这是整个系统的基础数据模型，所有其他模块都依赖它。

- [ ] **Step 1: 实现枚举和数据类**

`parser/types.py` 需包含：

```python
from enum import Enum
from dataclasses import dataclass, field

class FieldType(Enum):
    """Excel 支持的字段类型"""
    INT = "int"
    INT64 = "int64"
    FLOAT = "float"
    BOOL = "bool"
    STRING = "string"
    BYTE = "byte"
    VECTOR2 = "vector2"
    VECTOR3 = "vector3"

class BelongType(Enum):
    """字段归属类型，控制导出方向"""
    ALL = "A"       # 客户端 + 服务器
    CLIENT = "C"    # 仅客户端
    SERVER = "S"    # 仅服务器
    KEY = "K"       # 主键（客户端 + 服务器都导出）
    NONE = "N"      # 忽略

class ExportTarget(Enum):
    """导出目标"""
    CLIENT = "client"
    SERVER = "server"
    ALL = "all"

@dataclass
class FieldInfo:
    """单个字段的元信息"""
    name: str
    field_type: FieldType
    belong: BelongType
    comment: str
    column_index: int

    def is_belong_client(self) -> bool:
        return self.belong in (BelongType.KEY, BelongType.CLIENT, BelongType.ALL)

    def is_belong_server(self) -> bool:
        return self.belong in (BelongType.KEY, BelongType.SERVER, BelongType.ALL)

    def is_belong_target(self, target: ExportTarget) -> bool:
        if target == ExportTarget.CLIENT:
            return self.is_belong_client()
        elif target == ExportTarget.SERVER:
            return self.is_belong_server()
        else:  # ALL
            return self.belong != BelongType.NONE

@dataclass
class TableSchema:
    """一张表的完整元信息 + 数据"""
    file_name: str
    class_name: str
    fields: list[FieldInfo] = field(default_factory=list)
    key_field: FieldInfo = None
    rows: list[list[str]] = field(default_factory=list)

    def get_fields_for_target(self, target: ExportTarget) -> list[FieldInfo]:
        return [f for f in self.fields if f.is_belong_target(target)]
```

- [ ] **Step 2: 验证**

Run: `python -c "from parser.types import *; print('OK')"`
Expected: OK

---

## Task 3: 命名转换工具函数

**Files:**
- Create: `parser/helper.py`

- [ ] **Step 1: 实现工具函数**

`parser/helper.py` 需包含：

```python
import re

def snake_to_pascal(name: str) -> str:
    """snake_case 转 PascalCase: skill_effect -> SkillEffect"""
    return ''.join(word.capitalize() for word in name.split('_'))

def snake_to_camel(name: str) -> str:
    """snake_case 转 camelCase: skill_effect -> skillEffect"""
    parts = name.split('_')
    return parts[0].lower() + ''.join(w.capitalize() for w in parts[1:])

def to_camel_case(name: str) -> str:
    """字段名转 camelCase（首字母小写）: Id -> id, HpMax -> hpMax"""
    if not name:
        return name
    return name[0].lower() + name[1:]

def to_private_field(name: str) -> str:
    """字段名转私有字段名: Id -> m_Id, Name -> m_Name"""
    return f"m_{name}"

def is_legal_file_name(name: str) -> bool:
    """检查文件名是否合法：小写字母+下划线，不能以下划线开头或结尾"""
    return bool(re.match(r'^[a-z][a-z_]*[a-z]$', name) or re.match(r'^[a-z]+$', name))

def format_class_name(file_name: str) -> str:
    """文件名转类名: skill_effect -> SkillEffect"""
    return snake_to_pascal(file_name)
```

- [ ] **Step 2: 验证**

Run: `python -c "from parser.helper import *; assert snake_to_pascal('skill_effect') == 'SkillEffect'; assert to_camel_case('Id') == 'id'; print('OK')"`
Expected: OK

---

## Task 4: Excel 解析器

**Files:**
- Create: `parser/excel_parser.py`

这是核心模块之一，将 xlsx 文件转为 TableSchema。

- [ ] **Step 1: 实现 ExcelParser 类**

`parser/excel_parser.py` 需包含：

- 常量定义：`COMMENT_ROW = 1, BELONG_ROW = 2, TYPE_ROW = 3, FIELD_NAME_ROW = 4, DATA_START_ROW = 5`
- `ExcelParser` 类：
  - `parse(file_path: str) -> TableSchema`：主入口
  - `_read_header(sheet) -> list[FieldInfo]`：读取前 4 行构建字段列表
  - `_find_key_field(fields) -> FieldInfo`：按优先级确定主键
  - `_read_data_rows(sheet, fields) -> list[list[str]]`：读取数据行
  - `_validate(schema: TableSchema)`：校验字段名重复、类型合法性等

关键逻辑：
- 遍历第一个 Sheet 的列，从第 1 列开始，遇到字段名为空的列停止
- BelongType 解析：空值视为 N
- FieldType 解析：不支持的类型抛出 ValueError
- 数据行读取：None 值转为空字符串
- 校验：字段名不重复（忽略 N 列）、主键必须存在

- [ ] **Step 2: 验证**

准备一个测试用 xlsx 文件，手动运行：
Run: `python -c "from parser.excel_parser import ExcelParser; p = ExcelParser(); print('OK')"`
Expected: OK

---

## Task 5: Writer 抽象基类

**Files:**
- Create: `writer/base.py`

- [ ] **Step 1: 实现 IWriter**

```python
from abc import ABC, abstractmethod
from parser.types import TableSchema, ExportTarget

class IWriter(ABC):
    """数据导出器抽象基类"""

    @abstractmethod
    def write(self, schema: TableSchema, output_dir: str, target: ExportTarget) -> None:
        """将表数据导出到指定目录"""
        pass

    def filter_fields(self, schema: TableSchema, target: ExportTarget):
        """获取目标平台的字段列表及对应数据列"""
        fields = schema.get_fields_for_target(target)
        col_indices = [f.column_index for f in fields]
        filtered_rows = []
        for row in schema.rows:
            filtered_rows.append([row[i] if i < len(row) else '' for i in col_indices])
        return fields, filtered_rows
```

- [ ] **Step 2: 验证**

Run: `python -c "from writer.base import IWriter; print('OK')"`
Expected: OK

---

## Task 6: TXT Writer

**Files:**
- Create: `writer/txt_writer.py`

- [ ] **Step 1: 实现 TxtWriter**

关键逻辑：
- 输出 UTF-8 BOM (`\xef\xbb\xbf`)
- Tab 分隔 (`\t`)
- CRLF 换行 (`\r\n`)
- 3 行表头：注释行、类型行、字段名行（不含归属行）
- 数据行逐行写入
- 输出文件名：`{schema.file_name}.txt`

- [ ] **Step 2: 验证**

手动检查输出的 .txt 文件格式正确。

---

## Task 7: Bin Writer

**Files:**
- Create: `writer/bin_writer.py`

STBL 二进制格式，设计文档 5.2 节详细定义。

- [ ] **Step 1: 实现 BinWriter**

关键逻辑：
- Header 32 字节：magic "STBL"，version 1，col_count，row_count，schema_offset，data_offset
- Schema 段：每列 type(1B) + name(2B长度+UTF8) + comment(2B长度+UTF8)
- Data 段：row_offsets 表(每行4B) + row_data
- 小端序（Little-Endian）
- varint 编码 int/int64
- float 4B LE，bool 1B，string 2B长度+UTF8，byte 1B
- vector2: 2×float32，vector3: 3×float32

需要实现的辅助函数：
- `_encode_varint(value: int) -> bytes`
- `_encode_string(value: str) -> bytes`
- `_encode_field(value: str, field_type: FieldType) -> bytes`
- `_write_header(buf, col_count, row_count, schema_offset, data_offset)`
- `_write_schema(buf, fields)`
- `_write_data(buf, fields, rows)`

- [ ] **Step 2: 验证**

用一个简单的表数据手动验证二进制输出的正确性（hex 检查 magic 头）。

---

## Task 8: Lua Writer

**Files:**
- Create: `writer/lua_writer.py`

- [ ] **Step 1: 实现 LuaWriter**

关键逻辑：
- 文件头注释：`-- Auto Generated - DO NOT EDIT`
- `local data = {}`
- Key 常量定义：`local Key_Id = 1` 等
- 数据行：`data[主键值] = { Id = 1001, Name = "xxx", ... }`
- bool → `true/false`
- string → 加双引号，转义 `\`、`"`、`\n`、`\r`、`\t`
- vector → 保持字符串形式 `"1.0,2.0"`
- 文件末尾 `return data`
- UTF-8 编码，LF 换行

- [ ] **Step 2: 验证**

手动检查输出的 .lua 文件可被 Lua 解释器加载。

---

## Task 9: CodeGen 抽象基类

**Files:**
- Create: `codegen/base.py`

- [ ] **Step 1: 实现 ICodeGenerator**

```python
from abc import ABC, abstractmethod
from parser.types import TableSchema

class ICodeGenerator(ABC):
    """代码生成器抽象基类"""

    @abstractmethod
    def generate(self, schema: TableSchema, output_dir: str, template_dir: str) -> None:
        """根据 TableSchema 生成代码文件"""
        pass

    def load_template(self, template_dir: str, name: str) -> str:
        """加载模板文件内容"""
        import os
        path = os.path.join(template_dir, name)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
```

- [ ] **Step 2: 验证**

Run: `python -c "from codegen.base import ICodeGenerator; print('OK')"`
Expected: OK

---

## Task 10: C# 模板 + 代码生成器

**Files:**
- Rewrite: `templates/csharp/Data.tmpl`
- Rewrite: `templates/csharp/DataTable.tmpl`
- Create: `codegen/csharp_gen.py`

- [ ] **Step 1: 编写 C# Data 模板 (`templates/csharp/Data.tmpl`)**

模板变量（用 `${var}` 语法）：
- `${CLASS_NAME}` — 类名（如 `Skill`）
- `${FIELDS_DECLARE}` — 私有字段声明块
- `${PROPERTIES_DECLARE}` — 公开属性声明块
- `${PARSE_BIN_BODY}` — ParseFromBin 方法体
- `${PARSE_TXT_BODY}` — ParseFromTxt 方法体

生成结果符合设计文档 6.2 节的格式：
- 命名空间 `ST.Table`
- 类名 `TD_${CLASS_NAME}`
- 私有字段 `m_` 前缀，省略 private
- 公开属性 camelCase，`public type name => m_Name;`
- `partial class`

- [ ] **Step 2: 编写 C# DataTable 模板 (`templates/csharp/DataTable.tmpl`)**

模板变量：
- `${CLASS_NAME}` — 类名
- `${KEY_TYPE}` — 主键 C# 类型
- `${KEY_NAME}` — 主键属性名（camelCase）
- `${PARSE_BIN_BODY}` — ParseFromBin 方法体
- `${PARSE_TXT_BODY}` — ParseFromTxt 方法体

- [ ] **Step 3: 实现 CSharpGenerator**

`codegen/csharp_gen.py` 需包含：

- C# 类型映射字典：`FieldType → str`（int→"int", int64→"long", float→"float" 等）
- Bin 读取方法映射：`FieldType → str`（int→"ReadInt()", string→"ReadString()" 等）
- Txt 解析方法映射：`FieldType → str`（int→"int.Parse(fields[i])", string→"fields[i]" 等）
- `CSharpGenerator.generate(schema, output_dir, template_dir)`：
  1. 过滤客户端字段
  2. 构建模板变量（字段声明、属性、解析方法体）
  3. 用 `string.Template` 替换模板变量
  4. 写出 `TD_{ClassName}.cs` 和 `TD_{ClassName}Table.cs`

- [ ] **Step 4: 验证**

手动运行生成一张表的 C# 代码，检查格式正确。

---

## Task 11: Go 模板 + 代码生成器

**Files:**
- Rewrite: `templates/golang/Table.tmpl`
- Create: `codegen/golang_gen.py`

- [ ] **Step 1: 编写 Go 模板 (`templates/golang/Table.tmpl`)**

模板变量：
- `${FILE_NAME}` — 源文件名
- `${STRUCT_NAME}` — 结构体名（PascalCase）
- `${FIELDS_DECLARE}` — 结构体字段声明
- `${PARSE_BIN_BODY}` — ParseFromBin 方法体
- `${PARSE_TXT_BODY}` — ParseFromTxt 方法体
- `${KEY_TYPE}` — 主键 Go 类型
- `${KEY_NAME}` — 主键字段名

生成结果符合设计文档 6.3 节的格式：
- `package table`
- 结构体 + Table 结构体 + GetById + ParseFromBin + ParseFromTxt

- [ ] **Step 2: 实现 GolangGenerator**

`codegen/golang_gen.py` 需包含：

- Go 类型映射字典：`FieldType → str`（int→"int32", int64→"int64", float→"float32" 等）
- Bin 读取方法映射：`FieldType → str`（int→"ReadInt32()", string→"ReadString()" 等）
- `GolangGenerator.generate(schema, output_dir, template_dir)`：
  1. 过滤服务器字段
  2. 构建模板变量
  3. 替换模板，写出 `{file_name}_table.go`

- [ ] **Step 3: 验证**

手动运行生成一张表的 Go 代码，检查格式正确。

---

## Task 12: 配置加载

**Files:**
- Create: `config.py`
- Update: `config.json`

- [ ] **Step 1: 实现 Config 类**

`config.py` 需包含：

```python
import json
from dataclasses import dataclass, field

@dataclass
class Config:
    need_more_sheet: list[str] = field(default_factory=list)
    ignore_output_code: list[str] = field(default_factory=list)
    need_lua_file: list[str] = field(default_factory=list)

    @staticmethod
    def load(path: str) -> 'Config':
        """加载配置，文件不存在时返回默认配置"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Config(
                need_more_sheet=data.get('need_more_sheet', []),
                ignore_output_code=data.get('ignore_output_code', []),
                need_lua_file=data.get('need_lua_file', []),
            )
        except FileNotFoundError:
            return Config()

    def should_generate_code(self, file_name: str) -> bool:
        return file_name not in self.ignore_output_code

    def should_generate_lua(self, file_name: str) -> bool:
        if not self.need_lua_file:
            return True
        return file_name in self.need_lua_file
```

- [ ] **Step 2: 更新 `config.json`**

```json
{
    "need_more_sheet": [],
    "ignore_output_code": [],
    "need_lua_file": []
}
```

- [ ] **Step 3: 验证**

Run: `python -c "from config import Config; c = Config.load('config.json'); print(c)"`
Expected: 输出默认配置

---

## Task 13: CLI 主入口

**Files:**
- Create: `main.py`

这是最终的集成模块，串联所有组件。

- [ ] **Step 1: 实现 CLI 参数解析**

使用 `argparse`，参数如设计文档 7.1 节：
- `-i`：输入路径（必填）
- `-o`：输出目录
- `-f`：格式 bin/txt/lua/code（必填）
- `-t`：目标 client/server/all（默认 client）
- `-c`：配置 JSON 路径（默认 config.json）
- `--csharp-out`：C# 输出目录
- `--go-out`：Go 输出目录
- `--tmpl`：模板目录（默认脚本同级 templates/）

- [ ] **Step 2: 实现主处理流程**

```python
def process_file(file_path, args, config):
    """处理单个 xlsx 文件"""
    parser = ExcelParser()
    schema = parser.parse(file_path)

    if args.format == 'code':
        if args.csharp_out:
            CSharpGenerator().generate(schema, args.csharp_out, tmpl_dir)
        if args.go_out:
            GolangGenerator().generate(schema, args.go_out, tmpl_dir)
    else:
        writer = get_writer(args.format)  # bin/txt/lua
        writer.write(schema, args.output, target)

def main():
    args = parse_args()
    config = Config.load(args.config)

    # 遍历输入目录或处理单个文件
    if os.path.isfile(args.input):
        process_file(args.input, args, config)
    else:
        for xlsx in glob.glob(os.path.join(args.input, '*.xlsx')):
            # 跳过临时文件 ~$
            # 跳过 ignore_output_code（code 模式）
            # 跳过非 need_lua_file（lua 模式）
            process_file(xlsx, args, config)
```

- [ ] **Step 3: 实现 Writer 工厂**

```python
def get_writer(format_name: str) -> IWriter:
    writers = {
        'bin': BinWriter,
        'txt': TxtWriter,
        'lua': LuaWriter,
    }
    return writers[format_name]()
```

- [ ] **Step 4: 端到端验证**

准备测试 xlsx，分别运行：

```bash
python main.py -i ./test.xlsx -o ./output -f txt -t client
python main.py -i ./test.xlsx -o ./output -f bin -t client
python main.py -i ./test.xlsx -o ./output -f lua -t client
python main.py -i ./test.xlsx -f code --csharp-out ./output/csharp --go-out ./output/golang
```

检查所有输出文件格式正确。

---

## Task 14: 清理与收尾

- [ ] **Step 1: 删除不再需要的 Go Extend 模板**

删除 `templates/csharp/DataExtend.tmpl` 和 `templates/csharp/DataTableExtend.tmpl`（设计决定不生成 Extend 文件）。

- [ ] **Step 2: 检查所有文件编码为 UTF-8**

- [ ] **Step 3: 最终端到端测试**

用真实 xlsx 文件完整运行所有格式，确认无报错。

---

## 执行顺序与依赖

```
Task 1 (骨架)
    ↓
Task 2 (类型) → Task 3 (helper)
    ↓
Task 4 (Excel 解析器)
    ↓
Task 5 (Writer 基类)
    ↓
Task 6 (TXT) ─── Task 7 (Bin) ─── Task 8 (Lua)   ← 可并行
    ↓
Task 9 (CodeGen 基类)
    ↓
Task 10 (C#) ─── Task 11 (Go)                       ← 可并行
    ↓
Task 12 (Config)
    ↓
Task 13 (CLI main)
    ↓
Task 14 (清理)
```

Task 6/7/8 三个 Writer 可并行开发；Task 10/11 两个 Generator 可并行开发。
