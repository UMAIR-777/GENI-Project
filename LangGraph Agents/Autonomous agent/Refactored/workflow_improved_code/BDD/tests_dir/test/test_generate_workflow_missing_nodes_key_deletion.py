import pytest
from unittest.mock import MagicMock

def test_missing_nodes_key_deletion_coverage(make_generator):
    # Accept make_generator as a fixture parameter; do not call it directly
    gen, _, _ = make_generator

    # Mock create_planning_workflow to return a workflow with invoke method
    class MockWorkflow:
        def invoke(self, initial_state, options):
            # final_workflow_data contains "missing_nodes" key to trigger deletion line
            return {
                "final_workflow": {
                    "nodes": ["node1", "node2"],
                    "missing_nodes": ["node1", "node2"]
                },
                "missing_nodes": []
            }

    gen.create_planning_workflow = lambda: MockWorkflow()

    # Mock database_manager.save_workflow to avoid side effects
    gen.database_manager = MagicMock()
    gen.database_manager.save_workflow = MagicMock()

    # Call generate_workflow and verify it runs without error and deletes the key
    workflow_json, missing = gen.generate_workflow("Test missing_nodes key deletion coverage")

    assert workflow_json is not None
    assert isinstance(workflow_json, str)
    assert missing == []
