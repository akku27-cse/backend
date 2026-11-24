from app.services.evidence_collector import EvidenceCollector
from app.services.research_planner import ResearchPlanner


def test_research_planner_creates_dependent_web_tasks():
    plan = ResearchPlanner().build(
        "execution-1", "Research the latest AI agents with detailed sources", False
    )

    assert [task.required_tool for task in plan.tasks] == [
        "web_search",
        "webpage_extraction",
    ]
    assert plan.tasks[1].dependencies == ["web-search"]


def test_evidence_collector_deduplicates_records():
    collector = EvidenceCollector("execution-1", "What is RAG?")

    first = collector.add(
        "web-search",
        "Web",
        "Example",
        "Retrieved evidence",
        "tavily",
        "https://example.com",
    )
    duplicate = collector.add(
        "web-search",
        "Web",
        "Example",
        "Retrieved evidence",
        "tavily",
        "https://example.com",
    )

    assert first is not None
    assert duplicate is None
    assert len(collector.records) == 1
