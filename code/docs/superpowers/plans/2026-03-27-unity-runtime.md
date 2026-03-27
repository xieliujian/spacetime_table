# Unity 运行时读表支持库 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Unity 工程生成 DataStreamReader / StblReader / TableLoader 三个运行时支持库文件，并在每张表的 `TD_XxxTable.cs` 中添加 `Load(string _dir, bool _useBin = true)` 方法，使上层一行代码完成整张表的加载。

**Architecture:** 运行时库分三个职责明确的 C# 类（DataStreamReader 负责字节读取、StblReader 负责 STBL 格式解析、TableLoader 负责文件 IO）；Python 工具通过静态模板文件生成这三个类，仅在目标文件不存在时写出（保护用户改动）；`DataTable.tmpl` 追加 Load 方法完成对上层的统一封装。

**Tech Stack:** Python 3.9+, C# (Unity), string.Template, openpyxl

---

## 文件变更清单

| 操作 | 路径 | 说明 |
|------|------|------|
| 新建 | `templates/csharp/runtime/DataStreamReader.tmpl` | 字节流读取器模板 |
| 新建 | `templates/csharp/runtime/StblReader.tmpl` | STBL 格式解析模板 |
| 新建 | `templates/csharp/runtime/TableLoader.tmpl` | 文件 IO 工具模板 |
| 修改 | `templates/csharp/DataTable.tmpl` | 追加 Load() 方法 |
| 修改 | `codegen/csharp_gen.py` | 新增 generate_runtime() 函数 |
| 修改 | `main.py` | 新增 --runtime-out 参数和调用逻辑 |
| 修改 | `debug_run.py` | 新增 runtime 测试场景 |

---

## Task 1: DataStreamReader.tmpl

**Files:**
- Create: `templates/csharp/runtime/DataStreamReader.tmpl`

- [ ] **Step 1: 创建 runtime 模板目录**

```bash
mkdir templates/csharp/runtime
```

- [ ] **Step 2: 写入 DataStreamReader.tmpl**

文件内容（无模板变量，纯静态 C#）：

```csharp
// Auto Generated - DO NOT EDIT
using System.Text;
using UnityEngine;

namespace ST.Table
{
    /// <summary>
    /// 二进制字节流读取器，支持 varint / zigzag 编码及所有配表字段类型。
    /// </summary>
    public class DataStreamReader
    {
        byte[] m_Buffer;
        int m_Pos;

        public DataStreamReader(byte[] data, int startPos = 0)
        {
            m_Buffer = data;
            m_Pos = startPos;
        }

        /// <summary> 读取 zigzag varint → int32 </summary>
        public int ReadInt()
        {
            uint n = (uint)ReadVarint();
            return ZigzagDecode32(n);
        }

        /// <summary> 读取 zigzag varint → int64 </summary>
        public long ReadInt64()
        {
            ulong n = ReadVarint();
            return ZigzagDecode64(n);
        }

        /// <summary> 读取 4 字节小端序 float32 </summary>
        public float ReadFloat()
        {
            float v = System.BitConverter.ToSingle(m_Buffer, m_Pos);
            m_Pos += 4;
            return v;
        }

        /// <summary> 读取 1 字节，非 0 为 true </summary>
        public bool ReadBool()
        {
            return ReadRawByte() != 0;
        }

        /// <summary> 读取 2 字节 LE 长度前缀 + UTF-8 字符串 </summary>
        public string ReadString()
        {
            ushort len = ReadUInt16LE();
            if (len == 0) return string.Empty;
            string s = Encoding.UTF8.GetString(m_Buffer, m_Pos, len);
            m_Pos += len;
            return s;
        }

        /// <summary> 读取 1 字节 </summary>
        public byte ReadByte()
        {
            return ReadRawByte();
        }

        /// <summary> 读取 2 × float32 → Vector2 </summary>
        public Vector2 ReadVector2()
        {
            float x = ReadFloat();
            float y = ReadFloat();
            return new Vector2(x, y);
        }

        /// <summary> 读取 3 × float32 → Vector3 </summary>
        public Vector3 ReadVector3()
        {
            float x = ReadFloat();
            float y = ReadFloat();
            float z = ReadFloat();
            return new Vector3(x, y, z);
        }

        // ---- 私有辅助 ----

        byte ReadRawByte()
        {
            return m_Buffer[m_Pos++];
        }

        ushort ReadUInt16LE()
        {
            ushort v = (ushort)(m_Buffer[m_Pos] | (m_Buffer[m_Pos + 1] << 8));
            m_Pos += 2;
            return v;
        }

        uint ReadUInt32LE()
        {
            uint v = (uint)(m_Buffer[m_Pos]
                         | (m_Buffer[m_Pos + 1] << 8)
                         | (m_Buffer[m_Pos + 2] << 16)
                         | (m_Buffer[m_Pos + 3] << 24));
            m_Pos += 4;
            return v;
        }

        ulong ReadVarint()
        {
            ulong result = 0;
            int shift = 0;
            byte b;
            do
            {
                b = ReadRawByte();
                result |= (ulong)(b & 0x7F) << shift;
                shift += 7;
            } while ((b & 0x80) != 0);
            return result;
        }

        static int ZigzagDecode32(uint n)
        {
            return (int)((n >> 1) ^ (uint)(-(int)(n & 1)));
        }

        static long ZigzagDecode64(ulong n)
        {
            return (long)((n >> 1) ^ (ulong)(-(long)(n & 1)));
        }
    }
}
```

---

## Task 2: StblReader.tmpl

**Files:**
- Create: `templates/csharp/runtime/StblReader.tmpl`

- [ ] **Step 1: 写入 StblReader.tmpl**

```csharp
// Auto Generated - DO NOT EDIT
using System;
using System.IO;

namespace ST.Table
{
    /// <summary>
    /// STBL 二进制表文件解析器。
    /// 校验文件头 magic，解析行数和数据偏移，提供定位到行数据的 DataStreamReader。
    /// </summary>
    public class StblReader
    {
        /// <summary> 数据行数（由文件头读取）</summary>
        public int RowCount { get; }

        /// <summary> 已定位到行数据起点的读取器 </summary>
        public DataStreamReader Reader { get; }

        /// <summary>
        /// 解析 STBL 文件字节。
        /// 文件头布局（32 字节小端序）：magic[4] version[2] flags[2] fieldCount[2]
        /// rowCount[4@10] schemaOffset[4@14] dataOffset[4@18] reserved[10]
        /// </summary>
        public StblReader(byte[] data)
        {
            if (data == null || data.Length < 32)
                throw new InvalidDataException("STBL 数据不足 32 字节");

            if (data[0] != (byte)'S' || data[1] != (byte)'T' ||
                data[2] != (byte)'B' || data[3] != (byte)'L')
            {
                throw new InvalidDataException(
                    $"STBL magic 校验失败: 0x{data[0]:X2}{data[1]:X2}{data[2]:X2}{data[3]:X2}");
            }

            RowCount    = (int)BitConverter.ToUInt32(data, 10);
            int dataOffset = (int)BitConverter.ToUInt32(data, 18);

            // 跳过行偏移表（rowCount × 4 字节）后即为行数据起点
            int rowDataStart = dataOffset + RowCount * 4;
            Reader = new DataStreamReader(data, rowDataStart);
        }
    }
}
```

---

## Task 3: TableLoader.tmpl

**Files:**
- Create: `templates/csharp/runtime/TableLoader.tmpl`

- [ ] **Step 1: 写入 TableLoader.tmpl**

```csharp
// Auto Generated - DO NOT EDIT
using System.IO;

namespace ST.Table
{
    /// <summary>
    /// 表格文件加载工具，提供文件字节和文本的读取接口。
    /// </summary>
    public static class TableLoader
    {
        /// <summary>
        /// 读取文件全部字节。文件不存在时抛出含路径信息的异常。
        /// </summary>
        public static byte[] LoadBytes(string path)
        {
            if (!File.Exists(path))
                throw new FileNotFoundException($"表格文件不存在: {path}", path);
            return File.ReadAllBytes(path);
        }

        /// <summary>
        /// 读取 UTF-8（含 BOM）文本文件。文件不存在时抛出含路径信息的异常。
        /// </summary>
        public static string LoadText(string path)
        {
            if (!File.Exists(path))
                throw new FileNotFoundException($"表格文件不存在: {path}", path);
            return File.ReadAllText(path);
        }
    }
}
```

---

## Task 4: 更新 DataTable.tmpl — 追加 Load() 方法

**Files:**
- Modify: `templates/csharp/DataTable.tmpl`

- [ ] **Step 1: 在 `Clear()` 方法之后、类的 `}` 之前追加 Load() 方法**

在现有 `Clear()` 方法块结束后追加：

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

`${FILE_NAME}` 是 Python 模板变量，生成时替换为 Excel 文件名（如 `skill`、`item`）。

---

## Task 5: codegen/csharp_gen.py — 新增 generate_runtime()

**Files:**
- Modify: `codegen/csharp_gen.py`

- [ ] **Step 1: 在文件末尾新增模块级函数 `generate_runtime()`**

```python
def generate_runtime(runtime_out: str, template_dir: str) -> None:
    """将运行时支持库输出到 runtime_out 目录，仅在文件不存在时生成。

    生成文件：DataStreamReader.cs / StblReader.cs / TableLoader.cs
    """
    _runtime_logger = logging.getLogger(__name__)
    _RUNTIME_FILES = ["DataStreamReader", "StblReader", "TableLoader"]

    os.makedirs(runtime_out, exist_ok=True)

    for name in _RUNTIME_FILES:
        dest_path = os.path.join(runtime_out, f"{name}.cs")
        if os.path.exists(dest_path):
            _runtime_logger.info("[Runtime] 跳过（已存在）: %s", dest_path)
            continue

        tmpl_path = os.path.join(template_dir, "csharp", "runtime", f"{name}.tmpl")
        with open(tmpl_path, encoding="utf-8") as f:
            content = f.read()

        with open(dest_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

        _runtime_logger.info("[Runtime] 生成: %s", dest_path)
```

注意：需要在文件顶部已有 `import os` 和 `import logging`（确认现有 import 包含这两个，若缺少则追加）。

---

## Task 6: main.py — 新增 --runtime-out 参数

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 将 `-i` 改为可选参数**

将现有（line 148）：

```python
p.add_argument("-i", "--input", required=True, help="输入目录或单个 xlsx 文件")
```

改为：

```python
p.add_argument("-i", "--input", default="", help="输入目录或单个 xlsx 文件")
```

- [ ] **Step 2: 在 `_build_parser()` 中添加 `--runtime-out` 参数**

在 `--go-out` 参数行之后添加：

```python
p.add_argument("--runtime-out", default="",
               help="C# 运行时库输出目录（首次生成 DataStreamReader / StblReader / TableLoader）")
```

- [ ] **Step 3: 更新 `_validate_args()` — 替换整个函数体（保留原有 `-o` 校验）**

将整个 `_validate_args` 函数体替换为（三段校验都要保留）：

```python
def _validate_args(args) -> bool:
    """校验命令行参数组合的合法性。"""
    # 数据导出模式必须提供输出目录
    if args.format in ("bin", "txt", "lua") and not args.output:
        logger.error("数据导出模式（-f %s）需要指定输出目录（-o）", args.format)
        return False

    # 数据导出模式必须提供输入目录
    if args.format in ("bin", "txt", "lua") and not args.input:
        logger.error("数据导出模式（-f %s）需要指定输入目录（-i）", args.format)
        return False

    # code 模式校验
    if args.format == "code":
        has_code_out = bool(args.csharp_out or args.go_out)
        if not args.runtime_out and not has_code_out:
            logger.error("代码生成模式（-f code）至少需要指定 --csharp-out、--go-out 或 --runtime-out 之一")
            return False
        if has_code_out and not args.input:
            logger.error("生成表格代码需要指定输入目录（-i）")
            return False

    return True
```

- [ ] **Step 4: 更新 import，并在 `main()` 中调用 generate_runtime()**

将 `main.py` 中现有的：

```python
from codegen.csharp_gen import CSharpGenerator
```

改为：

```python
from codegen.csharp_gen import CSharpGenerator, generate_runtime
```

在 `main()` 函数中，**紧接在 `tmpl_dir` 确认之后、`_collect_xlsx_files()` 调用之前**，插入：

```python
    # 运行时库生成（不依赖 xlsx 文件，提前执行）
    if args.format == "code" and args.runtime_out:
        generate_runtime(args.runtime_out, tmpl_dir)
```

这样即使没有 xlsx 文件（`--runtime-out` 单独使用），运行时库也能正常生成。

- [ ] **Step 5: 若 code 模式且无 csharp_out / go_out，跳过 xlsx 处理**

在 `_collect_xlsx_files()` 调用处，将原来的：

```python
    xlsx_files = _collect_xlsx_files(args.input)
    if not xlsx_files:
        logger.warning("未找到任何 xlsx 文件: %s", args.input)
        return 0
```

改为：

```python
    # runtime-only 模式（仅生成运行时库，无需 xlsx 输入）
    if args.format == "code" and not args.csharp_out and not args.go_out:
        return 0

    if not args.input:
        logger.error("需要 -i 参数指定输入目录")
        return 1

    xlsx_files = _collect_xlsx_files(args.input)
    if not xlsx_files:
        logger.warning("未找到任何 xlsx 文件: %s", args.input)
        return 0
```

---

## Task 7: debug_run.py — 新增 runtime 测试场景

**Files:**
- Modify: `debug_run.py`

- [ ] **Step 1: 在 TEST_MODE 注释区新增 RUNTIME_OUT 参数**

在参数配置区追加：

```python
# 运行时库输出目录（空字符串表示不生成）
RUNTIME_OUT = os.path.join(OUTPUT_ROOT, "runtime")
```

- [ ] **Step 2: 在 code 模式的 argv 构建中追加 --runtime-out**

将 `TEST_MODE == "code"` 的分支改为：

```python
    if TEST_MODE == "code":
        argv = [
            "main.py",
            "-i", INPUT_DIR,
            "-f", "code",
            "--csharp-out", CSHARP_OUT,
            "--go-out", GO_OUT,
            "--runtime-out", RUNTIME_OUT,
            "-v",
        ]
```

---

## Task 8: 端到端验证

- [ ] **Step 1: 确保测试数据存在**

```bash
cd D:\xieliujian\spacetime_table\code
python create_test_xlsx.py
```

预期：`test_data/skill.xlsx` 和 `test_data/item.xlsx` 已生成。

- [ ] **Step 2: 运行 debug_run.py（code 模式）**

修改 `debug_run.py` 中 `TEST_MODE = "code"`，然后：

```bash
python debug_run.py
```

预期输出（含以下关键行）：
```
[C#] skill → test_output/csharp
[C#] item  → test_output/csharp
[Runtime] 生成: test_output/runtime/DataStreamReader.cs
[Runtime] 生成: test_output/runtime/StblReader.cs
[Runtime] 生成: test_output/runtime/TableLoader.cs
完成: 2 成功, 0 失败
```

- [ ] **Step 3: 检查生成的 TD_SkillTable.cs 包含 Load 方法**

检查 `test_output/csharp/TD_SkillTable.cs`，确认包含：
```csharp
public void Load(string _dir, bool _useBin = true)
```
且 `${FILE_NAME}` 已被替换为 `skill`。

- [ ] **Step 4: 再次运行，验证 runtime 文件不被重复生成**

再次运行 `python debug_run.py`，预期输出：
```
[Runtime] 跳过（已存在）: ...DataStreamReader.cs
[Runtime] 跳过（已存在）: ...StblReader.cs
[Runtime] 跳过（已存在）: ...TableLoader.cs
```

- [ ] **Step 5: 检查生成文件内容**

```bash
# 检查 DataStreamReader.cs 头部
python -c "print(open('test_output/runtime/DataStreamReader.cs', encoding='utf-8').read()[:200])"

# 检查 Load 方法被正确替换
python -c "
content = open('test_output/csharp/TD_SkillTable.cs', encoding='utf-8').read()
assert 'skill.bin' in content, 'FILE_NAME 未替换'
assert 'Load(string _dir' in content, 'Load 方法未生成'
print('验证通过')
"
```
