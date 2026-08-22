#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.cognition.tree_of_thought import (
    TreeOfThought,
    TreeSearchConfig,
    TreeOfThoughtReasoner,
)
from src.core.cognition.graph_reasoning import (
    GraphReasoningEngine,
    Entity,
    Relation,
    RelationType,
)
from src.core.cognition.causal_reasoning import (
    CausalReasoningEngine,
)
from src.core.cognition.advanced_reasoning_coordinator import (
    AdvancedReasoningCoordinator,
    ReasoningStrategy,
)


class TestTreeOfThought:
    def test_create_tree(self):
        tree = TreeOfThought()
        root = tree.create_root("测试问题")
        assert root is not None
        assert root.id is not None

    def test_expand_node(self):
        tree = TreeOfThought()
        root = tree.create_root("测试问题")
        children = tree.expand_node(root.id, ["想法1", "想法2", "想法3"])
        assert len(children) == 3
        assert len(tree.nodes) == 4

    def test_evaluate_node(self):
        tree = TreeOfThought()
        root = tree.create_root("测试问题")
        tree.evaluate_node(root.id, 0.8)
        assert tree.nodes[root.id].value == 0.8

    def test_select_best_paths(self):
        tree = TreeOfThought()
        root = tree.create_root("测试问题")
        children = tree.expand_node(root.id, ["想法1", "想法2"])
        tree.evaluate_node(children[0].id, 0.8)
        tree.evaluate_node(children[1].id, 0.5)
        paths = tree.select_best_paths()
        assert len(paths) > 0


class TestGraphReasoning:
    def test_add_entity(self):
        engine = GraphReasoningEngine()
        entity = Entity(id="e1", name="测试实体", type="concept")
        engine.add_entity(entity)
        assert "e1" in engine.entities

    def test_add_relation(self):
        engine = GraphReasoningEngine()
        e1 = Entity(id="e1", name="A", type="concept")
        e2 = Entity(id="e2", name="B", type="concept")
        engine.add_entity(e1)
        engine.add_entity(e2)
        rel_id = engine.add_relation("e1", "e2", RelationType.IS_A)
        assert rel_id is not None
        assert rel_id in engine.relations

    def test_get_statistics(self):
        engine = GraphReasoningEngine()
        stats = engine.get_statistics()
        assert "entities_count" in stats
        assert "relations_count" in stats


class TestCausalReasoning:
    def test_add_variable(self):
        engine = CausalReasoningEngine()
        engine.add_variable("v1", "变量1")
        assert "v1" in engine.graph.variables

    def test_add_causal_relation(self):
        engine = CausalReasoningEngine()
        engine.add_variable("cause", "原因")
        engine.add_variable("effect", "结果")
        engine.add_causal_relation("cause", "effect", strength=0.8)
        assert len(engine.graph.relations) == 1

    def test_observe_variable(self):
        engine = CausalReasoningEngine()
        engine.add_variable("v1", "变量1")
        engine.observe("v1", True)
        assert engine.graph.variables["v1"].is_observed is True


class TestAdvancedReasoningCoordinator:
    def test_coordinator_initialization(self):
        coordinator = AdvancedReasoningCoordinator()
        assert coordinator is not None
        assert coordinator.tot_reasoner is not None
        assert coordinator.graph_engine is not None
        assert coordinator.causal_engine is not None

    async def test_solve_with_tot(self):
        coordinator = AdvancedReasoningCoordinator()
        result = await coordinator.solve_problem(
            "测试问题", strategy=ReasoningStrategy.TREE_OF_THOUGHT
        )
        assert result.strategy == "tree_of_thought"
        assert result.solution is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
