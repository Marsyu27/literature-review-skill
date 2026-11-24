#!/usr/bin/env python3
"""Skill 自检入口（src/reproduce.py，文献知识图谱构建）

校验 SKILL.md frontmatter、盘点资源文件、写入 results/skill_manifest.json 与 stdout(run.log)。
运行: python3 src/reproduce.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED = [
    "SKILL.md",
    "references/entity-recognition.md",
    "references/entity-alignment.md",
    "references/relation-extraction.md",
    "references/source-binding.md",
    "references/graph-query.md",
    "references/output-schema.md",
    "examples/kg-examples.md",
]


def check_frontmatter(path):
    text = open(path, encoding="utf-8").read()
    if not text.startswith("---"):
        return False, "缺少 YAML frontmatter"
    end = text.find("\n---", 3)
    if end < 0:
        return False, "frontmatter 未闭合"
    fm = text[3:end]
    return ("name:" in fm) and ("description:" in fm), ("name/description 齐全" if ("name:" in fm) and ("description:" in fm) else "缺 name 或 description")


def main():
    log = ["Skill 自检开始"]
    missing = [p for p in REQUIRED if not os.path.exists(os.path.join(ROOT, p))]
    if missing:
        log.append(f"缺失文件: {missing}")
        print("\n".join(log))
        sys.exit(1)
    log.append(f"文件盘点: {len(REQUIRED)} 个必需文件全部存在")

    ok, msg = check_frontmatter(os.path.join(ROOT, "SKILL.md"))
    log.append(f"SKILL.md frontmatter 校验: {msg}")
    if not ok:
        print("\n".join(log))
        sys.exit(1)

    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    manifest = {
        "skill": "literature-knowledge-graph",
        "challenge_id": "product-arena-10-760d1a0b",
        "files": REQUIRED,
        "notes": "Skill 以 SKILL.md 为入口，references/ 为规则（实体识别、实体对齐、关系抽取、来源绑定、图谱查询、输出契约），examples/ 为示例。",
    }
    with open(os.path.join(ROOT, "results", "skill_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    log.append("已写入 results/skill_manifest.json")
    print("\n".join(log))


if __name__ == "__main__":
    main()
