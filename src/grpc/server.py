import os
import logging
from concurrent import futures
from datetime import datetime

import grpc

from src.mcp.server import BayesianMCPServer

logger = logging.getLogger(__name__)

_GRPC_PORT = int(os.environ.get("GRPC_PORT", "50051"))


class BayesianGrpcService:
    def __init__(self, mcp_server: BayesianMCPServer):
        self.mcp = mcp_server

    async def EvaluateCodeConfidence(self, request, context):
        result = await self.mcp._evaluate_code_confidence({"code": request.code, "language": request.language})
        from src.grpc.proto import bayesian_pb2
        return bayesian_pb2.ConfidenceResponse(
            confidence_score=result.get("confidence_score", 0),
            confidence_level=result.get("confidence_level", "low"),
            cyclomatic_complexity=result.get("complexity_metrics", {}).get("cyclomatic_complexity", 0),
            cognitive_complexity=result.get("complexity_metrics", {}).get("cognitive_complexity", 0),
        )

    async def RetrieveSimilarBugs(self, request, context):
        filters = {}
        if request.language:
            filters["language"] = request.language
        if request.severity:
            filters["severity"] = request.severity
        result = await self.mcp._retrieve_similar_bugs({"query": request.query, "limit": max(request.limit, 5), "filters": filters or None})
        from src.grpc.proto import bayesian_pb2
        bugs = []
        for r in result.get("results", []):
            bugs.append(bayesian_pb2.BugEntry(
                id=r.get("bug_id", ""), description=r.get("description", ""),
                root_cause=r.get("root_cause", ""), solution=r.get("solution", ""),
                language=r.get("language", ""), severity=r.get("severity", ""),
                relevance_score=r.get("similarity_score", 0),
            ))
        return bayesian_pb2.BugList(bugs=bugs, total=len(bugs))

    async def PredictComplexity(self, request, context):
        result = await self.mcp._predict_complexity({"code": request.code, "language": request.language})
        from src.grpc.proto import bayesian_pb2
        return bayesian_pb2.ComplexityResponse(
            cyclomatic=result.get("cyclomatic_complexity", 0),
            cognitive=result.get("cognitive_complexity", 0),
            maintainability_index=result.get("maintainability_index", 0),
            predicted_bug_probability=result.get("predicted_bug_probability", 0),
            evolution_trend=result.get("evolution_trend", "stable"),
        )

    async def ActiveInference(self, request, context):
        result = await self.mcp._active_inference({
            "current_state": request.current_state,
            "goal_state": request.goal_state,
            "available_actions": list(request.available_actions),
            "constraints": list(request.constraints),
        })
        from src.grpc.proto import bayesian_pb2
        return bayesian_pb2.InferenceResponse(
            recommended_action=result.get("recommended_action", ""),
            expected_free_energy=result.get("expected_free_energy", 0),
            action_probabilities=[p.get("probability", 0) for p in result.get("action_probabilities", [])],
            reasoning_chain=result.get("reasoning_chain", []),
            confidence=result.get("confidence", 0),
        )

    async def SemanticSearch(self, request, context):
        result = await self.mcp._semantic_search({
            "query": request.query,
            "memory_layers": list(request.layers) or ["medium_term", "long_term"],
            "limit": max(request.limit, 5),
        })
        from src.grpc.proto import bayesian_pb2
        results = []
        for r in result.get("results", []):
            results.append(bayesian_pb2.SearchResult(
                content=r.get("content", ""), layer=r.get("layer", ""),
                relevance_score=r.get("relevance_score", 0), importance=r.get("importance", 0),
            ))
        return bayesian_pb2.SearchResponse(results=results, total=len(results))


def serve_grpc(mcp_server: BayesianMCPServer):
    try:
        server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
        from src.grpc.proto import bayesian_pb2_grpc
        bayesian_pb2_grpc.add_BayesianServiceServicer_to_server(BayesianGrpcService(mcp_server), server)
        server.add_insecure_port(f"[::]:{_GRPC_PORT}")
        logger.info(f"gRPC server starting on port {_GRPC_PORT}")
        return server
    except ImportError:
        logger.warning("grpcio not installed. Run: pip install grpcio grpcio-tools")
        return None
