# Unity 运行时读表支持库设计文档

**日期**: 2026-03-27  
**项目**: spacetime_table — Python 配表转换工具  
**范围**: Unity C# 运行时支持库 + 表格 Load 接口  

---

## 背景

当前工具已能生成 `TD_SkillTable.cs` / `TD_Skill.cs` 等 C# 文件，但：

1. 生成代码依赖 `DataStreamReader`，该类在 Unity 项目中不存在，导致编译报错。
2. 每张表只有 `ParseFromBin(reader, rowCount)` / `ParseFromTxt(content)` 低层方法，调用方需自行处理文件 IO 和 STBL 格式解析。
3. 需要统一的 `Load(string _dir, bool _useBin = true)` 入口，使上层只需一行代码即可加载整张表。

---

## 目标

1. 为 Unity 工程提供完整的运行时支持库（3 个 C# 文件），导入后立即编译通过。
2. 每张生成的 `TD_XxxTable.cs` 新增 `Load(string _dir, bool _useBin = true)` 方法。
3. Python 工具新增 `--runtime-out` 参数，控制运行时库输出位置，仅在目标文件不存在时生成（不覆盖用户改动）。

---

## 架构

### 方案：StblReader 独立封装（方案 C）

```
bytes[]
  └─► StblReader          — 解析 STBL 文件头，定位到行数据
          ├─ RowCount       — 从 header 读取
          └─ Reader         — DataStreamReader，已跳过 header + schema + 偏移表

DataStreamReader            — 纯二进制读取，varint/zigzag，所有字段类型
TableLoader                 — 静态文件 IO 工具，LoadBytes / LoadText
```

职责边界：

| 类 | 职责 | 依赖 |
|----|------|------|
| `DataStreamReader` | byte[] 位置游标 + 类型读取 | UnityEngine（Vector2 / Vector3） |
| `StblReader` | STBL 格式解析，持有 Reader | DataStreamReader，System.IO |
| `TableLoader` | 文件 IO，路径拼接，错误处理 | System.IO |

---

## 运行时文件详细设计

> 三个运行时文件均使用命名空间 `ST.Table`，与生成的表格代码一致，无需额外 `using`。

### DataStreamReader.cs

```
命名空间 : ST.Table
using    : UnityEngine（Vector2 / Vector3）
```

**内部状态**
- `byte[] m_Buffer` — 数据字节数组
- `int m_Pos` — 当前读取位置

**公开 API**

| 方法 | 说明 |
|------|------|
| `DataStreamReader(byte[] data, int startPos = 0)` | 构造，初始化缓冲区和起始位置 |
| `int ReadInt()` | 读取 zigzag varint → int32 |
| `long ReadInt64()` | 读取 zigzag varint → int64 |
| `float ReadFloat()` | 读取 4 字节 LE float32 |
| `bool ReadBool()` | 读取 1 字节，非 0 为 true |
| `string ReadString()` | 读取 2 字节 LE 长度 + UTF-8 字节 |
| `byte ReadByte()` | 读取 1 字节 |
| `Vector2 ReadVector2()` | 读取 2 × float32 |
| `Vector3 ReadVector3()` | 读取 3 × float32 |

**私有辅助**

- `ReadRawByte()` — 读 1 字节，推进 pos
- `ReadUInt16LE()` — 读 2 字节 LE uint16
- `ReadUInt32LE()` — 读 4 字节 LE uint32
- `ReadVarint()` — unsigned varint 解码
- `ZigzagDecode32(uint)` / `ZigzagDecode64(ulong)` — zigzag 还原

---

### StblReader.cs

```
命名空间 : ST.Table
using    : System（BitConverter）、System.IO（InvalidDataException）
```

**STBL 文件头布局（32 字节，小端序）**

| 偏移 | 大小 | 字段 |
|------|------|------|
| 0 | 4 | magic = "STBL" |
| 4 | 2 | version |
| 6 | 2 | flags |
| 8 | 2 | fieldCount |
| 10 | 4 | rowCount |
| 14 | 4 | schemaOffset |
| 18 | 4 | dataOffset |
| 22 | 10 | reserved |

**构造逻辑**

header 的原始读取使用 `System.BitConverter`（在 DataStreamReader 创建之前执行）：

1. 校验 `data[0..3]` 的 ASCII 等于 `"STBL"`，不符则抛 `InvalidDataException`
2. `rowCount  = (int)BitConverter.ToUInt32(data, 10)`
3. `dataOffset = (int)BitConverter.ToUInt32(data, 18)`
4. `pos = dataOffset`（无需解析 schema 段）
5. `pos += rowCount × 4`（跳过行偏移表）
6. `Reader = new DataStreamReader(data, pos)`

**公开 API**

| 成员 | 说明 |
|------|------|
| `StblReader(byte[] data)` | 构造，解析 header |
| `int RowCount` | 数据行数 |
| `DataStreamReader Reader` | 定位至行数据的读取器 |

---

### TableLoader.cs

```
命名空间 : ST.Table
using    : System.IO（File、FileNotFoundException）
```

**公开 API**

| 方法 | 说明 |
|------|------|
| `static byte[] LoadBytes(string path)` | 读取文件字节，文件不存在抛含路径信息的 `FileNotFoundException` |
| `static string LoadText(string path)` | 读取 UTF-8（含 BOM）文本文件 |

---

## TD_XxxTable.cs 新增 Load 方法

在现有 `DataTable.tmpl` 中追加：

```csharp
public void Load(string _dir, bool _useBin = true)
{
    Clear();
    if (_useBin)
    {
        byte[] bytes = TableLoader.LoadBytes(System.IO.Path.Combine(_dir, "${FILE_NAME}.bin"));
        var stbl = new StblReader(bytes);
        ParseFromBin(stbl.Reader, stbl.RowCount);
    }
    else
    {
        string content = TableLoader.LoadText(System.IO.Path.Combine(_dir, "${FILE_NAME}.txt"));
        ParseFromTxt(content);
    }
}
```

**说明**：

- `${FILE_NAME}` — Python 模板变量，替换为 Excel 文件名（不含扩展名，蛇形命名），如 `skill`、`item`、`skill_effect`。与现有模板中 `${FILE_NAME}` 用法一致。
- `TableLoader` / `StblReader` 与生成的表格代码同属 `namespace ST.Table`，**无需额外 `using` 指令**，直接可用。

---

## Python 工具改动

### 新增 CLI 参数

`main.py` 新增可选参数（在 `code` 模式下生效，也可单独使用）：

```
--runtime-out <目录>
```

典型用法：

```bash
# 同时生成表格代码 + 运行时库
python main.py -i ./test_data -f code \
    --csharp-out ./output/csharp \
    --runtime-out ./output/runtime

# 只生成运行时库（不指定 --csharp-out 时跳过表格代码生成）
python main.py -f code --runtime-out ./output/runtime
```

`--runtime-out` 可单独使用，无需同时指定 `--csharp-out`。

### 新增运行时生成逻辑

`codegen/csharp_gen.py` 新增 `generate_runtime(runtime_out, template_dir)` 函数：

- 遍历 3 个运行时模板文件（`DataStreamReader.tmpl`、`StblReader.tmpl`、`TableLoader.tmpl`）
- 对每个目标文件：若 `runtime_out/<name>.cs` **不存在**，则从模板复制生成
- 若文件已存在，跳过并输出 INFO 日志（保护用户改动）
- **已知限制**：若模板有 bug 修复，需手动删除目标文件后重新生成（或日后视需求添加 `--force-runtime` 标志覆盖）

### 模板文件位置

```
templates/csharp/runtime/
├── DataStreamReader.tmpl
├── StblReader.tmpl
└── TableLoader.tmpl
```

这 3 个模板为纯静态内容（无变量替换），直接复制即可。

---

## 文件结构变更

```
code/
├── codegen/
│   └── csharp_gen.py          ← 新增 generate_runtime()
├── templates/csharp/
│   ├── Data.tmpl               （无变化）
│   ├── DataTable.tmpl          ← 追加 Load() 方法
│   └── runtime/               ← 新增目录
│       ├── DataStreamReader.tmpl
│       ├── StblReader.tmpl
│       └── TableLoader.tmpl
└── main.py                     ← 新增 --runtime-out 参数
```

生成输出示例（`--runtime-out ./output/runtime`）：

```
output/runtime/
├── DataStreamReader.cs   （仅首次生成）
├── StblReader.cs         （仅首次生成）
└── TableLoader.cs        （仅首次生成）
```

---

## 错误处理

| 情况 | 处理方式 |
|------|---------|
| STBL magic 不符 | `StblReader` 构造时抛 `InvalidDataException` |
| 文件不存在 | `TableLoader.LoadBytes/LoadText` 抛含路径的 `FileNotFoundException` |
| 运行时文件已存在 | Python 工具跳过，输出 INFO 日志 |

---

## 命名约定（与现有规范一致）

- 命名空间：`ST.Table`
- 私有字段：无 `private` 关键字，`m_` 前缀 + PascalCase
- 公开属性：camelCase
- 方法：PascalCase，无 `private` 关键字

---

## 不在范围内

- Go 服务端运行时库（本次只做 C# 端）
- Unity StreamingAssets / Resources 路径封装（`TableLoader` 仅做文件系统 IO，路径由调用方构造）
- 加密/压缩支持
