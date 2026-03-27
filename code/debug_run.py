"""调试入口 — 预配置参数，直接运行即可调试，不影响 main.py 正常功能。

使用方式：
  1. 在 IDE 中打开此文件，按 F5 运行/调试
  2. 修改下方 TEST_MODE / TARGET / INPUT_DIR 等参数切换测试场景
  3. main.py 保持不变，正式使用时仍通过命令行传参
"""

import os
import sys
import logging

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from main import main

# ===================== 在这里修改测试参数 =====================

INPUT_DIR   = os.path.join(_SCRIPT_DIR, "test_data")
OUTPUT_ROOT = os.path.join(_SCRIPT_DIR, "test_output")

# 可选: "txt", "bin", "lua", "code"
TEST_MODE = "txt"

# 导出目标: "client", "server", "all"
TARGET = "client"

# code 模式的输出目录
CSHARP_OUT = os.path.join(OUTPUT_ROOT, "csharp")
GO_OUT     = os.path.join(OUTPUT_ROOT, "golang")

# =============================================================


def run():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if TEST_MODE == "code":
        argv = [
            "main.py",
            "-i", INPUT_DIR,
            "-f", "code",
            "--csharp-out", CSHARP_OUT,
            "--go-out", GO_OUT,
            "-v",
        ]
    else:
        argv = [
            "main.py",
            "-i", INPUT_DIR,
            "-o", os.path.join(OUTPUT_ROOT, TEST_MODE),
            "-f", TEST_MODE,
            "-t", TARGET,
            "-v",
        ]

    logging.getLogger("tableconv").info("===== 调试模式 =====")
    logging.getLogger("tableconv").info("参数: %s", " ".join(argv[1:]))

    sys.argv = argv
    return main()


if __name__ == "__main__":
    sys.exit(run())
