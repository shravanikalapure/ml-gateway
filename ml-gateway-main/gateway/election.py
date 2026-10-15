"""
Bully Election Algorithm Implementation (Unit III: Synchronization)

Simulates three nodes:
- Node 100: Worker Alpha
- Node 200: Worker Beta
- Node 300: Worker Gamma

Implements ELECTION, ANSWER (OK), and COORDINATOR message flow,
coordinator failure detection, and node recovery with coordinator reclamation.
"""

import time
import threading
from typing import Dict, List, Optional, Any


class ElectionNode:
    def __init__(self, node_id: int, name: str, is_alive: bool = True):
        self.id = node_id
        self.name = name
        self.is_alive = is_alive
        self.is_coordinator = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "is_alive": self.is_alive,
            "is_coordinator": self.is_coordinator
        }


class BullyElectionManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.nodes: Dict[int, ElectionNode] = {
            100: ElectionNode(100, "Worker Alpha", is_alive=True),
            200: ElectionNode(200, "Worker Beta", is_alive=True),
            300: ElectionNode(300, "Worker Gamma", is_alive=True),
        }
        # Initially, highest alive node (300) is coordinator
        self.current_coordinator_id: Optional[int] = 300
        self.nodes[300].is_coordinator = True
        self.election_state: str = "IDLE"  # IDLE, IN_PROGRESS, COMPLETED
        self.history: List[Dict[str, Any]] = []

        self._record_event(
            event_type="SYSTEM_INIT",
            sender_id=300,
            receiver_id=None,
            message="Bully Election System initialized. Initial coordinator: Node 300 (Worker Gamma)."
        )

    def _record_event(
        self,
        event_type: str,
        sender_id: Optional[int],
        receiver_id: Optional[int],
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        event = {
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S", time.localtime()),
            "event_type": event_type,
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "message": message,
            "details": details or {}
        }
        self.history.append(event)
        if len(self.history) > 200:
            self.history.pop(0)

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            coord_name = (
                self.nodes[self.current_coordinator_id].name
                if self.current_coordinator_id and self.current_coordinator_id in self.nodes
                else "None"
            )
            return {
                "coordinator_id": self.current_coordinator_id,
                "coordinator_name": coord_name,
                "election_state": self.election_state,
                "nodes": [node.to_dict() for node in sorted(self.nodes.values(), key=lambda n: n.id)],
                "alive_nodes_count": sum(1 for n in self.nodes.values() if n.is_alive),
                "total_nodes_count": len(self.nodes)
            }

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(reversed(self.history[-limit:]))

    def fail_node(self, node_id: int) -> Dict[str, Any]:
        with self._lock:
            if node_id not in self.nodes:
                raise ValueError(f"Unknown node ID: {node_id}")

            node = self.nodes[node_id]
            node.is_alive = False
            was_coord = (self.current_coordinator_id == node_id)
            if was_coord:
                node.is_coordinator = False
                self.current_coordinator_id = None
                self._record_event(
                    event_type="COORDINATOR_FAIL",
                    sender_id=node_id,
                    receiver_id=None,
                    message=f"Coordinator Node {node_id} ({node.name}) failed! Election required."
                )
            else:
                self._record_event(
                    event_type="NODE_FAIL",
                    sender_id=node_id,
                    receiver_id=None,
                    message=f"Node {node_id} ({node.name}) marked as failed (offline)."
                )

            return {
                "node_id": node_id,
                "is_alive": False,
                "was_coordinator": was_coord,
                "current_coordinator_id": self.current_coordinator_id
            }

    def recover_node(self, node_id: int, auto_elect: bool = True) -> Dict[str, Any]:
        with self._lock:
            if node_id not in self.nodes:
                raise ValueError(f"Unknown node ID: {node_id}")

            node = self.nodes[node_id]
            node.is_alive = True
            self._record_event(
                event_type="NODE_RECOVER",
                sender_id=node_id,
                receiver_id=None,
                message=f"Node {node_id} ({node.name}) recovered and is back online."
            )

        if auto_elect:
            # Under Bully Algorithm, when a node recovers (especially a higher ID node),
            # it initiates an election to claim leadership.
            return self.start_election(initiator_id=node_id)

        return self.get_status()

    def start_election(self, initiator_id: Optional[int] = None) -> Dict[str, Any]:
        with self._lock:
            alive_nodes = [n for n in self.nodes.values() if n.is_alive]
            if not alive_nodes:
                self.current_coordinator_id = None
                for n in self.nodes.values():
                    n.is_coordinator = False
                self.election_state = "IDLE"
                self._record_event(
                    event_type="ELECTION_ERROR",
                    sender_id=initiator_id,
                    receiver_id=None,
                    message="Election failed: No alive nodes available in the cluster."
                )
                return {
                    "success": False,
                    "coordinator_id": None,
                    "message": "No alive nodes available."
                }

            if initiator_id is not None:
                if initiator_id not in self.nodes:
                    raise ValueError(f"Unknown initiator node ID: {initiator_id}")
                if not self.nodes[initiator_id].is_alive:
                    raise ValueError(f"Initiator Node {initiator_id} is currently offline and cannot initiate.")
                initiator = self.nodes[initiator_id]
            else:
                # Default initiator: lowest alive node to demonstrate message cascade
                initiator = min(alive_nodes, key=lambda n: n.id)

            self.election_state = "IN_PROGRESS"
            self._record_event(
                event_type="ELECTION_START",
                sender_id=initiator.id,
                receiver_id=None,
                message=f"Node {initiator.id} ({initiator.name}) initiated Bully Election."
            )

            # Bully algorithm message sequence:
            # 1. Initiator sends ELECTION to all higher IDs in the system
            current_caller = initiator
            rounds = []

            while True:
                higher_system_nodes = sorted(
                    [n for n in self.nodes.values() if n.id > current_caller.id],
                    key=lambda n: n.id
                )
                higher_alive = [n for n in higher_system_nodes if n.is_alive]

                round_info = {
                    "caller_id": current_caller.id,
                    "higher_system_nodes": [n.id for n in higher_system_nodes],
                    "higher_alive_nodes": [n.id for n in higher_alive],
                    "responses": []
                }

                for higher_node in higher_system_nodes:
                    if higher_node.is_alive:
                        self._record_event(
                            event_type="ELECTION",
                            sender_id=current_caller.id,
                            receiver_id=higher_node.id,
                            message=f"Node {current_caller.id} sent ELECTION message to higher Node {higher_node.id}."
                        )
                        # Higher alive node answers OK
                        self._record_event(
                            event_type="ANSWER",
                            sender_id=higher_node.id,
                            receiver_id=current_caller.id,
                            message=f"Node {higher_node.id} answered OK to Node {current_caller.id} and took over election."
                        )
                        round_info["responses"].append({"from": higher_node.id, "status": "OK"})
                    else:
                        self._record_event(
                            event_type="ELECTION",
                            sender_id=current_caller.id,
                            receiver_id=higher_node.id,
                            message=f"Node {current_caller.id} sent ELECTION to Node {higher_node.id} (Timed out: Node {higher_node.id} is down)."
                        )
                        round_info["responses"].append({"from": higher_node.id, "status": "TIMEOUT"})

                rounds.append(round_info)

                if higher_alive:
                    # The highest available higher node takes over next
                    highest_candidate = max(higher_alive, key=lambda n: n.id)
                    if highest_candidate.id == current_caller.id:
                        winner = highest_candidate
                        break
                    # Continue cascade with the highest candidate
                    current_caller = highest_candidate
                    if not [n for n in self.nodes.values() if n.id > current_caller.id]:
                        winner = current_caller
                        break
                else:
                    # No higher alive node responded; current_caller wins!
                    winner = current_caller
                    break

            # Winner broadcasts COORDINATOR message to all other alive nodes
            for other_node in sorted(alive_nodes, key=lambda n: n.id):
                if other_node.id != winner.id:
                    self._record_event(
                        event_type="COORDINATOR",
                        sender_id=winner.id,
                        receiver_id=other_node.id,
                        message=f"Node {winner.id} broadcast COORDINATOR announcement to Node {other_node.id}."
                    )

            # Update state
            for n in self.nodes.values():
                n.is_coordinator = (n.id == winner.id)

            self.current_coordinator_id = winner.id
            self.election_state = "COMPLETED"

            self._record_event(
                event_type="COORDINATOR_ELECTED",
                sender_id=winner.id,
                receiver_id=None,
                message=f"Node {winner.id} ({winner.name}) successfully declared as the new COORDINATOR."
            )

            return {
                "success": True,
                "initiator_id": initiator.id,
                "coordinator_id": winner.id,
                "coordinator_name": winner.name,
                "rounds": rounds
            }


# Global singleton instance for application use
bully_election_manager = BullyElectionManager()
