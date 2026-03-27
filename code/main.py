"""配表转换工具 — CLI 入口

将 Excel (xlsx) 配表文件转换为多种输出格式，供 Unity 客户端和 Go 服务端使用。

用法示例::

    # 导出客户端二进制数据
    python main.py -i ./xlsx -o ./output/bin -f bin -t client

    # 导出服务器文本数据
    python main.py -i ./xlsx -o ./output/txt -f txt -t server

    # 导出客户端 Lua
    python main.py -i ./xlsx -o ./output/lua -f lua -t client

    # 生成 C# + Go 代码
    python main.py -i ./xlsx -f code --csharp-out ./output/csharp --go-out ./output/golang
"""

from __future__ import annotations

import argparse
import glob
import logging
import os
import sys
import time

# 将脚本所在目录加入 sys.path，避免 parser 包名与标准库冲突
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from config import Config
from table_parser.excel_parser import ExcelParser
from table_parser.types import ExportTarget
from writer.bin_writer import BinWriter
from writer.txt_writer import TxtWriter
from writer.lua_writer import LuaWriter
from codegen.csharp_gen import CSharpGenerator
from codegen.golang_gen import GolangGenerator

logger = logging.getLogger("tableconv")

# ---------------------------------------------------------------------------
# Writer 工厂
# ---------------------------------------------------------------------------

_WRITER_MAP = {
    "bin": BinWriter,
    "txt": TxtWriter,
    "lua": LuaWriter,
}


def _get_writer(format_name: str):
    """根据格式名获取对应的 Writer 实例。"""
    cls = _WRITER_MAP.get(format_name)
    if cls is None:
        raise ValueError(f"不支持的输出格式: {format_name}，可选: {', '.join(_WRITER_MAP)}")
    return cls()


# ---------------------------------------------------------------------------
# ExportTarget 解析
# ---------------------------------------------------------------------------

_TARGET_MAP = {
    "client": ExportTarget.CLIENT,
    "server": ExportTarget.SERVER,
    "all": ExportTarget.ALL,
}


def _parse_target(target_str: str) -> ExportTarget:
    """将命令行参数转为 ExportTarget 枚举。"""
    t = _TARGET_MAP.get(target_str)
    if t is None:
        raise ValueError(f"不支持的导出目标: {target_str}，可选: {', '.join(_TARGET_MAP)}")
    return t


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

def _collect_xlsx_files(input_path: str) -> list[str]:
    """收集输入路径下的所有 xlsx 文件（跳过临时文件）。"""
    if os.path.isfile(input_path):
        return [input_path]

    if not os.path.isdir(input_path):
        logger.error("输入路径不存在: %s", input_path)
        return []

    files = glob.glob(os.path.join(input_path, "*.xlsx"))
    return [f for f in files if not os.path.basename(f).startswith("~$")]


def _process_data(file_path: str, args, config: Config) -> None:
    """处理单个 xlsx 文件的数据导出（bin / txt / lua）。"""
    file_name = os.path.splitext(os.path.basename(file_path))[0]

    if args.format == "lua" and not config.should_generate_lua(file_name):
        logger.debug("跳过 Lua 导出（不在白名单）: %s", file_name)
        return

    parser = ExcelParser()
    schema = parser.parse(file_path)

    target = _parse_target(args.target)
    writer = _get_writer(args.format)
    writer.write(schema, args.output, target)

    logger.info("[%s] %s → %s", args.format.upper(), file_name, args.output)


def _process_code(file_path: str, args, config: Config, tmpl_dir: str) -> None:
    """处理单个 xlsx 文件的代码生成。"""
    file_name = os.path.splitext(os.path.basename(file_path))[0]

    if not config.should_generate_code(file_name):
        logger.debug("跳过代码生成（在忽略列表）: %s", file_name)
        return

    parser = ExcelParser()
    schema = parser.parse(file_path)

    if args.csharp_out:
        CSharpGenerator().generate(schema, args.csharp_out, tmpl_dir)
        logger.info("[C#] %s → %s", file_name, args.csharp_out)

    if args.go_out:
        GolangGenerator().generate(schema, args.go_out, tmpl_dir)
        logger.info("[Go] %s → %s", file_name, args.go_out)


# ---------------------------------------------------------------------------
# 参数解析
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    p = argparse.ArgumentParser(
        description="配表转换工具 — 将 xlsx 配表转换为 bin/txt/lua 数据或 C#/Go 代码",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-i", "--input", required=True, help="输入目录或单个 xlsx 文件")
    p.add_argument("-o", "--output", default="", help="数据输出目录（bin/txt/lua 模式必填）")
    p.add_argument("-f", "--format", required=True, choices=["bin", "txt", "lua", "code"],
                   help="输出格式")
    p.add_argument("-t", "--target", default="client", choices=["client", "server", "all"],
                   help="导出目标（默认 client）")
    p.add_argument("-c", "--config", default="config.json", help="配置 JSON 路径")
    p.add_argument("--csharp-out", default="", help="C# 代码输出目录（code 模式）")
    p.add_argument("--go-out", default="", help="Go 代码输出目录（code 模式）")
    p.add_argument("--tmpl", default="", help="模板目录（默认脚本同级 templates/）")
    p.add_argument("-v", "--verbose", action="store_true", help="输出详细日志")
    return p


def _validate_args(args) -> bool:
    """校验命令行参数组合的合法性。"""
    if args.format in ("bin", "txt", "lua") and not args.output:
        logger.error("数据导出模式（-f %s）需要指定输出目录（-o）", args.format)
        return False

    if args.format == "code" and not args.csharp_out and not args.go_out:
        logger.error("代码生成模式（-f code）至少需要指定 --csharp-out 或 --go-out 之一")
        return False

    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主函数，返回退出码。"""
    p = _build_parser()
    args = p.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if not _validate_args(args):
        return 1

    config = Config.load(args.config)

    tmpl_dir = args.tmpl or os.path.join(_SCRIPT_DIR, "templates")
    if args.format == "code" and not os.path.isdir(tmpl_dir):
        logger.error("模板目录不存在: %s", tmpl_dir)
        return 1

    xlsx_files = _collect_xlsx_files(args.input)
    if not xlsx_files:
        logger.warning("未找到任何 xlsx 文件: %s", args.input)
        return 0

    logger.info("找到 %d 个 xlsx 文件，格式: %s，目标: %s", len(xlsx_files), args.format, args.target)

    start = time.time()
    success_count = 0
    error_count = 0

    for file_path in sorted(xlsx_files):
        try:
            if args.format == "code":
                _process_code(file_path, args, config, tmpl_dir)
            else:
                _process_data(file_path, args, config)
            success_count += 1
        except Exception as e:
            error_count += 1
            logger.error("处理失败 %s: %s", os.path.basename(file_path), e)

    elapsed = time.time() - start
    logger.info("完成: %d 成功, %d 失败, 耗时 %.2f 秒", success_count, error_count, elapsed)

    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
