"""
Ricart–Agrawala Mutual Exclusion Algorithm Implementation (Unit III: Synchronization)

Simulates three processes: P1, P2, and P3 competing for exclusive access to
a shared critical section: "model-weights-update".

Implements:
- Process states: RELEASED, WANTED, HELD
- Lamport logical clocks: L = max(L_local, L_received) + 1
- Deterministic tie-breaking priority: (timestamp, process_id)
- Deferred reply queues and immediate reply semantics
- Strict mutual exclusion and deadlock-free operation
"""

import time
import threading
from typing import Dict, List, Optional, Set, Any


class RAProcess:
    def __init__(self, pid: str):
        self.id = pid
        self.state: str = "RELEASED"  # RELEASED, WANTED, HELD
        self.clock: int = 0
        self.request_timestamp: Optional[int] = None
        self.pending_replies: Set[str] = set()
        self.deferred_queue: List[str] = []
        self.requests_sent: int = 0
        self.replies_sent: int = 0
        self.deferred_count: int = 0
        self.cs_entries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "state": self.state,
            "clock": self.clock,
            "request_timestamp": self.request_timestamp,
            "pending_replies": sorted(list(self.pending_replies)),
            "pending_reply_count": len(self.pending_replies),
            "deferred_queue": list(self.deferred_queue),
            "requests_sent": self.requests_sent,
            "replies_sent": self.replies_sent,
            "deferred_count": self.deferred_count,
            "cs_entries": self.cs_entries
        }


class RicartAgrawalaManager:
    RESOURCE_NAME = "model-weights-update"

    def __init__(self):
        self._lock = threading.Lock()
        self.processes: Dict[str, RAProcess] = {
            "P1": RAProcess("P1"),
            "P2": RAProcess("P2"),
            "P3": RAProcess("P3")
        }
        self.current_cs_holder: Optional[str] = None
        self.cs_entry_time: Optional[float] = None
        self.history: List[Dict[str, Any]] = []

        self._record_event(
            event_type="SYSTEM_INIT",
            sender="SYSTEM",
            receiver=None,
            clock=0,
            message="Ricart–Agrawala Mutual Exclusion initialized with processes P1, P2, P3."
        )

    def _record_event(
        self,
        event_type: str,
        sender: str,
        receiver: Optional[str],
        clock: int,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        event = {
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S", time.localtime()),
            "event_type": event_type,
            "sender": sender,
            "receiver": receiver,
            "clock": clock,
            "message": message,
            "details": details or {}
        }
        self.history.append(event)
        if len(self.history) > 200:
            self.history.pop(0)

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "resource_name": self.RESOURCE_NAME,
                "current_cs_holder": self.current_cs_holder,
                "cs_occupied": self.current_cs_holder is not None,
                "cs_entry_time": self.cs_entry_time,
                "processes": {pid: proc.to_dict() for pid, proc in sorted(self.processes.items())}
            }

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(reversed(self.history[-limit:]))

    def request_cs(self, process_id: str) -> Dict[str, Any]:
        """
        Process requests entry to the Critical Section.
        """
        with self._lock:
            if process_id not in self.processes:
                raise ValueError(f"Unknown process ID: {process_id}")

            proc = self.processes[process_id]
            if proc.state == "HELD":
                return {
                    "success": False,
                    "message": f"Process {process_id} already holds the Critical Section.",
                    "status": self.get_status()
                }
            if proc.state == "WANTED":
                return {
                    "success": False,
                    "message": f"Process {process_id} is already in WANTED state awaiting replies.",
                    "status": self.get_status()
                }

            # 1. Increment local Lamport clock
            proc.clock += 1
            proc.state = "WANTED"
            proc.request_timestamp = proc.clock
            req_ts = proc.request_timestamp

            # Initialize pending replies to all peers
            peers = [p for pid, p in self.processes.items() if pid != process_id]
            proc.pending_replies = {p.id for p in peers}
            proc.requests_sent += len(peers)

            self._record_event(
                event_type="REQUEST_CS",
                sender=process_id,
                receiver="ALL_PEERS",
                clock=proc.clock,
                message=f"Process {process_id} broadcast REQUEST(ts={req_ts}, pid={process_id}) to peers."
            )

            # 2. Peer message exchange
            for peer in peers:
                # Update peer's logical clock: L = max(L_local, L_received) + 1
                peer.clock = max(peer.clock, req_ts) + 1

                # Check if peer defers reply
                defer = False
                if peer.state == "HELD":
                    defer = True
                    reason = f"Peer {peer.id} is currently HELD in Critical Section."
                elif peer.state == "WANTED":
                    # Priority comparison: (request_timestamp, process_id)
                    # Lower value has higher priority
                    peer_priority = (peer.request_timestamp, peer.id)
                    req_priority = (req_ts, process_id)
                    if peer_priority < req_priority:
                        defer = True
                        reason = f"Peer {peer.id} has higher priority {peer_priority} < {req_priority}."

                if defer:
                    peer.deferred_queue.append(process_id)
                    peer.deferred_count += 1
                    self._record_event(
                        event_type="DEFERRED",
                        sender=peer.id,
                        receiver=process_id,
                        clock=peer.clock,
                        message=f"Process {peer.id} deferred REPLY to {process_id} ({reason})."
                    )
                else:
                    # Send immediate reply
                    peer.clock += 1
                    peer.replies_sent += 1
                    self._record_event(
                        event_type="REPLY",
                        sender=peer.id,
                        receiver=process_id,
                        clock=peer.clock,
                        message=f"Process {peer.id} sent immediate REPLY to {process_id}."
                    )
                    # Process receives reply: update clock
                    proc.clock = max(proc.clock, peer.clock) + 1
                    proc.pending_replies.discard(peer.id)

            # 3. If all replies received, enter Critical Section immediately
            entered_cs = False
            if len(proc.pending_replies) == 0:
                proc.state = "HELD"
                proc.cs_entries += 1
                self.current_cs_holder = process_id
                self.cs_entry_time = time.time()
                entered_cs = True
                self._record_event(
                    event_type="ENTER_CS",
                    sender=process_id,
                    receiver=None,
                    clock=proc.clock,
                    message=f"Process {process_id} acquired all replies and entered Critical Section ({self.RESOURCE_NAME})!"
                )

            return {
                "success": True,
                "process_id": process_id,
                "state": proc.state,
                "clock": proc.clock,
                "entered_cs": entered_cs,
                "pending_replies": sorted(list(proc.pending_replies))
            }

    def release_cs(self, process_id: str) -> Dict[str, Any]:
        """
        Process releases the Critical Section and sends deferred replies.
        """
        with self._lock:
            if process_id not in self.processes:
                raise ValueError(f"Unknown process ID: {process_id}")

            proc = self.processes[process_id]
            if proc.state != "HELD":
                raise ValueError(f"Process {process_id} cannot release Critical Section (state is {proc.state}, not HELD).")

            # Update process state to RELEASED
            proc.state = "RELEASED"
            proc.request_timestamp = None
            proc.clock += 1
            self.current_cs_holder = None
            self.cs_entry_time = None

            self._record_event(
                event_type="RELEASE_CS",
                sender=process_id,
                receiver=None,
                clock=proc.clock,
                message=f"Process {process_id} released Critical Section ({self.RESOURCE_NAME})."
            )

            # Flush deferred replies
            deferred_to_send = list(proc.deferred_queue)
            proc.deferred_queue.clear()

            new_cs_holder = None
            for waiter_id in deferred_to_send:
                waiter = self.processes.get(waiter_id)
                if not waiter:
                    continue

                # Process sends deferred reply
                proc.clock += 1
                proc.replies_sent += 1
                self._record_event(
                    event_type="REPLY_DEFERRED",
                    sender=process_id,
                    receiver=waiter_id,
                    clock=proc.clock,
                    message=f"Process {process_id} sent deferred REPLY to {waiter_id}."
                )

                # Waiter receives reply
                waiter.clock = max(waiter.clock, proc.clock) + 1
                waiter.pending_replies.discard(process_id)

                # If waiter now has all replies and is WANTED, it enters CS!
                if len(waiter.pending_replies) == 0 and waiter.state == "WANTED" and self.current_cs_holder is None:
                    waiter.state = "HELD"
                    waiter.cs_entries += 1
                    self.current_cs_holder = waiter.id
                    self.cs_entry_time = time.time()
                    new_cs_holder = waiter.id
                    self._record_event(
                        event_type="ENTER_CS",
                        sender=waiter.id,
                        receiver=None,
                        clock=waiter.clock,
                        message=f"Process {waiter.id} acquired remaining deferred reply and entered Critical Section ({self.RESOURCE_NAME})!"
                    )

            return {
                "success": True,
                "process_id": process_id,
                "deferred_replies_sent": deferred_to_send,
                "new_cs_holder": new_cs_holder,
                "current_cs_holder": self.current_cs_holder
            }

    def reset(self):
        with self._lock:
            self.processes = {
                "P1": RAProcess("P1"),
                "P2": RAProcess("P2"),
                "P3": RAProcess("P3")
            }
            self.current_cs_holder = None
            self.cs_entry_time = None
            self._record_event(
                event_type="SYSTEM_RESET",
                sender="SYSTEM",
                receiver=None,
                clock=0,
                message="Ricart–Agrawala system state was reset."
            )


# Global singleton instance for application use
ricart_agrawala_manager = RicartAgrawalaManager()
