"""
Unit and integration tests for the Bully Election Algorithm (Unit III: Synchronization)
"""

import pytest
from gateway.election import BullyElectionManager


def test_initial_coordinator_is_highest_node():
    manager = BullyElectionManager()
    status = manager.get_status()
    # Initially all nodes (100, 200, 300) are alive, so 300 must be coordinator
    assert status["coordinator_id"] == 300
    assert status["coordinator_name"] == "Worker Gamma"
    assert status["alive_nodes_count"] == 3


def test_election_initiated_by_lowest_node():
    manager = BullyElectionManager()
    # Node 100 initiates election. Higher nodes (200, 300) respond and 300 wins
    result = manager.start_election(initiator_id=100)
    assert result["success"] is True
    assert result["coordinator_id"] == 300
    assert result["coordinator_name"] == "Worker Gamma"

    status = manager.get_status()
    assert status["coordinator_id"] == 300
    assert manager.nodes[300].is_coordinator is True
    assert manager.nodes[100].is_coordinator is False
    assert manager.nodes[200].is_coordinator is False


def test_coordinator_failure_and_new_election():
    manager = BullyElectionManager()
    # Fail coordinator (300)
    fail_result = manager.fail_node(300)
    assert fail_result["was_coordinator"] is True
    assert manager.current_coordinator_id is None

    # Now start election from Node 100
    result = manager.start_election(initiator_id=100)
    assert result["success"] is True
    # Highest alive node is now 200 (Worker Beta)
    assert result["coordinator_id"] == 200
    assert result["coordinator_name"] == "Worker Beta"

    status = manager.get_status()
    assert status["coordinator_id"] == 200


def test_cascading_failures_to_lowest_node():
    manager = BullyElectionManager()
    # Fail 300 and 200
    manager.fail_node(300)
    manager.fail_node(200)

    # Node 100 is only alive node; when election runs, Node 100 becomes coordinator
    result = manager.start_election(initiator_id=100)
    assert result["success"] is True
    assert result["coordinator_id"] == 100
    assert result["coordinator_name"] == "Worker Alpha"


def test_higher_id_node_recovery_reclaims_leadership():
    manager = BullyElectionManager()
    # Fail 300; 200 becomes coordinator
    manager.fail_node(300)
    manager.start_election(initiator_id=100)
    assert manager.current_coordinator_id == 200

    # Recover Node 300 with auto_elect=True
    recover_result = manager.recover_node(300, auto_elect=True)
    assert recover_result["coordinator_id"] == 300
    assert manager.current_coordinator_id == 300
    assert manager.nodes[300].is_coordinator is True


def test_all_nodes_failed_election_handling():
    manager = BullyElectionManager()
    manager.fail_node(100)
    manager.fail_node(200)
    manager.fail_node(300)

    result = manager.start_election()
    assert result["success"] is False
    assert result["coordinator_id"] is None
    assert manager.current_coordinator_id is None


def test_election_history_audit_trail():
    manager = BullyElectionManager()
    manager.fail_node(300)
    manager.start_election(initiator_id=100)

    history = manager.get_history(limit=50)
    assert len(history) > 0

    event_types = [e["event_type"] for e in history]
    assert "COORDINATOR_FAIL" in event_types
    assert "ELECTION_START" in event_types
    assert "COORDINATOR_ELECTED" in event_types
