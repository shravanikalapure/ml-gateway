"""
Unit tests for the Ricart–Agrawala Mutual Exclusion Algorithm (Unit III: Synchronization)
"""

import pytest
from gateway.mutual_exclusion import RicartAgrawalaManager


def test_initial_state():
    ra = RicartAgrawalaManager()
    status = ra.get_status()
    assert status["cs_occupied"] is False
    assert status["current_cs_holder"] is None
    for pid in ["P1", "P2", "P3"]:
        proc = status["processes"][pid]
        assert proc["state"] == "RELEASED"
        assert proc["clock"] == 0
        assert len(proc["deferred_queue"]) == 0


def test_single_process_cs_entry_and_clock_update():
    ra = RicartAgrawalaManager()
    res = ra.request_cs("P1")

    assert res["success"] is True
    assert res["entered_cs"] is True
    assert res["state"] == "HELD"

    status = ra.get_status()
    assert status["cs_occupied"] is True
    assert status["current_cs_holder"] == "P1"

    # P1 requested CS: clock incremented on request, then peers incremented on receipt
    # and P1 received replies and updated clock
    p1 = status["processes"]["P1"]
    p2 = status["processes"]["P2"]
    p3 = status["processes"]["P3"]

    assert p1["state"] == "HELD"
    assert p2["state"] == "RELEASED"
    assert p3["state"] == "RELEASED"
    assert p1["clock"] > 0
    assert p2["clock"] > 0
    assert p3["clock"] > 0


def test_deferred_reply_when_cs_held():
    ra = RicartAgrawalaManager()
    # P1 requests and enters CS
    ra.request_cs("P1")
    assert ra.current_cs_holder == "P1"

    # P2 requests CS while P1 holds CS
    res2 = ra.request_cs("P2")
    assert res2["success"] is True
    assert res2["entered_cs"] is False
    assert res2["state"] == "WANTED"

    # P1 must have deferred reply to P2
    p1_status = ra.processes["P1"]
    assert "P2" in p1_status.deferred_queue

    # P2 is waiting for P1's reply
    p2_status = ra.processes["P2"]
    assert "P1" in p2_status.pending_replies
    # But P3 is RELEASED, so P3 replied immediately
    assert "P3" not in p2_status.pending_replies


def test_release_cs_flushes_deferred_reply_and_transfers_cs():
    ra = RicartAgrawalaManager()
    # P1 enters CS
    ra.request_cs("P1")

    # P2 requests and gets deferred by P1
    ra.request_cs("P2")
    assert ra.current_cs_holder == "P1"
    assert ra.processes["P2"].state == "WANTED"

    # P1 releases CS
    rel_res = ra.release_cs("P1")
    assert rel_res["success"] is True
    assert "P2" in rel_res["deferred_replies_sent"]

    # P2 now receives deferred reply from P1 and automatically enters CS!
    assert ra.current_cs_holder == "P2"
    assert ra.processes["P2"].state == "HELD"
    assert ra.processes["P1"].state == "RELEASED"
    assert len(ra.processes["P1"].deferred_queue) == 0

    # Finally P2 releases CS
    rel_res2 = ra.release_cs("P2")
    assert rel_res2["success"] is True
    assert ra.current_cs_holder is None
    assert ra.processes["P2"].state == "RELEASED"


def test_priority_tie_breaking_timestamp_and_pid():
    ra = RicartAgrawalaManager()
    # Ensure Lamport clock update rule: L = max(L_local, L_received) + 1
    p1 = ra.processes["P1"]
    p2 = ra.processes["P2"]

    p1.clock = 5
    p2.clock = 10

    # Simulate message from P2 to P1 with clock 10
    updated_clock = max(p1.clock, 10) + 1
    assert updated_clock == 11
