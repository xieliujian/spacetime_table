# spacetime_table

游戏配表转换工具 — 将 Excel (xlsx) 配表文件转换为多种数据格式和代码，供 Unity 客户端与 Go 服务端使用。

## 功能

- **数据导出** — bin（二进制）、txt（文本）、lua 三种格式
- **代码生成** — Unity C# 读表代码、Go 服务端读表代码
- **字段过滤** — 按归属码自动区分客户端/服务端字段
- **扩展性强** — 模块化管道架构，新增格式只需实现一个 Writer 或 Generator

## 快速开始

### 环境要求

- Python 3.9+

### 安装

```bash
cd code
pip install -r requirements.txt
```

或直接运行：

```bash
cd code
install.bat
```

### 基本用法

```bash
cd code

# 导出客户端二进制数据
python main.py -i <xlsx目录> -o <输出目录> -f bin -t client

# 导出客户端文本数据
python main.py -i <xlsx目录> -o <输出目录> -f txt -t client

# 导出客户端 Lua 数据
python main.py -i <xlsx目录> -o <输出目录> -f lua -t client

# 导出服务器文本数据
python main.py -i <xlsx目录> -o <输出目录> -f txt -t server

# 生成 C# 代码
python main.py -i <xlsx目录> -f code --csharp-out <C#输出目录>

# 生成 Go 代码
python main.py -i <xlsx目录> -f code --go-out <Go输出目录>

# 同时生成 C# + Go 代码
python main.py -i <xlsx目录> -f code --csharp-out <C#目录> --go-out <Go目录>
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-i, --input` | 输入目录或单个 xlsx 文件 | 必填 |
| `-o, --output` | 数据输出目录 | 数据模式必填 |
| `-f, --format` | 输出格式：`bin` / `txt` / `lua` / `code` | 必填 |
| `-t, --target` | 导出目标：`client` / `server` / `all` | `client` |
| `-c, --config` | 配置 JSON 路径 | `config.json` |
| `--csharp-out` | C# 代码输出目录 | code 模式可选 |
| `--go-out` | Go 代码输出目录 | code 模式可选 |
| `--tmpl` | 模板目录 | 脚本同级 `templates/` |
| `-v, --verbose` | 输出详细日志 | 关闭 |

## Excel 表格规范

每张表的前 4 行为表头，第 5 行起为数据：

| 行 | 含义 | 说明 |
|----|------|------|
| 1 | 注释 | 策划可读的字段描述 |
| 2 | 归属 | 控制字段导出到哪个平台 |
| 3 | 类型 | 字段数据类型 |
| 4 | 字段名 | 代码中使用的标识符 |

### 示例

| 技能ID | 技能名称 | 伤害值 | 冷却时间 | 服务器标记 |
|--------|---------|--------|---------|-----------|
| K | A | C | A | S |
| int | string | float | float | int |
| Id | Name | Damage | Cooldown | ServerFlag |
| 1001 | fireball | 120.5 | 3.0 | 10 |
| 1002 | ice_arrow | 80.0 | 2.5 | 20 |

### 归属码

| 码 | 含义 | 客户端导出 | 服务器导出 |
|----|------|-----------|-----------|
| `K` | 主键 | ✅ | ✅ |
| `A` | 全平台 | ✅ | ✅ |
| `C` | 仅客户端 | ✅ | ❌ |
| `S` | 仅服务器 | ❌ | ✅ |
| `N` | 忽略 | ❌ | ❌ |

### 支持的字段类型

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

### 文件名规范

Excel 文件名须为小写字母 + 下划线，且不能以下划线开头或结尾：

```
skill.xlsx        ✅
skill_effect.xlsx ✅
Skill.xlsx        ❌ (大写)
_skill.xlsx       ❌ (下划线开头)
```

## 输出格式

### TXT（文本）

- 编码：UTF-8 BOM
- 分隔符：Tab
- 表头 3 行（注释 / 类型 / 字段名）+ 数据行

### Bin（二进制 STBL）

自定义二进制格式，特点：
- 魔数 `STBL`，小端序
- varint 编码整数，节省空间
- 行偏移表支持按索引随机访问

### Lua

```lua
local data = {}

data[1001] = { Id = 1001, Name = "fireball", Damage = 120.5 }
data[1002] = { Id = 1002, Name = "ice_arrow", Damage = 80.0 }

return data
```

### C# 代码

每张表生成 2 个文件，命名空间 `ST.Table`：

- `TD_{ClassName}.cs` — 数据行类（字段、属性、`ParseFromBin`、`ParseFromTxt`）
- `TD_{ClassName}Table.cs` — 表管理器（字典索引、批量加载、`GetById`）

### Go 代码

每张表生成 1 个文件，包名 `table`：

- `{file_name}_table.go` — 数据结构 + 表管理器（`ParseFromBin`、`ParseFromTxt`、`GetById`）

## 配置文件

`config.json` 控制导出行为：

```json
{
    "need_more_sheet": [],
    "ignore_output_code": [],
    "need_lua_file": []
}
```

| 字段 | 说明 |
|------|------|
| `need_more_sheet` | 需要合并多 Sheet 的表名列表 |
| `ignore_output_code` | 跳过代码生成的表名列表 |
| `need_lua_file` | Lua 导出白名单（空 = 全部导出） |

## 文件部署

生成完成后，使用 `deploy.py` 将输出文件复制（或移动）到项目目标目录：

```bash
cd code

# 复制模式（默认），将所有输出部署到目标目录
python deploy.py

# 移动模式（源文件删除）
python deploy.py --move

# 只执行指定规则
python deploy.py --only "客户端C#代码"

# 查看所有部署规则
python deploy.py --list

# 使用自定义配置
python deploy.py -c my_deploy.json

# 详细日志
python deploy.py -v
```

### 部署配置

`deploy_config.json` 定义部署规则：

```json
{
    "deploy": [
        { "name": "客户端C#代码",   "src": "./output/csharp",      "dest": "../../project/Assets/Script/Table",     "pattern": "*.cs"  },
        { "name": "客户端Lua数据",  "src": "./output/lua",         "dest": "../../project/Assets/Script/Lua/table", "pattern": "*.lua" },
        { "name": "客户端Bin数据",  "src": "./output/bin",         "dest": "../../project/BuildRes/config",          "pattern": "*.bin" },
        { "name": "客户端Txt数据",  "src": "./output/txt",         "dest": "../../project/BuildRes/config",          "pattern": "*.txt" },
        { "name": "服务器Go代码",   "src": "./output/golang",      "dest": "../../server/table",                     "pattern": "*.go"  },
        { "name": "服务器Bin数据",  "src": "./output/server_bin",  "dest": "../../server/config",                    "pattern": "*.bin" },
        { "name": "服务器Txt数据",  "src": "./output/server_txt",  "dest": "../../server/config",                    "pattern": "*.txt" }
    ]
}
```

| 字段 | 说明 |
|------|------|
| `name` | 规则名称（用于日志和 `--only` 过滤） |
| `src` | 源目录（支持相对路径，相对于配置文件） |
| `dest` | 目标目录（支持相对路径，不存在时自动创建） |
| `pattern` | 文件匹配模式（glob 语法） |

### deploy.py 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-c, --config` | 部署配置 JSON 路径 | `deploy_config.json` |
| `--move` | 移动模式（源文件删除） | 关闭（复制模式） |
| `--only` | 只执行名称包含该字符串的规则 | 全部执行 |
| `--list` | 列出所有规则，不执行 | — |
| `-v, --verbose` | 输出详细日志 | 关闭 |

## 项目结构

```
code/
├── main.py                  # CLI 入口
├── deploy.py                # 文件部署工具
├── debug_run.py             # 调试入口（预配置参数）
├── config.py                # 配置加载
├── config.json              # 默认配置
├── deploy_config.json       # 部署配置
├── requirements.txt         # Python 依赖
├── table_parser/
│   ├── types.py             # 核心数据模型
│   ├── helper.py            # 命名转换工具
│   └── excel_parser.py      # Excel 解析器
├── writer/
│   ├── base.py              # Writer 抽象基类
│   ├── bin_writer.py        # 二进制导出 (STBL)
│   ├── txt_writer.py        # 文本导出
│   └── lua_writer.py        # Lua 导出
├── codegen/
│   ├── base.py              # CodeGen 抽象基类
│   ├── csharp_gen.py        # C# 代码生成
│   └── golang_gen.py        # Go 代码生成
└── templates/
    ├── csharp/
    │   ├── Data.tmpl         # 数据行类模板
    │   └── DataTable.tmpl    # 表管理器模板
    └── golang/
        └── Table.tmpl        # Go 表文件模板
```

## 扩展指南

### 添加新的数据格式

1. 在 `writer/` 下新建文件，继承 `IWriter`
2. 实现 `write(schema, output_dir, target)` 方法
3. 在 `main.py` 的 `_WRITER_MAP` 中注册

### 添加新的代码语言

1. 在 `codegen/` 下新建文件，继承 `ICodeGenerator`
2. 在 `templates/` 下新建模板目录
3. 实现 `generate(schema, output_dir, template_dir)` 方法
4. 在 `main.py` 中添加对应的命令行参数和调用逻辑

### 添加新的字段类型

1. 在 `table_parser/types.py` 的 `FieldType` 枚举中添加
2. 在各 Writer 和 Generator 的类型映射字典中补充对应转换规则

## License

MIT
