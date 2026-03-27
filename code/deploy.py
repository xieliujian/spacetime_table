"""部署工具 — 将生成的代码和数据文件复制/移动到项目目标目录。

读取 deploy_config.json 中的部署规则，按规则将源目录中匹配的文件
复制（或移动）到目标目录。

用法示例::

    python deploy.py                        # 默认复制
    python deploy.py --move                 # 移动模式（源文件删除）
    python deploy.py --only "客户端C#代码"   # 只执行指定规则
    python deploy.py -c my_deploy.json      # 指定配置文件
    python deploy.py -v                     # 详细日志
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import shutil
import sys
import time

logger = logging.getLogger("deploy")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# 部署规则
# ---------------------------------------------------------------------------

class DeployRule:
    """单条部署规则。"""

    def __init__(self, name: str, src: str, dest: str, pattern: str = "*"):
        self.name = name
        self.src = src
        self.dest = dest
        self.pattern = pattern

    def __repr__(self) -> str:
        return f"DeployRule({self.name!r}, {self.src!r} → {self.dest!r}, {self.pattern!r})"


def load_deploy_config(config_path: str) -> list[DeployRule]:
    """从 JSON 文件加载部署规则列表。

    路径支持相对路径，相对于配置文件所在目录解析。
    """
    config_dir = os.path.dirname(os.path.abspath(config_path))

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rules: list[DeployRule] = []
    for item in data.get("deploy", []):
        src = item.get("src", "")
        dest = item.get("dest", "")

        if not os.path.isabs(src):
            src = os.path.normpath(os.path.join(config_dir, src))
        if not os.path.isabs(dest):
            dest = os.path.normpath(os.path.join(config_dir, dest))

        rules.append(DeployRule(
            name=item.get("name", ""),
            src=src,
            dest=dest,
            pattern=item.get("pattern", "*"),
        ))

    return rules


# ---------------------------------------------------------------------------
# 部署执行
# ---------------------------------------------------------------------------

def execute_rule(rule: DeployRule, move: bool = False) -> tuple[int, int]:
    """执行单条部署规则，返回 (成功数, 失败数)。"""
    action = "移动" if move else "复制"

    if not os.path.isdir(rule.src):
        logger.warning("[跳过] %s — 源目录不存在: %s", rule.name, rule.src)
        return 0, 0

    files = glob.glob(os.path.join(rule.src, rule.pattern))
    if not files:
        logger.warning("[跳过] %s — 无匹配文件: %s/%s", rule.name, rule.src, rule.pattern)
        return 0, 0

    os.makedirs(rule.dest, exist_ok=True)

    success = 0
    fail = 0

    for src_file in sorted(files):
        if not os.path.isfile(src_file):
            continue

        file_name = os.path.basename(src_file)
        dest_file = os.path.join(rule.dest, file_name)

        try:
            if move:
                shutil.move(src_file, dest_file)
            else:
                shutil.copy2(src_file, dest_file)
            logger.debug("  %s: %s → %s", action, file_name, rule.dest)
            success += 1
        except Exception as e:
            logger.error("  %s失败: %s — %s", action, file_name, e)
            fail += 1

    logger.info("[%s] %s — %s %d 个文件到 %s", action, rule.name, action, success, rule.dest)
    return success, fail


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="部署工具 — 将生成的文件复制/移动到项目目标目录",
    )
    p.add_argument("-c", "--config", default=os.path.join(_SCRIPT_DIR, "deploy_config.json"),
                   help="部署配置 JSON 路径（默认 deploy_config.json）")
    p.add_argument("--move", action="store_true",
                   help="移动模式（源文件删除），默认为复制模式")
    p.add_argument("--only", default="",
                   help="只执行指定名称的规则（匹配 name 字段）")
    p.add_argument("--list", action="store_true",
                   help="列出所有部署规则，不执行")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="输出详细日志")
    return p


def main() -> int:
    p = _build_parser()
    args = p.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if not os.path.isfile(args.config):
        logger.error("配置文件不存在: %s", args.config)
        return 1

    rules = load_deploy_config(args.config)
    if not rules:
        logger.warning("配置中没有部署规则")
        return 0

    if args.list:
        logger.info("部署规则列表（共 %d 条）：", len(rules))
        for i, r in enumerate(rules, 1):
            logger.info("  %d. [%s] %s → %s (%s)", i, r.name, r.src, r.dest, r.pattern)
        return 0

    if args.only:
        rules = [r for r in rules if args.only in r.name]
        if not rules:
            logger.error("未找到名称包含 %r 的规则", args.only)
            return 1

    action = "移动" if args.move else "复制"
    logger.info("开始部署（%s模式），共 %d 条规则", action, len(rules))

    start = time.time()
    total_success = 0
    total_fail = 0

    for rule in rules:
        s, f = execute_rule(rule, move=args.move)
        total_success += s
        total_fail += f

    elapsed = time.time() - start
    logger.info("部署完成: %d 个文件%s, %d 失败, 耗时 %.2f 秒",
                total_success, action, total_fail, elapsed)

    return 1 if total_fail > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
