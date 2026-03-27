# Go 运行时读表支持库设计文档

**日期**: 2026-03-27  
**项目**: spacetime_table — Python 配表转换工具  
**范围**: Go 服务端运行时支持库 + 表格 Load 接口  
**状态**: 已通过评审  

---

## 背景

当前工具已能生成 Go 表格代码（`skill_table.go` 等），`ParseFromBin` 引用了 `*DataStreamReader`，但该类型在 Go 端不存在，生成的代码无法编译。每张表也只有 `ParseFromBin` / `ParseFromTxt` 低层方法，缺少统一的 `Load(dir string, useBin bool) error` 入口。

---

## 目标

1. 为 Go 服务端提供完整运行时支持库（3 个 `.go` 文件），与现有表格代码同 `package table`，导入后立即编译通过。
2. 每张生成的 `*Table` 新增 `Load(dir string, useBin bool) error` 方法。
3. Python 工具扩展 `generate_runtime` 逻辑，增加 `--go-runtime-out` 独立参数，在指定目录输出 Go runtime 文件，仅首次不存在时生成（逐文件检查）。

---

## 架构

### 方案：镜像 C# 三文件结构（方案 A）

C# runtime 文件由 `--runtime-out` 控制，Go runtime 文件由 `--go-runtime-out` 控制，两者独立：

```
<--runtime-out 目录>/        (C# 端，已有)
├── DataStreamReader.cs
├── StblReader.cs
└── TableLoader.cs

<--go-runtime-out 目录>/     (Go 端，新增)
├── data_stream_reader.go
├── stbl_reader.go
└── table_loader.go
```

职责边界：

| 文件 | 类型/函数 | 职责 | 依赖 |
|------|-----------|------|------|
| `data_stream_reader.go` | `DataStreamReader` struct | byte 位置游标 + 类型读取 | encoding/binary, math |
| `stbl_reader.go` | `StblReader` struct | STBL 格式解析，持有 Reader | encoding/binary, fmt |
| `table_loader.go` | 包级函数 | 文件 IO | os |

所有文件均为 `package table`，与生成的表格代码同包，无需 import 语句。

---

## Go 运行时文件详细设计

### data_stream_reader.go

```
package table
import: encoding/binary, math
```

- `encoding/binary`：`binary.LittleEndian.Uint32` 等读取多字节整数
- `math`：`math.Float32frombits` 将 uint32 位模式转为 float32

**结构体**

```go
type DataStreamReader struct {
    buf []byte
    pos int
}
```

**构造**

```go
func NewDataStreamReader(buf []byte, startPos int) *DataStreamReader
```

**公开 API**

| 方法 | 说明 |
|------|------|
| `ReadInt32() int32` | zigzag varint → int32 |
| `ReadInt64() int64` | zigzag varint → int64 |
| `ReadFloat32() float32` | 读 4 字节 LE uint32，用 `math.Float32frombits` 转为 float32 |
| `ReadBool() bool` | 1 字节，非 0 为 true |
| `ReadString() string` | 2 字节 LE 长度 + UTF-8 字节 |
| `ReadByte() byte` | 1 字节 |
| `ReadVector2() Vector2` | 2 × ReadFloat32() |
| `ReadVector3() Vector3` | 3 × ReadFloat32() |

**ReadFloat32 示例实现**

```go
func (r *DataStreamReader) ReadFloat32() float32 {
    bits := binary.LittleEndian.Uint32(r.buf[r.pos:])
    r.pos += 4
    return math.Float32frombits(bits)
}
```

**私有辅助**

| 方法 | 说明 |
|------|------|
| `readRawByte() byte` | 读 1 字节，pos++ |
| `readUint16LE() uint16` | 读 2 字节 LE |
| `readVarint() uint64` | unsigned varint 解码（与 Python writer 对称） |
| `zigzagDecode32(n uint32) int32` | zigzag 还原 |
| `zigzagDecode64(n uint64) int64` | zigzag 还原 |

**辅助类型**（同文件内声明，避免 Unity 依赖）

```go
type Vector2 struct{ X, Y float32 }
type Vector3 struct{ X, Y, Z float32 }
```

---

### stbl_reader.go

```
package table
import: encoding/binary, fmt
```

- `encoding/binary`：读取 uint32/uint16
- `fmt`：`fmt.Errorf` 格式化含调试信息的错误消息

**STBL 文件头（32 字节小端序）**

| 偏移 | 大小 | 字段 |
|------|------|------|
| 0 | 4 | magic "STBL" |
| 4 | 2 | version |
| 6 | 2 | flags |
| 8 | 2 | fieldCount |
| 10 | 4 | rowCount (uint32) |
| 14 | 4 | schemaOffset |
| 18 | 4 | dataOffset |
| 22 | 10 | reserved |

**结构体**

```go
type StblReader struct {
    RowCount int
    Reader   *DataStreamReader
}
```

> **字段命名说明**：Go runtime 库公开字段使用 PascalCase（`RowCount`、`Reader`），符合 Go 导出规范，与 C# camelCase 规范不同（C# 规范仅约束 `TD_` 表格类的属性）。

**构造逻辑**

```go
func NewStblReader(data []byte) (*StblReader, error)
```

1. 若 `len(data) < 32` → 返回 `fmt.Errorf("STBL 数据过短: %d 字节", len(data))`
2. 校验 magic：逐字节比较 `data[0]='S'`, `data[1]='T'`, `data[2]='B'`, `data[3]='L'`  
   不符 → 返回 `fmt.Errorf("STBL magic 校验失败: 0x%02X%02X%02X%02X", data[0], data[1], data[2], data[3])`
3. `rowCount = int(binary.LittleEndian.Uint32(data[10:14]))`
4. `dataOffset = int(binary.LittleEndian.Uint32(data[18:22]))`
5. `rowDataStart = dataOffset + rowCount * 4`（跳过行偏移表）
6. 若 `rowDataStart > len(data)` → 返回 `fmt.Errorf("STBL dataOffset 超界: rowDataStart=%d, len=%d", rowDataStart, len(data))`
7. 返回 `&StblReader{RowCount: rowCount, Reader: NewDataStreamReader(data, rowDataStart)}`

---

### table_loader.go

```
package table
import: os
```

**函数**

```go
// LoadBytes 读取文件全部字节，文件不存在返回带路径的 error
func LoadBytes(path string) ([]byte, error)

// LoadText 读取 UTF-8 文本文件内容
func LoadText(path string) (string, error)
```

---

## Table.tmpl 新增 Load 方法

在现有 `ParseFromTxt` 之后追加（不需要在开头重置 dataDict/dataList，ParseFromBin/ParseFromTxt 内部已初始化）：

```go
// Load 从目录加载全部数据，useBin=true 读 bin 格式，否则读 txt 格式
func (t *${STRUCT_NAME}Table) Load(dir string, useBin bool) error {
    if useBin {
        data, err := LoadBytes(filepath.Join(dir, "${FILE_NAME}.bin"))
        if err != nil {
            return err
        }
        stbl, err := NewStblReader(data)
        if err != nil {
            return err
        }
        t.ParseFromBin(stbl.Reader, stbl.RowCount)
    } else {
        content, err := LoadText(filepath.Join(dir, "${FILE_NAME}.txt"))
        if err != nil {
            return err
        }
        t.ParseFromTxt(content)
    }
    return nil
}
```

**占位符定义**

| 占位符 | 示例 | 来源 |
|--------|------|------|
| `${FILE_NAME}` | `skill` | Excel 文件名（蛇形，无扩展名） |
| `${STRUCT_NAME}` | `Skill` | PascalCase 结构体名 |
| `${KEY_TYPE}` | `int32` | 主键 Go 类型 |

**IMPORTS 说明**：`_build_imports` 需新增 `"path/filepath"` 始终无条件包含（`"strings"` 已有，无需变动）。

---

## Python 工具侧改动

### 新增 Go 模板目录

```
templates/golang/runtime/
├── data_stream_reader.tmpl
├── stbl_reader.tmpl
└── table_loader.tmpl
```

### golang_gen.py 新增 generate_go_runtime()

```python
def generate_go_runtime(runtime_out: str, template_dir: str) -> None:
    """输出 Go 运行时支持库，逐文件检查，仅在文件不存在时生成。"""
```

- 3 个输出文件：`data_stream_reader.go`、`stbl_reader.go`、`table_loader.go`
- 与 `csharp_gen.generate_runtime()` 逻辑完全对称（逐文件 exists 检查，存在则 INFO 日志 + 跳过）

### main.py

1. **新增 `--go-runtime-out` 参数**（与 `--runtime-out` 并列）：

   ```python
   p.add_argument("--go-runtime-out", default="",
                  help="Go 运行时库输出目录（首次生成 data_stream_reader / stbl_reader / table_loader）")
   ```

2. **更新 import 语句**（第 41 行）：

   ```python
   from codegen.golang_gen import GolangGenerator, generate_go_runtime
   ```

3. **新增调用**（在 `generate_runtime` 调用之后）：

   ```python
   if args.format == "code" and args.go_runtime_out:
       generate_go_runtime(args.go_runtime_out, tmpl_dir)
   ```

4. **更新 `_validate_args`**：允许仅传入 `--go-runtime-out` 时 `--input` 不必须（与 `--runtime-out` 独立逻辑对称）。

### Table.tmpl

- 追加 `Load` 方法
- `_build_imports` 新增 `"path/filepath"` 无条件包含

### debug_run.py

新增 `GO_RUNTIME_OUT` 变量并在 `code` 模式参数中传入 `--go-runtime-out`：

```python
GO_RUNTIME_OUT = os.path.join(_SCRIPT_DIR, "go_runtime")
# 在 argv 中添加：
"--go-runtime-out", GO_RUNTIME_OUT,
```

---

## 文件变更清单

| 操作 | 路径 | 说明 |
|------|------|------|
| 新建 | `templates/golang/runtime/data_stream_reader.tmpl` | Go DataStreamReader 模板 |
| 新建 | `templates/golang/runtime/stbl_reader.tmpl` | Go StblReader 模板 |
| 新建 | `templates/golang/runtime/table_loader.tmpl` | Go TableLoader 模板 |
| 修改 | `templates/golang/Table.tmpl` | 追加 Load() 方法 |
| 修改 | `codegen/golang_gen.py` | 新增 generate_go_runtime()，_build_imports 无条件含 filepath |
| 修改 | `main.py` | 新增 --go-runtime-out 参数、import、调用、validate 更新 |
| 修改 | `debug_run.py` | 新增 GO_RUNTIME_OUT，传入 --go-runtime-out |

---

## 错误处理

| 情况 | 处理方式 |
|------|---------|
| STBL magic 不符 | `fmt.Errorf` 返回含 hex 字节的错误消息 |
| STBL 数据过短（< 32 字节） | `fmt.Errorf` 返回实际长度 |
| STBL dataOffset 超界 | `fmt.Errorf` 返回 rowDataStart 和 len 信息 |
| 文件不存在 | `LoadBytes`/`LoadText` 返回 os.ReadFile 原始 error |
| Go runtime 文件已存在 | Python 工具逐文件检查，跳过已存在的，输出 INFO 日志 |

---

## 不在范围内

- Go 端 Vector2/Vector3 的数学运算（只需 struct 定义）
- 加密/压缩支持
- Go module 管理（runtime 文件由使用方集成到自己的 module）
