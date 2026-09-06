#!/usr/bin/env python3
"""
Agent Skills 自动化合规性校验脚本
用于 GitHub Actions CI 与本地预检，确保所有技能目录结构与元数据 100% 合规。
"""

import os
import sys
import re

def validate_skills(skills_dir="skills"):
    if not os.path.exists(skills_dir):
        print(f"❌ 找不到目录: {skills_dir}")
        return False

    errors = []
    skill_dirs = [d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))]

    print(f"🔍 正在校验 {skills_dir}/ 下的 {len(skill_dirs)} 个技能目录...\n")

    for skill_name in sorted(skill_dirs):
        full_path = os.path.join(skills_dir, skill_name)
        skill_md = os.path.join(full_path, "SKILL.md")

        # 1. 检查必需的核心定义文件 SKILL.md
        if not os.path.isfile(skill_md):
            errors.append(f"[{skill_name}] 缺少必需的核心定义文件 SKILL.md")
            continue

        # 2. 读取并验证 Frontmatter
        try:
            with open(skill_md, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            errors.append(f"[{skill_name}] 读取 SKILL.md 失败: {e}")
            continue

        match = re.match(r"^---\s*\r?\n(.*?)\r?\n---", content, re.DOTALL)
        if not match:
            errors.append(f"[{skill_name}] SKILL.md 头部缺少以 --- 包裹的标准 YAML Frontmatter")
            continue

        fm = match.group(1)

        # 提取 name
        name_match = re.search(r"^name:\s*[\"']?([a-zA-Z0-9_-]+)[\"']?\s*$", fm, re.MULTILINE)
        desc_match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)

        if not name_match:
            errors.append(f"[{skill_name}] YAML Frontmatter 中缺少有效的 name 字段")
        else:
            declared_name = name_match.group(1).lower()
            if declared_name != skill_name.lower():
                errors.append(f"[{skill_name}] 声明的 name ({declared_name}) 与目录名 ({skill_name}) 不一致")

        if not desc_match or not desc_match.group(1).strip():
            errors.append(f"[{skill_name}] YAML Frontmatter 中缺少有效的 description 字段")

        print(f"  ✓ 校验通过: {skill_name}")

    if errors:
        print("\n❌ 发现以下合规性校验错误:")
        for err in errors:
            print(f"  - {err}")
        return False

    print("\n🎉 所有技能格式校验全部通过！零格式缺陷。")
    return True

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "skills"
    if not validate_skills(target_dir):
        sys.exit(1)
