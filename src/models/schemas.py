from __future__ import annotations

"""pipeline 中各类结构化 artifact 的数据模型定义。"""

from dataclasses import asdict, dataclass, field
from typing import Any


# ---- collect / normalize 阶段产物 ----


@dataclass(slots=True)
class Contest:
    """标准化后的比赛元信息。"""

    contest_id: str
    source: str
    title: str
    start_time: str
    duration_seconds: int
    type: str | None = None
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Problem:
    """标准化后的题目信息。"""

    problem_id: str
    contest_id: str
    label: str
    title: str
    tags: list[str] = field(default_factory=list)
    difficulty: int | None = None
    tutorial_content: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProblemResult:
    """单场比赛中某道题的作答结果。"""

    problem_id: str
    accepted: bool
    attempts: int | None = None
    first_ac_time: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Standing:
    """标准化后的队伍排名记录。"""

    contest_id: str
    team_raw_name: str
    rank: int
    solved_count: int
    penalty: int | None = None
    problem_results: list[ProblemResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["problem_results"] = [item.to_dict() for item in self.problem_results]
        return payload


# ---- team_identity / history / metrics 阶段产物 ----


@dataclass(slots=True)
class TeamIdentity:
    """目标队伍的统一身份映射结果。"""

    canonical_id: str
    display_name: str
    aliases: list[str] = field(default_factory=list)
    platform_ids: dict[str, str] = field(default_factory=dict)
    school: str | None = None
    region: str | None = None
    matched_names: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ContestRecord:
    """从 standings 中抽取出的目标队伍单场历史记录。"""

    contest_id: str
    rank: int
    solved_count: int
    total_teams: int
    percentile_rank: float
    problem_results: list[ProblemResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["problem_results"] = [item.to_dict() for item in self.problem_results]
        return payload


@dataclass(slots=True)
class TeamHistory:
    """队伍历史参赛记录集合。"""

    canonical_id: str
    contest_records: list[ContestRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["contest_records"] = [item.to_dict() for item in self.contest_records]
        return payload


@dataclass(slots=True)
class TeamMetrics:
    """确定性指标计算阶段的输出结果。"""

    canonical_id: str
    rank_trend: list[dict[str, Any]] = field(default_factory=list)
    tag_distribution: dict[str, dict[str, float | int]] = field(default_factory=dict)
    stability_score: float = 0.0
    growth_score: float | None = None
    solve_pace: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---- analyze / report / visualize / validation 阶段产物 ----


@dataclass(slots=True)
class TeamInsight:
    """分析阶段生成的高层洞察结果。"""

    canonical_id: str
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    summary: str = ""
    training_advice: list[str] = field(default_factory=list)
    stage_analysis: str | None = None
    model_used: str | None = None
    generated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReportArtifact:
    """报告产物的元数据索引。"""

    canonical_id: str
    generated_at: str
    format: str
    path: str
    sections_present: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VisualizationArtifact:
    """可视化产物的元数据索引。"""

    canonical_id: str
    generated_at: str
    format: str
    path: str
    chart_keys: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ValidationResult:
    """最终验收阶段的检查结果。"""

    canonical_id: str
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---- orchestrator 输入任务 ----


@dataclass(slots=True)
class AnalysisTask:
    """一次分析任务的统一输入配置。"""

    target_team: str
    aliases: list[str] = field(default_factory=list)
    source: str = "fixture"
    time_range: str | None = None
    fixture_dir: str = "examples/sample_fixture"
    codeforces_handle: str | None = None
    contest_ids: list[int] = field(default_factory=list)
    max_contests: int | None = None
    include_gym: bool = False
    bridge_import_id: str | None = None
    bridge_metadata_path: str | None = None
    bridge_payload_path: str | None = None
    generate_visualize: bool = True
    generate_insight: bool = True
    enable_llm_insight: bool = True
    llm_model: str | None = None
    llm_settings_path: str | None = None
    llm_fallback_to_rule: bool = True
    school: str | None = None
    region: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
