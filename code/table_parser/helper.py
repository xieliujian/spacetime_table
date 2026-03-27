"""表转换相关的命名转换与校验工具。"""

import re

# 合法表文件名：仅小写字母与下划线，且不能以首尾下划线结尾。
# 单段小写名用 ^[a-z]+$；多段用 ^[a-z][a-z_]*[a-z]$。
_LEGAL_FILE_NAME = re.compile(r"^[a-z]+$|^[a-z][a-z_]*[a-z]$")


def snake_to_pascal(name: str) -> str:
    """将 snake_case 转为 PascalCase。

    例如：``skill_effect`` → ``SkillEffect``，``skill`` → ``Skill``。
    """
    if not name:
        return ""
    parts = [p for p in name.split("_") if p]
    return "".join(p[:1].upper() + p[1:] for p in parts)


def snake_to_camel(name: str) -> str:
    """将 snake_case 转为 camelCase。

    例如：``skill_effect`` → ``skillEffect``。
    """
    pascal = snake_to_pascal(name)
    if not pascal:
        return ""
    return pascal[0].lower() + pascal[1:]


def to_camel_case(name: str) -> str:
    """将字段名（如 PascalCase）转为 camelCase：仅首字母小写。

    例如：``Id`` → ``id``，``HpMax`` → ``hpMax``，``Name`` → ``name``。
    """
    if not name:
        return ""
    return name[0].lower() + name[1:]


def to_private_field(name: str) -> str:
    """字段名转为带 ``m_`` 前缀的私有字段形式。

    例如：``Id`` → ``m_Id``，``Name`` → ``m_Name``。
    """
    return f"m_{name}"


def is_legal_file_name(name: str) -> bool:
    """判断是否为合法表文件名：仅小写字母与下划线，且首尾不能是下划线。

    合法模式：``^[a-z]+$`` 或 ``^[a-z][a-z_]*[a-z]$``。
    """
    return bool(name and _LEGAL_FILE_NAME.fullmatch(name))


def format_class_name(file_name: str) -> str:
    """由表文件名得到 C# 风格类名（snake_case → PascalCase）。

    例如：``skill_effect`` → ``SkillEffect``。
    """
    return snake_to_pascal(file_name)
