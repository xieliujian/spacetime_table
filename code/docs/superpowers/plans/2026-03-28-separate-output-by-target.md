# 实现计划：按目标分离数据文件输出目录

> 规格文档：[2026-03-28-separate-output-by-target.md](../specs/2026-03-28-separate-output-by-target.md)
> 日期：2026-03-28

## 实现步骤

### 1. 修改 Writer 基类
**文件：** `writer/base.py`

添加辅助方法生成带目标子目录的输出路径：
```python
def _get_output_path(self, output_dir: str, target: ExportTarget, file_name: str, ext: str) -> str:
    """生成输出文件路径，格式：{output_dir}/{target}/{file_name}.{ext}"""
    target_dir = os.path.join(output_dir, target.value)
    os.makedirs(target_dir, exist_ok=True)
    return os.path.join(target_dir, f"{file_name}.{ext}")
```

### 2. 修改 BinWriter
**文件：** `writer/bin_writer.py`

更新 `write()` 方法，使用新路径：
```python
def write(self, schema: TableSchema, output_dir: str, target: ExportTarget) -> None:
    output_path = self._get_output_path(output_dir, target, schema.file_name, "bin")
    # ... 其余逻辑不变
```

### 3. 修改 TxtWriter
**文件：** `writer/txt_writer.py`

更新 `write()` 方法，使用新路径：
```python
def write(self, schema: TableSchema, output_dir: str, target: ExportTarget) -> None:
    output_path = self._get_output_path(output_dir, target, schema.file_name, "txt")
    # ... 其余逻辑不变
```

### 4. 修改 LuaWriter
**文件：** `writer/lua_writer.py`

更新 `write()` 方法，使用新路径：
```python
def write(self, schema: TableSchema, output_dir: str, target: ExportTarget) -> None:
    output_path = self._get_output_path(output_dir, target, schema.file_name, "lua")
    # ... 其余逻辑不变
```

### 5. 清理旧测试输出
删除旧的混合数据文件，重新生成分离的数据。

### 6. 更新文档
**文件：** `CLAUDE.md`, `docs/2026-03-27-tableconv-design.md`

更新示例命令和目录结构说明。

## 验证清单

- [x] 客户端 bin 文件生成到 `output/bin/client/`
- [x] 服务器 bin 文件生成到 `output/bin/server/`
- [x] txt/lua 同样按目标分离
- [x] C# 代码字段与客户端数据匹配
- [x] Go 代码字段与服务器数据匹配
- [x] 文档已更新
