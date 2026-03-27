"""创建测试用 xlsx 文件，用于验证配表工具。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import openpyxl

def create_test_file():
    """创建 skill.xlsx 测试文件。"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    # Row 1: 注释
    ws.append(["技能ID", "技能名称", "伤害值", "冷却时间", "是否AOE", "描述", "服务器标记"])
    # Row 2: 归属
    ws.append(["K",      "A",        "C",       "A",        "C",       "A",    "S"])
    # Row 3: 类型
    ws.append(["int",    "string",   "float",   "float",    "bool",    "string", "int"])
    # Row 4: 字段名
    ws.append(["Id",     "Name",     "Damage",  "Cooldown", "IsAoe",   "Desc",   "ServerFlag"])
    # Row 5+: 数据行
    ws.append([1001, "fireball",    120.5, 3.0, 1, "火球术",   10])
    ws.append([1002, "ice_arrow",   80.0,  2.5, 0, "冰箭术",   20])
    ws.append([1003, "thunder",     200.0, 5.0, 1, "雷击",     30])
    ws.append([1004, "heal",        0,     4.0, 0, "治疗术",   0])
    ws.append([1005, "slash",       150.0, 1.5, 0, "斩击",     15])

    os.makedirs("test_data", exist_ok=True)
    path = os.path.join("test_data", "skill.xlsx")
    wb.save(path)
    print(f"测试文件已创建: {path}")

    # 再创建一个 item.xlsx
    wb2 = openpyxl.Workbook()
    ws2 = wb2.active
    ws2.title = "Sheet1"

    ws2.append(["物品ID", "物品名称", "售价", "可堆叠"])
    ws2.append(["K",      "A",        "C",    "A"])
    ws2.append(["int",    "string",   "int",  "bool"])
    ws2.append(["Id",     "Name",     "Price","Stackable"])
    ws2.append([2001, "sword",   500,  0])
    ws2.append([2002, "potion",  50,   1])
    ws2.append([2003, "shield",  300,  0])

    path2 = os.path.join("test_data", "item.xlsx")
    wb2.save(path2)
    print(f"测试文件已创建: {path2}")

if __name__ == "__main__":
    create_test_file()
