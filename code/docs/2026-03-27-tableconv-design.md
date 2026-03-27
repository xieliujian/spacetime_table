# TableConv 配表工具设计文档

> 日期：2026-03-27
> 状态：已审核

## 1. 项目概述

用 Python 实现的 Excel 配表转换工具，供 Unity 游戏客户端和 Go 服务器使用。

**核心功能**：
- 读取 Excel (xlsx) 配表文件
- 导出 3 种数据格式：bin（二进制）、txt（文本）、lua
- 生成 C# 代码（Unity 客户端，可读取 bin 和 txt）
- 生成 Go 代码（服务器，可读取 bin 和 txt）

**设计目标**：代码清晰整洁、注释清晰、扩展性强。

**输出目录**：`D:\xieliujian\spacetime_table\code\`

---

## 2. Excel 表格约定

### 2.1 表头结构（固定 4 行）

| 行号 | 含义 | 说明 |
|------|------|------|
| 1 | 注释（comment） | 策划可读的字段描述 |
| 2 | 归属（belong） | 控制字段导出方向 |
| 3 | 类型（type） | 字段数据类型 |
| 4 | 字段名（fieldName） | 代码中使用的标识符 |
| 5+ | 数据行 | 实际配置数据 |

### 2.2 归属码（Belong）

| 码 | 含义 | 客户端导出 | 服务器导出 |
|----|------|-----------|-----------|
| `K` | 主键 | 是 | 是 |
| `A` | 全部 | 是 | 是 |
| `C` | 仅客户端 | 是 | 否 |
| `S` | 仅服务器 | 否 | 是 |
| `N` | 忽略 | 否 | 否 |

### 2.3 支持的字段类型

| 类型 | 说明 | C# 映射 | Go 映射 |
|------|------|---------|---------|
| `int` | 32 位整数 | `int` | `int32` |
| `int64` | 64 位整数 | `long` | `int64` |
| `float` | 单精度浮点 | `float` | `float32` |
| `bool` | 布尔值 | `bool` | `bool` |
| `string` | 字符串 | `string` | `string` |
| `byte` | 字节 | `byte` | `byte` |
| `vector2` | 二维向量 | `Vector2` | `Vector2` |
| `vector3` | 三维向量 | `Vector3` | `Vector3` |

### 2.4 主键确定规则

优先级：`K` 归属列 > 名为 `Id` 的列 > 第一列

### 2.5 文件名约定

Excel 文件名必须为小写字母+下划线：`^[a-z][a-z_]*[a-z]$` 或 `^[a-z]+$`

---

## 3. 架构设计

### 3.1 模块化管道架构

```
xlsx 文件
    │
    ▼
ExcelParser  ──→  TableSchema（统一数据模型）
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
     BinWriter    TxtWriter    LuaWriter     ← 数据导出
          │            │            │
          ▼            ▼            ▼
      .bin 文件    .txt 文件    .lua 文件
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
    CSharpGenerator          GolangGenerator  ← 代码生成
          │                         │
          ▼                         ▼
    TD_*.cs 文件            *_table.go 文件
```

### 3.2 目录结构

```
D:\xieliujian\spacetime_table\code\
├── main.py                     # CLI 入口
├── config.json                 # 默认配置
├── requirements.txt            # 依赖：openpyxl
├── install.bat                 # pip install openpyxl
├── parser/
│   ├── __init__.py
│   ├── types.py                # FieldType, BelongType, FieldInfo, TableSchema
│   ├── excel_parser.py         # Excel → TableSchema
│   └── helper.py               # 命名转换工具函数
├── writer/
│   ├── __init__.py
│   ├── base.py                 # IWriter 抽象基类
│   ├── bin_writer.py           # STBL 二进制格式
│   ├── txt_writer.py           # Tab 分隔文本
│   └── lua_writer.py           # Lua table 格式
├── codegen/
│   ├── __init__.py
│   ├── base.py                 # ICodeGenerator 抽象基类
│   ├── csharp_gen.py           # C# 代码生成
│   └── golang_gen.py           # Go 代码生成
├── templates/
│   ├── csharp/
│   │   ├── Data.tmpl           # TD_{Class}.cs 模板
│   │   └── DataTable.tmpl      # TD_{Class}Table.cs 模板
│   └── golang/
│       └── Table.tmpl          # {name}_table.go 模板
└── docs/
    └── 2026-03-27-tableconv-design.md
```

### 3.3 依赖

| 依赖 | 用途 | 安装方式 |
|------|------|----------|
| openpyxl | 读取 xlsx 文件 | `pip install openpyxl` |

模板引擎使用 Python 内置 `string.Template` + f-string 实现，不引入 Jinja2。

---

## 4. 核心数据模型

### 4.1 类型定义（`parser/types.py`）

```python
class FieldType(Enum):
    INT = "int"
    INT64 = "int64"
    FLOAT = "float"
    BOOL = "bool"
    STRING = "string"
    BYTE = "byte"
    VECTOR2 = "vector2"
    VECTOR3 = "vector3"

class BelongType(Enum):
    ALL = "A"
    CLIENT = "C"
    SERVER = "S"
    KEY = "K"
    NONE = "N"

class ExportTarget(Enum):
    CLIENT = "client"
    SERVER = "server"
    ALL = "all"

class FieldInfo:
    name: str           # 字段名（原始）
    field_type: FieldType
    belong: BelongType
    comment: str
    column_index: int

class TableSchema:
    file_name: str              # 源文件名（不含扩展名）
    class_name: str             # PascalCase 类名
    fields: list[FieldInfo]     # 所有字段
    key_field: FieldInfo        # 主键字段
    rows: list[list[str]]       # 原始数据行（字符串）
```

### 4.2 字段过滤

| ExportTarget | 包含的归属码 |
|-------------|-------------|
| CLIENT | K + C + A |
| SERVER | K + S + A |
| ALL | K + C + S + A（所有非 N） |

过滤逻辑在 `FieldInfo` 或 `helper.py` 中提供 `is_belong_client()` / `is_belong_server()` 方法。

---

## 5. 数据导出格式

### 5.1 TXT 格式

- 编码：UTF-8 BOM
- 分隔符：Tab (`\t`)
- 换行符：CRLF
- 表头：3 行（注释 / 类型 / 字段名），不含归属行
- 数据：从第 4 行开始
- 文件扩展名：`.txt`

### 5.2 Bin 二进制格式（STBL）

```
文件布局：
┌──────────────────────────────┐
│ Header (固定 32 字节)         │
│   magic:        4B  "STBL"   │  SpaceTime TaBLe
│   version:      2B  uint16   │  当前版本 1
│   flags:        2B  uint16   │  预留，默认 0
│   col_count:    2B  uint16   │  列数
│   row_count:    4B  uint32   │  数据行数
│   schema_offset: 4B uint32   │  schema 段偏移
│   data_offset:   4B uint32   │  data 段偏移
│   reserved:     10B          │  预留
├──────────────────────────────┤
│ Schema 段                     │
│   per column:                │
│     type:    1B  uint8 枚举   │
│     name:    2B 长度 + UTF-8  │
│     comment: 2B 长度 + UTF-8  │
├──────────────────────────────┤
│ Data 段                       │
│   row_offsets: row_count × 4B │  每行偏移（支持随机访问）
│   row_data:                   │
│     int:     varint 编码      │
│     int64:   varint 编码      │
│     float:   4B little-endian │
│     bool:    1B (0/1)         │
│     string:  2B 长度 + UTF-8  │
│     byte:    1B               │
│     vector2: 8B  (2 × float32)│
│     vector3: 12B (3 × float32)│
└──────────────────────────────┘
```

关键设计点：
- **小端序**（Little-Endian）— 与 x86/ARM 一致
- **行偏移表** — 支持按索引随机访问
- **varint** — 小整数节省空间
- **version 字段** — 向后兼容

### 5.3 Lua 格式

```lua
-- Auto Generated - DO NOT EDIT
-- source: skill.xlsx

local data = {}

local Key_Id = 1
local Key_Name = 2
local Key_Hp = 3

data[1001] = { Id = 1001, Name = "warrior", Hp = 100.0 }
data[1002] = { Id = 1002, Name = "mage", Hp = 80.0 }

return data
```

- bool 输出为 `true/false`
- string 加引号并转义特殊字符
- vector 保持字符串形式 `"1.0,2.0"`
- 文件扩展名：`.lua`

---

## 6. 代码生成

### 6.1 C# 命名规范

| 项目 | 规范 | 示例 |
|------|------|------|
| 命名空间 | PascalCase | `ST.Table` |
| 类名 | `TD_` 前缀 + PascalCase | `TD_Skill`、`TD_SkillTable` |
| 私有字段 | 省略 private，`m_` 前缀 + PascalCase | `m_Id`、`m_Name` |
| 公开属性 | public + camelCase | `public int id => m_Id;` |
| 私有方法 | 省略 private，PascalCase | `void DoSomething()` |
| 公开方法 | public + PascalCase | `public void ParseFromBin(...)` |
| partial class | 是 | `public partial class TD_Skill` |

### 6.2 C# 生成文件

每张表生成 2 个文件：

**`TD_{ClassName}.cs`** — 数据行类：

```csharp
namespace ST.Table
{
    /// <summary> 自动生成，请勿手动修改 </summary>
    public partial class TD_Skill
    {
        int m_Id;
        string m_Name;
        float m_Hp;

        public int id => m_Id;
        public string name => m_Name;
        public float hp => m_Hp;

        /// <summary> 从二进制流读取 </summary>
        public void ParseFromBin(DataStreamReader reader)
        {
            m_Id = reader.ReadInt();
            m_Name = reader.ReadString();
            m_Hp = reader.ReadFloat();
        }

        /// <summary> 从文本行读取 </summary>
        public void ParseFromTxt(string[] fields)
        {
            m_Id = int.Parse(fields[0]);
            m_Name = fields[1];
            m_Hp = float.Parse(fields[2]);
        }
    }
}
```

**`TD_{ClassName}Table.cs`** — 表管理类：

```csharp
namespace ST.Table
{
    /// <summary> 自动生成，请勿手动修改 </summary>
    public partial class TD_SkillTable
    {
        Dictionary<int, TD_Skill> m_DataDict = new();
        List<TD_Skill> m_DataList = new();

        public Dictionary<int, TD_Skill> dataDict => m_DataDict;
        public List<TD_Skill> dataList => m_DataList;

        public TD_Skill GetById(int id)
        {
            m_DataDict.TryGetValue(id, out var data);
            return data;
        }

        public void ParseFromBin(DataStreamReader reader, int rowCount)
        {
            for (int i = 0; i < rowCount; i++)
            {
                var data = new TD_Skill();
                data.ParseFromBin(reader);
                m_DataList.Add(data);
                m_DataDict[data.id] = data;
            }
        }

        public void ParseFromTxt(string content)
        {
            // 按行分割，跳过 3 行表头，按 Tab 分割每行，逐行 ParseFromTxt
        }
    }
}
```

### 6.3 Go 生成文件

每张表生成 1 个文件：`{file_name}_table.go`

```go
package table

// Code generated by tableconv. DO NOT EDIT.
// source: skill.xlsx

type Skill struct {
    Id   int32
    Name string
    Hp   float32
}

type SkillTable struct {
    dataDict map[int32]*Skill
    dataList []*Skill
}

func (t *SkillTable) GetById(id int32) *Skill {
    return t.dataDict[id]
}

func (t *SkillTable) ParseFromBin(reader *DataStreamReader, rowCount int) {
    t.dataDict = make(map[int32]*Skill, rowCount)
    t.dataList = make([]*Skill, 0, rowCount)
    for i := 0; i < rowCount; i++ {
        data := &Skill{}
        data.Id = reader.ReadInt32()
        data.Name = reader.ReadString()
        data.Hp = reader.ReadFloat32()
        t.dataList = append(t.dataList, data)
        t.dataDict[data.Id] = data
    }
}

func (t *SkillTable) ParseFromTxt(content string) {
    // 按行分割，跳过 3 行表头，按 Tab 分割每行
}
```

Go 命名规范：
- 包名：`table`
- 导出字段：PascalCase
- 类型映射见 2.3 节
- 字段过滤：只导出 S/A/K 归属

### 6.4 模板实现

使用 Python 内置 `string.Template` + f-string，模板文件为 `.tmpl` 纯文本，变量用 `${var}` 标记，循环逻辑在 Python 代码中处理后拼接传入。

---

## 7. CLI 接口

### 7.1 命令行参数

```bash
python main.py -i <输入路径> -o <输出目录> -f <格式> [-t <目标>] [-c <配置>]
               [--csharp-out <C#目录>] [--go-out <Go目录>] [--tmpl <模板目录>]
```

| 参数 | 含义 | 默认值 | 必填 |
|------|------|--------|------|
| `-i` | 输入目录或单个 xlsx | - | 是 |
| `-o` | 数据输出目录 | - | 数据模式必填 |
| `-f` | 格式：`bin`/`txt`/`lua`/`code` | - | 是 |
| `-t` | 目标：`client`/`server`/`all` | `client` | 否 |
| `-c` | 配置 JSON 路径 | `config.json` | 否 |
| `--csharp-out` | C# 输出目录 | - | code 模式可选 |
| `--go-out` | Go 输出目录 | - | code 模式可选 |
| `--tmpl` | 模板目录 | 脚本同级 `templates/` | 否 |

### 7.2 使用示例

```bash
# 导出客户端二进制数据
python main.py -i ./xlsx -o ./output/bin -f bin -t client

# 导出服务器文本数据
python main.py -i ./xlsx -o ./output/txt -f txt -t server

# 导出客户端 Lua
python main.py -i ./xlsx -o ./output/lua -f lua -t client

# 生成 C# + Go 代码
python main.py -i ./xlsx -f code --csharp-out ./output/csharp --go-out ./output/golang
```

---

## 8. 配置文件（简洁版）

```json
{
    "need_more_sheet": [],
    "ignore_output_code": [],
    "need_lua_file": []
}
```

| 字段 | 含义 |
|------|------|
| `need_more_sheet` | 需要合并多 Sheet 的表名列表 |
| `ignore_output_code` | 跳过代码生成的表名列表 |
| `need_lua_file` | Lua 导出白名单（空=全部导出） |

所有字段为空数组时采用默认行为，后续按需扩展。

---

## 9. 验证与校验

解析阶段执行以下校验：
- 文件名格式合法性（小写+下划线）
- 归属码有效性（必须为 A/C/S/K/N）
- 类型有效性（必须为支持的类型之一）
- 字段名非空且不重复（忽略 N 列）
- 主键字段必须存在
- 数据行中检查类型兼容性（int 列不含非数字等）
