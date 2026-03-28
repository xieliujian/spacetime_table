# 按目标分离数据文件输出目录

> 日期：2026-03-28
> 状态：待审核

## 1. 需求背景

当前问题：
- C# 代码生成包含客户端字段（K/C/A），Go 代码生成包含服务器字段（K/S/A）
- 但 bin/txt/lua 数据文件未按 client/server 分离，导致代码和数据字段不匹配
- C# 的 `ParseFromBin` 按客户端字段顺序读取，但如果读取服务器 bin 文件会出错

## 2. 目标

1. **数据文件按目标分离**：
   - `output/bin/client/` - 客户端二进制（K/C/A 字段）
   - `output/bin/server/` - 服务器二进制（K/S/A 字段）
   - txt/lua 同样分离

2. **代码文件保持独立**：
   - `output/csharp/` - C# 代码（客户端字段）
   - `output/golang/` - Go 代码（服务器字段）

3. **test_output 目录调整**：
   - 确保测试数据也按 client/server 分离

## 3. 设计方案

### 3.1 目录结构变化

**当前结构：**
```
test_output/
├── bin/
│   ├── item.bin          # 混合，字段不明确
│   └── skill.bin
├── txt/
│   ├── item.txt
│   └── skill.txt
├── lua/
│   ├── item.lua
│   └── skill.lua
├── csharp/
│   ├── TD_Item.cs
│   └── TD_ItemTable.cs
└── golang/
    └── item_table.go
```

**新结构：**
```
test_output/
├── bin/
│   ├── client/
│   │   ├── item.bin      # 包含 K/C/A 字段
│   │   └── skill.bin
│   └── server/
│       ├── item.bin      # 包含 K/S/A 字段
│       └── skill.bin
├── txt/
│   ├── client/
│   │   ├── item.txt
│   │   └── skill.txt
│   └── server/
│       ├── item.txt
│       └── skill.txt
├── lua/
│   ├── client/
│   │   ├── item.lua
│   │   └── skill.lua
│   └── server/
│       ├── item.lua
│       └── skill.lua
├── csharp/
│   ├── TD_Item.cs        # 读取 client 数据
│   └── TD_ItemTable.cs
└── golang/
    └── item_table.go     # 读取 server 数据
```

### 3.2 实现要点

1. **Writer 修改**：
   - `write()` 方法在输出时，根据 `target` 参数创建子目录
   - 路径格式：`{output_dir}/{target.value}/{file_name}.{ext}`

2. **CLI 参数保持不变**：
   - 用户仍使用 `-o output/bin -t client`
   - 工具自动在 `output/bin/` 下创建 `client/` 子目录

3. **向后兼容**：
   - 如果 `target` 为 `all`，输出到 `output/bin/all/`

## 4. 实现步骤

1. 修改 `writer/base.py`：添加 `_get_output_path()` 辅助方法
2. 修改 `writer/bin_writer.py`：使用新路径
3. 修改 `writer/txt_writer.py`：使用新路径
4. 修改 `writer/lua_writer.py`：使用新路径
5. 更新文档和测试脚本

## 5. 测试验证

```bash
# 生成客户端数据
python main.py -i test_data -o test_output/bin -f bin -t client
python main.py -i test_data -o test_output/txt -f txt -t client

# 生成服务器数据
python main.py -i test_data -o test_output/bin -f bin -t server
python main.py -i test_data -o test_output/txt -f txt -t server

# 验证目录结构
ls test_output/bin/client/
ls test_output/bin/server/
```
