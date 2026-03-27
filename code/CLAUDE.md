# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Python 配表转换工具，将 Excel (xlsx) 配表文件转换为多种输出格式，供 Unity 客户端和 Go 服务端使用。

## Architecture

```
main.py                 CLI 入口，参数解析与调度
config.py               JSON 配置加载
table_parser/
  types.py              核心数据模型：FieldType, BelongType, ExportTarget, FieldInfo, TableSchema
  helper.py             命名转换：snake_to_pascal, to_camel_case, to_private_field
  excel_parser.py       openpyxl 读取 xlsx → TableSchema
writer/
  base.py               IWriter 抽象基类（filter_fields 按目标过滤字段）
  bin_writer.py          STBL 二进制格式（小端序，varint，行随机访问）
  txt_writer.py          UTF-8 BOM Tab 分隔文本
  lua_writer.py          Lua table 格式
codegen/
  base.py               ICodeGenerator 抽象基类
  csharp_gen.py          C# 代码生成（string.Template）
  golang_gen.py          Go 代码生成（string.Template）
templates/
  csharp/Data.tmpl       TD_{Class}.cs 模板
  csharp/DataTable.tmpl  TD_{Class}Table.cs 模板
  golang/Table.tmpl      {name}_table.go 模板
```

## Common Commands

```bash
# 安装依赖
pip install -r requirements.txt

# 导出客户端二进制数据
python main.py -i <xlsx目录> -o <输出目录> -f bin -t client

# 导出客户端文本数据
python main.py -i <xlsx目录> -o <输出目录> -f txt -t client

# 导出服务器文本数据
python main.py -i <xlsx目录> -o <输出目录> -f txt -t server

# 导出客户端 Lua
python main.py -i <xlsx目录> -o <输出目录> -f lua -t client

# 生成 C# + Go 代码
python main.py -i <xlsx目录> -f code --csharp-out <C#目录> --go-out <Go目录>

# 指定配置文件
python main.py -i <xlsx目录> -o <输出目录> -f bin -t client -c config.json

# 详细日志
python main.py -i <xlsx目录> -o <输出目录> -f txt -t client -v
```

## Excel Table Format

4 行表头，第 5 行起为数据：

| 行 | 含义 | 示例 |
|----|------|------|
| 1 | 注释 | 技能ID, 技能名称 |
| 2 | 归属 | K, A, C, S, N |
| 3 | 类型 | int, string, float, bool, vector2 |
| 4 | 字段名 | Id, Name, Damage |

归属码：`K`=主键, `A`=全平台, `C`=仅客户端, `S`=仅服务器, `N`=忽略

支持类型：`int`, `int64`, `float`, `bool`, `string`, `byte`, `vector2`, `vector3`

## C# Naming Conventions

- 命名空间：`ST.Table`
- 类名前缀：`TD_` + PascalCase（`TD_Skill`, `TD_SkillTable`）
- 私有字段：省略 `private`，`m_` 前缀（`m_Id`, `m_Name`）
- 公开属性：camelCase（`public int id => m_Id;`）
- 私有方法：省略 `private`
- 所有类使用 `partial class`

## Configuration (config.json)

```json
{
    "need_more_sheet": [],
    "ignore_output_code": [],
    "need_lua_file": []
}
```

## Dependencies

- Python 3.9+
- openpyxl (xlsx 读取)
- 模板引擎使用 Python 内置 string.Template

## Binary Format (STBL)

32 字节头：magic "STBL" + version + col/row counts + schema/data offsets。
小端序，int 用 varint+zigzag 编码，行偏移表支持随机访问。
