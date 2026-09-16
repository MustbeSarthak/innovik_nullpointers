"""LangGraph orchestration for the multi-agent risk evaluation."""

from typing import Any

from langgraph.graph import END, START, StateGraph

from backend.agents.risk.aggregator import aggregate_risks
from backend.agents.risk.allergy_agent import evaluate_allergies
from backend.agents.risk.condition_agent import evaluate_conditions
from backend.agents.risk.history_agent import evaluate_history
from backend.agents.risk.medication_agent import evaluate_medications
from backend.agents.risk.models import RiskAssessment, RiskRequest, RiskResult
from backend.agents.risk.state import RiskGraphState, RiskInput, VitalReading
from backend.agents.risk.symptom_agent import evaluate_symptoms
from backend.agents.risk.vital_agent import evaluate_vitals
from backend.core.exceptions import MemoryAgentError
from backend.integrations.acno import AcnoProvider, build_acno_context
from backend.memory.agent import MemoryAgent
from backend.memory.schemas import MedicalContext
from backend.schemas.assessment import HealthAssessmentRead


class RiskEvaluationAgent:
    """Reusable facade for patient-scoped risk evaluation."""

    def __init__(self, memory_agent: MemoryAgent | None = None, acno_provider: AcnoProvider | None = None) -> None:
        self.memory_agent = memory_agent or MemoryAgent()
        self.graph = build_risk_graph(self.memory_agent, acno_provider)

    def evaluate(
        self,
        patient_id: int,
        *,
        assessment: HealthAssessmentRead | None,
        query: str,
        vitals: list[VitalReading] | None = None,
        recent_vitals: list[dict[str, Any]] | None = None,
    ) -> RiskAssessment:
        """Evaluate only the supplied patient's assessment and retrieved memory."""
        result = self.graph.invoke(
            {
                "patient_id": patient_id,
                "query": query,
                "assessment": assessment,
                "vitals": vitals or [],
                "recent_vitals": recent_vitals or [],
            }
        )
        response = result.get("response")
        if not isinstance(response, RiskAssessment):
            raise MemoryAgentError("risk graph returned an invalid assessment")
        return response

    def invoke(self, request: RiskRequest, *, patient_id: int, assessment: HealthAssessmentRead | None) -> RiskAssessment:
        """Run a validated request for a known authenticated patient."""
        vitals = [VitalReading.model_validate(item) for item in request.vitals]
        return self.evaluate(patient_id, assessment=assessment, query=request.query, vitals=vitals)


def build_risk_graph(memory_agent: MemoryAgent | None = None, acno_provider: AcnoProvider | None = None) -> Any:
    """Compile the risk workflow with modular specialist execution."""
    memory = memory_agent or MemoryAgent()

    def load_patient_context(state: RiskGraphState) -> dict[str, Any]:
        return {
            "risk_input": RiskInput(
                patient_id=state["patient_id"],
                assessment=state.get("assessment"),
                medical_context=MedicalContext(
                    patient_id=state["patient_id"], query=state["query"], available=False, status="pending"
                ),
                vitals=[VitalReading.model_validate(item) for item in state.get("vitals", [])],
                recent_vitals=list(state.get("recent_vitals", []))[:10],
            )
        }

    def retrieve_medical_memory(state: RiskGraphState) -> dict[str, Any]:
        risk_input = state["risk_input"]
        context = memory.retrieve_context(risk_input.patient_id, state["query"])
        return {"medical_context": context, "risk_input": risk_input.model_copy(update={"medical_context": context})}

    def run_specialists(state: RiskGraphState) -> dict[str, Any]:
        data = state["risk_input"]
        return {"specialist_results": [
            evaluate_history(data),
            evaluate_symptoms(data),
            evaluate_medications(data),
            evaluate_allergies(data),
            evaluate_conditions(data),
            evaluate_vitals(data),
        ]}

    def aggregate(state: RiskGraphState) -> dict[str, Any]:
        assessment = aggregate_risks(state["patient_id"], state["specialist_results"])
        if acno_provider is None:
            from backend.integrations.acno import AcnoAIProvider
            provider: AcnoProvider = AcnoAIProvider()
        else:
            provider = acno_provider
        data = state["risk_input"]
        current_vitals = {item.name: item.value for item in data.vitals}
        context = build_acno_context(
            state["patient_id"], data.assessment, current_vitals, data.recent_vitals, state["medical_context"]
        )
        try:
            ai_result = provider.analyze(context)
        except Exception:
            ai_result = None
        if ai_result is not None:
            from backend.agents.risk.common import level_for_score
            from backend.agents.risk.models import RiskEvidence, RiskFinding
            ai_score = max(assessment.score, ai_result.score)
            ai_finding = RiskFinding(
                agent="acno_ai",
                risk_level=level_for_score(ai_result.score),
                score=ai_result.score,
                finding="Acno AI reported additional risk indicators for review.",
                evidence=[RiskEvidence(source="acno_ai", detail=indicator) for indicator in ai_result.detected_indicators],
                confidence=0.5,
                reason=ai_result.reason,
            )
            assessment = assessment.model_copy(update={
                "score": ai_score,
                "overall_risk": level_for_score(ai_score),
                "findings": assessment.findings + [ai_finding],
                "evidence": assessment.evidence + ai_finding.evidence,
                "detected_indicators": list(dict.fromkeys(ai_result.detected_indicators)),
                "escalation_required": assessment.score >= 70 or ai_result.escalation_required,
                "ai_provider": "acno_ai",
            })
        return {"final_assessment": assessment}

    def validate_and_respond(state: RiskGraphState) -> dict[str, Any]:
        assessment = state.get("final_assessment")
        if not isinstance(assessment, RiskAssessment):
            raise MemoryAgentError("risk graph produced no valid aggregate")
        return {"response": assessment}

    graph = StateGraph(RiskGraphState)
    graph.add_node("load_patient_context", load_patient_context)
    graph.add_node("retrieve_medical_memory", retrieve_medical_memory)
    graph.add_node("run_specialized_agents", run_specialists)
    graph.add_node("risk_aggregator", aggregate)
    graph.add_node("validate_result", validate_and_respond)
    graph.add_edge(START, "load_patient_context")
    graph.add_edge("load_patient_context", "retrieve_medical_memory")
    graph.add_edge("retrieve_medical_memory", "run_specialized_agents")
    graph.add_edge("run_specialized_agents", "risk_aggregator")
    graph.add_edge("risk_aggregator", "validate_result")
    graph.add_edge("validate_result", END)
    return graph.compile()
