"""Catalog sync regression test between the two sibling skills.

两个 Skill（agent-usage-report 与 review-material-organizer）共用同一张
Agent 目录表（scan_agents.py 的 _agent_paths()）。本测试断言两边完全一致，
防止只改一边导致召回能力分叉。

找不到对方 Skill 时（独立分发场景）自动 skip，不影响独立测试运行。
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__)  # 不 resolve()：保留项目根符号链接路径，便于定位兄弟 Skill
SCRIPTS = HERE.parents[1] / "scripts"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("scan_agents_%d" % id(path), path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def _find_sibling_scan_agents() -> Path | None:
    own = SCRIPTS / "scan_agents.py"
    project_root = HERE.parents[2]
    candidates = [
        project_root / "agent-usage-report" / "scripts" / "scan_agents.py",
        project_root / "review-material-organizer" / "scripts" / "scan_agents.py",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.parent != own.parent:
            return candidate
    return None


class CatalogSyncTests(unittest.TestCase):
    def test_agent_catalog_identical_between_sibling_skills(self):
        sibling = _find_sibling_scan_agents()
        if sibling is None:
            self.skipTest("兄弟 Skill 不在本目录旁（独立分发场景），跳过目录表同步检查")

        own_mod = _load(SCRIPTS / "scan_agents.py")
        sibling_mod = _load(sibling)

        own_catalog = {
            name: sorted(str(p) for p in paths)
            for name, paths in own_mod._agent_paths().items()
        }
        sibling_catalog = {
            name: sorted(str(p) for p in paths)
            for name, paths in sibling_mod._agent_paths().items()

        }
        if own_catalog != sibling_catalog:
            only_own = sorted(set(own_catalog) - set(sibling_catalog))
            only_sibling = sorted(set(sibling_catalog) - set(own_catalog))
            diff_paths = sorted(
                name for name in set(own_catalog) & set(sibling_catalog)
                if own_catalog[name] != sibling_catalog[name]
            )
            details = []
            if only_own:
                details.append("仅本 Skill 有的工具: %s" % ", ".join(only_own))
            if only_sibling:
                details.append("仅对方 Skill 有的工具: %s" % ", ".join(only_sibling))
            if diff_paths:
                details.append("路径不一致的工具: %s" % ", ".join(diff_paths))
            self.fail(
                "两个 Skill 的 Agent 目录表不一致，召回能力会分叉。请同步修改两侧 scan_agents.py 的 _agent_paths()。%s"
                % ("；".join(details) if details else "")
            )


if __name__ == "__main__":
    unittest.main()
