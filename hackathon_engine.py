import json
import logging
import re
from typing import Any, Dict, List, Optional

from llm import llm_manager

logger = logging.getLogger(__name__)


MODE_MAP = {
    "roadmap": "Business + Roadmap Focus",
    "basic_poc": "Basic POC Prototype",
    "advanced": "Advanced Production Vision",
}


DOMAIN_KEYWORDS = {
    "support": ["call", "support", "ticket", "complaint", "service", "resolution", "agent", "crm"],
    "fraud": ["fraud", "phishing", "scam", "chargeback", "unauthorized", "suspicious", "aml"],
    "onboarding": ["onboard", "kyc", "account opening", "form", "document", "verification"],
    "operations": ["ops", "operation", "reconcile", "settlement", "exception", "manual", "back office"],
    "lending": ["loan", "emi", "collections", "delinquent", "credit", "underwriting"],
    "sales": ["cross-sell", "upsell", "offer", "campaign", "deposit", "card", "conversion"],
}


IDEA_BLUEPRINTS = [
    {
        "suffix": "Resolution Copilot",
        "summary": "An AI assistant that converts fragmented issue data into ranked resolutions for frontline teams.",
        "fit": ["CRM", "Call Center", "Mobile App Backend"],
        "impact": "Reduce repeat contacts by 18-30% and cut average handling time by 20-35%.",
        "ease": 5,
        "innovation": 3,
        "feasibility": 5,
        "adoption": 5,
        "simplicity": 5,
        "systems": ["CRM", "ticketing", "knowledge base", "interaction logs"],
    },
    {
        "suffix": "Journey Intervention Engine",
        "summary": "A predictive layer that detects customer friction and triggers the next best intervention before the customer calls.",
        "fit": ["Mobile App", "CRM", "Outbound Service Hub"],
        "impact": "Prevent 12-20% of avoidable service contacts and improve digital completion rates by 8-15%.",
        "ease": 3,
        "innovation": 5,
        "feasibility": 4,
        "adoption": 4,
        "simplicity": 3,
        "systems": ["mobile telemetry", "CRM", "notification APIs", "case history"],
    },
    {
        "suffix": "Operations Exception Radar",
        "summary": "A triage workspace that groups exceptions, explains root causes, and recommends the shortest resolution path.",
        "fit": ["Operations Dashboard", "Backend Ops Console"],
        "impact": "Reduce manual investigation effort by 25-40% and improve same-day exception closure by 15-25%.",
        "ease": 4,
        "innovation": 4,
        "feasibility": 5,
        "adoption": 4,
        "simplicity": 4,
        "systems": ["SQL databases", "batch logs", "case queues", "PDF or email evidence"],
    },
    {
        "suffix": "Decision Intelligence Studio",
        "summary": "An explainable intelligence layer that packages customer context, policy signals, and recommended actions for staff.",
        "fit": ["CRM", "Branch", "Relationship Manager Workspace"],
        "impact": "Improve decision consistency by 20-30% and reduce training dependency for new staff by 30-50%.",
        "ease": 3,
        "innovation": 4,
        "feasibility": 4,
        "adoption": 4,
        "simplicity": 3,
        "systems": ["CRM", "policy docs", "core banking", "customer profile APIs"],
    },
    {
        "suffix": "Trust and Fraud Shield",
        "summary": "A guided investigation assistant that highlights suspicious patterns, required actions, and audit-ready rationale.",
        "fit": ["Fraud Desk", "Call Center", "Mobile Security Journey"],
        "impact": "Cut manual review effort by 30-45% and lower false-positive handling by 10-18%.",
        "ease": 3,
        "innovation": 4,
        "feasibility": 4,
        "adoption": 4,
        "simplicity": 3,
        "systems": ["transaction streams", "fraud rules", "case management", "authentication logs"],
    },
]


def _clean_problem(problem_statement: str) -> str:
    return re.sub(r"\s+", " ", problem_statement).strip()


def _normalize_fit_channels(channels: List[str]) -> List[str]:
    cleaned: List[str] = []
    for channel in channels:
        normalized = re.sub(r"^fit_channel_?\d*:\s*", "", channel, flags=re.IGNORECASE).strip()
        if normalized:
            cleaned.append(normalized)
    return cleaned or ["CRM"]


def _dominant_domain(problem_statement: str) -> str:
    normalized = problem_statement.lower()
    scores: Dict[str, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        scores[domain] = sum(1 for keyword in keywords if keyword in normalized)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return ranked[0][0] if ranked and ranked[0][1] > 0 else "support"


def _domain_label(domain: str) -> str:
    return {
        "support": "Service",
        "fraud": "Fraud",
        "onboarding": "Onboarding",
        "operations": "Operations",
        "lending": "Lending",
        "sales": "Growth",
    }.get(domain, "Banking")


def _score_idea(idea: Dict[str, Any]) -> float:
    return round(
        idea["business_impact_score"] * 0.45
        + idea["practical_adoption_score"] * 0.35
        + idea["simplicity_score"] * 0.20,
        2,
    )


def _try_llm_json(prompt: str) -> Optional[Dict[str, Any]]:
    try:
        raw = llm_manager.generate_response(prompt)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        return json.loads(match.group(0))
    except Exception as exc:
        logger.warning("Hackathon engine LLM fallback engaged: %s", exc)
        return None


def _try_llm_delimited_ideas(problem: str) -> Optional[Dict[str, Any]]:
    prompt = f"""
Return exactly 3 lines and nothing else.
Each line must use this format:
title || problem_understanding || business_impact || ease_of_implementation || innovation_level || real_world_feasibility || business_impact_score || practical_adoption_score || simplicity_score || fit_channel_1,fit_channel_2
Allowed values for ease_of_implementation, innovation_level, real_world_feasibility: High, Medium, Low.
Scores must be integers from 1 to 5.
Problem: {problem}
"""
    try:
        raw = llm_manager.generate_response(prompt)
        ideas: List[Dict[str, Any]] = []
        for line in raw.splitlines():
            cleaned = line.strip().lstrip("-0123456789. ")
            if not cleaned or ("||" not in cleaned and "|" not in cleaned):
                continue
            separator = "||" if "||" in cleaned else "|"
            parts = [part.strip() for part in cleaned.split(separator)]
            if len(parts) < 6:
                continue

            title = parts[0]
            problem_understanding = parts[1] if len(parts) > 1 else f"The problem is that {problem.lower()} is creating avoidable friction."
            business_impact = parts[2] if len(parts) > 2 else "Improve customer resolution speed and reduce manual effort."
            ease_of_implementation = parts[3] if len(parts) > 3 else "Medium"
            innovation_level = parts[4] if len(parts) > 4 else "Medium"
            real_world_feasibility = parts[5] if len(parts) > 5 else "High"
            business_impact_score = parts[6] if len(parts) > 6 else 4
            practical_adoption_score = parts[7] if len(parts) > 7 else 4
            simplicity_score = parts[8] if len(parts) > 8 else 4
            fit_channels = _normalize_fit_channels([item.strip() for item in (parts[9] if len(parts) > 9 else parts[1]).split(",") if item.strip()])

            ideas.append(
                {
                    "title": title,
                    "problem_understanding": problem_understanding,
                    "business_impact": business_impact,
                    "ease_of_implementation": ease_of_implementation,
                    "innovation_level": innovation_level,
                    "real_world_feasibility": real_world_feasibility,
                    "business_impact_score": business_impact_score,
                    "practical_adoption_score": practical_adoption_score,
                    "simplicity_score": simplicity_score,
                    "fit_channels": fit_channels or ["CRM"],
                }
            )
        if not ideas:
            return None
        return {
            "problem_summary": "LLM-generated banking hackathon ideas.",
            "ideas": ideas,
        }
    except Exception as exc:
        logger.warning("Hackathon engine LLM fallback engaged: %s", exc)
        return None


def _enrich_llm_ideas(problem: str, ideas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    for index, idea in enumerate(ideas[:3], start=1):
        fit_channels = idea.get("fit_channels") or ["CRM"]
        business_impact_score = int(idea.get("business_impact_score", 4)) if str(idea.get("business_impact_score", "")).isdigit() else 4
        practical_adoption_score = int(idea.get("practical_adoption_score", 4)) if str(idea.get("practical_adoption_score", "")).isdigit() else 4
        simplicity_score = int(idea.get("simplicity_score", 4)) if str(idea.get("simplicity_score", "")).isdigit() else 4

        enriched_idea = {
            "id": f"idea-{index}",
            "title": idea.get("title", f"Banking Idea {index}"),
            "problem_understanding": idea.get(
                "problem_understanding",
                f"The core issue is that {problem.lower()} creates avoidable delay, fragmented execution, and poor service consistency.",
            ),
            "business_impact": idea.get("business_impact", "Reduce manual effort and improve resolution speed for banking teams."),
            "ease_of_implementation": idea.get("ease_of_implementation", "Medium"),
            "innovation_level": idea.get("innovation_level", "Medium"),
            "real_world_feasibility": idea.get("real_world_feasibility", "High"),
            "business_impact_score": max(1, min(5, business_impact_score)),
            "practical_adoption_score": max(1, min(5, practical_adoption_score)),
            "simplicity_score": max(1, min(5, simplicity_score)),
            "fit_channels": _normalize_fit_channels(fit_channels) if isinstance(fit_channels, list) else ["CRM"],
            "solution_summary": idea.get("solution_summary", idea.get("problem_understanding", "Practical AI workflow for banking execution improvement.")),
            "integration_hint": idea.get("integration_hint", ["CRM", "knowledge base", "ticket history"]),
        }
        enriched_idea["weighted_score"] = _score_idea(enriched_idea)
        enriched.append(enriched_idea)
    return enriched


def generate_ideas(problem_statement: str) -> Dict[str, Any]:
    problem = _clean_problem(problem_statement)
    llm_payload = _try_llm_delimited_ideas(problem)
    if llm_payload and isinstance(llm_payload.get("ideas"), list) and llm_payload["ideas"]:
        llm_ideas = _enrich_llm_ideas(problem, llm_payload["ideas"])
        heuristic_payload = None
        if len(llm_ideas) < 3:
            domain = _dominant_domain(problem)
            label = _domain_label(domain)
            heuristic_candidates: List[Dict[str, Any]] = []
            for index, blueprint in enumerate(IDEA_BLUEPRINTS[:4], start=1):
                impact_score = min(5, blueprint["ease"] + blueprint["innovation"] // 2 + 1)
                heuristic_idea = {
                    "id": f"idea-h-{index}",
                    "title": f"{label} {blueprint['suffix']}",
                    "problem_understanding": f"The core issue is that {problem.lower()} creates fragmented decisions, slow service recovery, and avoidable workload for banking teams.",
                    "business_impact": blueprint["impact"],
                    "ease_of_implementation": "High" if blueprint["ease"] >= 4 else "Medium",
                    "innovation_level": "High" if blueprint["innovation"] >= 5 else "Medium",
                    "real_world_feasibility": "High" if blueprint["feasibility"] >= 4 else "Medium",
                    "business_impact_score": impact_score,
                    "practical_adoption_score": blueprint["adoption"],
                    "simplicity_score": blueprint["simplicity"],
                    "fit_channels": blueprint["fit"],
                    "solution_summary": blueprint["summary"],
                    "integration_hint": blueprint["systems"],
                }
                heuristic_idea["weighted_score"] = _score_idea(heuristic_idea)
                heuristic_candidates.append(heuristic_idea)
            existing_titles = {idea["title"].strip().lower() for idea in llm_ideas}
            fill_ideas = [idea for idea in heuristic_candidates if idea["title"].strip().lower() not in existing_titles]
            ranked = sorted((llm_ideas + fill_ideas)[:4], key=lambda item: item["weighted_score"], reverse=True)
        else:
            ranked = sorted(llm_ideas, key=lambda item: item["weighted_score"], reverse=True)
        return {
            "problem_summary": llm_payload.get("problem_summary", problem),
            "ideas": ranked,
            "ranking_basis": ["Business impact", "Practical adoption", "Simplicity"],
            "recommended_idea_id": ranked[0]["id"],
            "generated_with": "hybrid-llm",
        }

    domain = _dominant_domain(problem)
    label = _domain_label(domain)
    ideas: List[Dict[str, Any]] = []
    for index, blueprint in enumerate(IDEA_BLUEPRINTS[:4], start=1):
        impact_score = min(5, blueprint["ease"] + blueprint["innovation"] // 2 + 1)
        idea = {
            "id": f"idea-{index}",
            "title": f"{label} {blueprint['suffix']}",
            "problem_understanding": f"The core issue is that {problem.lower()} creates fragmented decisions, slow service recovery, and avoidable workload for banking teams.",
            "business_impact": blueprint["impact"],
            "ease_of_implementation": "High" if blueprint["ease"] >= 4 else "Medium",
            "innovation_level": "High" if blueprint["innovation"] >= 5 else "Medium",
            "real_world_feasibility": "High" if blueprint["feasibility"] >= 4 else "Medium",
            "business_impact_score": impact_score,
            "practical_adoption_score": blueprint["adoption"],
            "simplicity_score": blueprint["simplicity"],
            "fit_channels": blueprint["fit"],
            "solution_summary": blueprint["summary"],
            "integration_hint": blueprint["systems"],
        }
        idea["weighted_score"] = _score_idea(idea)
        ideas.append(idea)

    ranked = sorted(ideas, key=lambda item: item["weighted_score"], reverse=True)
    return {
        "problem_summary": f"Primary domain detected: {label}. The problem is suitable for an AI workflow that improves execution speed without replacing core banking systems.",
        "ideas": ranked,
        "ranking_basis": ["Business impact", "Practical adoption", "Simplicity"],
        "recommended_idea_id": ranked[0]["id"],
        "generated_with": "heuristic",
    }


def _estimate_business_impact(selected_idea: Dict[str, Any], mode: str) -> Dict[str, str]:
    impact_score = selected_idea.get("business_impact_score", 4)
    stretch = 4 if mode == "advanced" else 0
    return {
        "call_reduction": f"{max(10, 12 + impact_score * 3)}-{min(40, 18 + impact_score * 4 + stretch)}%",
        "time_saved": f"{max(15, 20 + impact_score * 4)}-{min(60, 28 + impact_score * 5 + stretch)}% faster resolution time",
        "cost_savings": f"Estimated annual service cost reduction of 8-15% for the targeted process area",
        "efficiency_gain": f"{max(12, 15 + impact_score * 4)}-{min(55, 22 + impact_score * 5 + stretch)}% productivity improvement for frontline or ops users",
    }


def _build_pilot_metrics(selected_idea: Dict[str, Any]) -> List[str]:
    return [
        f"Pilot 1 KPI: Validate {selected_idea['title']} with one team, one process, and a measurable baseline.",
        "Pilot 2 KPI: Track adoption, decision accuracy, and manual effort removed before scaling.",
        "Pilot 3 KPI: Prove auditability with source-linked outputs and clear human override controls.",
    ]


def _build_prototype_plan(selected_idea: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "stack": ["Python FastAPI", "Simple HTML or React UI", "SQLite or SQL Server connector", "PDF or folder reader", "Light RAG or rules", "Local deployment"],
        "screens": [
            "Problem intake and idea generation screen",
            "Idea comparison and selection screen",
            "Roadmap and impact summary screen",
        ],
        "delivery_window": "Buildable in 2-4 hours with mock or sample banking data",
        "notes": [
            f"Use a single endpoint for generating ranked ideas around {selected_idea['title']}",
            "Keep persistence optional; local JSON state is enough for a demo",
            "Use streamed responses to show thinking stages in real time",
        ],
    }


def _build_advanced_architecture(selected_idea: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "experience_layer": ["Web dashboard", "CRM side panel", "Mobile or branch assistant surface"],
        "application_layer": ["FastAPI or Node backend", "workflow orchestrator", "policy engine", "prompt templates"],
        "ai_layer": ["LLM for structured generation", "RAG over policies, SOPs, and historical cases", "vector database for retrieval"],
        "data_layer": ["SQL Server or Oracle", "CRM APIs", "ticket logs", "PDF knowledge base", "audit event store"],
        "deployment": ["Local or on-prem runtime for sensitive data", "cloud burst for non-sensitive summarization", "API gateway and monitoring"],
        "non_functionals": ["role-based access", "prompt logging", "PII masking", "human approval for sensitive recommendations"],
    }


def build_solution(problem_statement: str, selected_idea_id: str, ideas: List[Dict[str, Any]], mode: str) -> Dict[str, Any]:
    selected_idea = next((idea for idea in ideas if idea["id"] == selected_idea_id), None)
    if not selected_idea:
        raise ValueError("Selected idea not found")

    mode_label = MODE_MAP.get(mode, MODE_MAP["roadmap"])
    business_impact = _estimate_business_impact(selected_idea, mode)

    solution = {
        "idea_summary": {
            "problem": _clean_problem(problem_statement),
            "selected_idea": selected_idea,
            "recommended_mode": mode_label,
        },
        "selected_mode": mode_label,
        "real_world_roadmap": {
            "where_it_fits": selected_idea.get("fit_channels", ["CRM", "Backend"]),
            "integration_points": {
                "systems": selected_idea.get("integration_hint", ["CRM", "SQL data source", "document repository"]),
                "apis_required": [
                    "Customer profile API",
                    "Case or ticket lookup API",
                    "Authentication and role API",
                    "Knowledge retrieval or document service API",
                ],
                "data_sources": ["SQL tables", "CRM records", "PDF SOPs", "interaction logs", "CSV or batch files"],
            },
            "implementation_phases": [
                {
                    "phase": "Phase 1: Pilot",
                    "goal": "Limited rollout for one product line or one service team",
                    "scope": "Use read-only integrations, human review, and 2-3 high-frequency journeys",
                    "success_metrics": _build_pilot_metrics(selected_idea),
                },
                {
                    "phase": "Phase 2: Internal adoption",
                    "goal": "Expand across service, ops, or fraud teams with team-level dashboards",
                    "scope": "Add workflow analytics, feedback capture, and more data connectors",
                    "success_metrics": [
                        "Agent adoption above 60% in target teams",
                        "Resolution time improvement sustained for 4-6 weeks",
                        "Manager confidence in AI suggestions with clear source traceability",
                    ],
                },
                {
                    "phase": "Phase 3: Full scale deployment",
                    "goal": "Embed into enterprise channels and operational governance",
                    "scope": "Integrate with CRM, backend orchestration, monitoring, and model governance",
                    "success_metrics": [
                        "Stable SLA adherence across channels",
                        "Audit-ready logs and approval controls in place",
                        "Measured business case translated into budgeted rollout",
                    ],
                },
            ],
            "operational_impact": {
                "teams": ["Call center", "Operations", "Fraud", "Customer support"],
                "process_improvement": f"Replaces fragmented lookup, manual triage, and ad hoc decisioning with a guided workflow around {selected_idea['title']}",
            },
            "business_impact": business_impact,
            "practical_feasibility": [
                "Uses existing banking systems as read-only sources before deeper integration",
                "Starts with narrow use cases so compliance and operations teams can validate outcomes safely",
                "Requires minimal disruption because the AI layer augments current staff workflows instead of replacing them",
            ],
            "risks": [
                "Integration delays if source systems lack stable APIs or clean identifiers",
                "Adoption risk if outputs are not explainable or if staff training is skipped",
                "Regulatory concerns around PII handling, audit trails, and model recommendations for sensitive journeys",
            ],
        },
        "solution_overview": {
            "positioning": selected_idea["solution_summary"],
            "why_now": "Banks already have enough operational and customer context; the missing layer is orchestration, retrieval, and decision support.",
            "business_case": selected_idea["business_impact"],
        },
        "demo_flow": [
            {
                "user_query": f"We are struggling with: {_clean_problem(problem_statement)}",
                "system_action": "The engine analyzes the problem, generates ranked ideas, and recommends the strongest option based on business impact and adoption.",
                "output": f"Top recommendation: {selected_idea['title']} with a phased roadmap and quantified impact.",
            },
            {
                "user_query": f"Proceed with {selected_idea['title']} in {mode_label}",
                "system_action": "The engine generates integration points, implementation phases, operational impact, and business value.",
                "output": "A board-ready plan is produced for demo, PPT, and video narration.",
            },
        ],
        "ppt_content": [
            {"slide": 1, "title": "Team & Project Overview", "content": f"Introduce the team and present {selected_idea['title']} as the chosen hackathon concept."},
            {"slide": 2, "title": "Problem Statement", "content": _clean_problem(problem_statement)},
            {"slide": 3, "title": "Opportunity Size", "content": f"Show the operational waste and upside: {selected_idea['business_impact']}"},
            {"slide": 4, "title": "Proposed AI Solution", "content": selected_idea['solution_summary']},
            {"slide": 5, "title": "Architecture", "content": "Cover channel entry points, orchestration layer, source systems, and human review controls."},
            {"slide": 6, "title": "AI Approach", "content": "Explain prompt templates, retrieval, workflow rules, and explainable outputs."},
            {"slide": 7, "title": "Prototype / Demo", "content": "Show problem input, idea ranking, mode selection, and generated roadmap."},
            {"slide": 8, "title": "Risks & Limitations", "content": "Address data quality, integration effort, compliance, and adoption constraints."},
            {"slide": 9, "title": "Implementation Plan", "content": "Walk through pilot, internal adoption, and enterprise rollout phases."},
            {"slide": 10, "title": "Business Value", "content": f"Summarize quantified gains: {business_impact['call_reduction']} call reduction potential and {business_impact['efficiency_gain']}."},
        ],
        "video_script": {
            "duration": "3 minutes",
            "script": [
                f"Problem: Banking teams still handle {_clean_problem(problem_statement).lower()} through fragmented systems and manual decisions.",
                f"Solution: {selected_idea['title']} acts as an AI-driven decision layer that recommends practical next actions using existing banking data.",
                "How it works: the user enters a problem, the engine ranks multiple ideas, then generates a real-world roadmap with integration points and rollout phases.",
                f"Impact: the bank can target {business_impact['call_reduction']} call reduction potential, faster resolution times, and stronger staff productivity without replacing core systems.",
            ],
        },
    }

    if mode == "basic_poc":
        solution["prototype"] = _build_prototype_plan(selected_idea)
    elif mode == "advanced":
        solution["architecture"] = _build_advanced_architecture(selected_idea)

    return solution