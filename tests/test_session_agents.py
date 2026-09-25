"""session_agents.py on hand-built session logs.

Each test writes a session log (and, where it needs one, the log's
<sessionId>/subagents/ directory) into a temporary directory from records
written here by hand, then runs the tool as a subprocess. The records follow
the shapes Claude Code writes: an Agent tool_use in an assistant record, its
tool_result with a top-level toolUseResult, task-notification and peer
hand-back user records, queue-operation copies, SendMessage calls, and
subagent transcripts with a .meta.json beside them. Some logs are written
with alphabetically sorted keys, as a resume rewrites them. Not released.

    python3 -m unittest discover -s tests
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
TOOL = KIT / "session_agents.py"
SESSION = "00000000-0000-4000-8000-000000000001"
SENTINEL = "SENTINEL-PROMPT-TEXT-do-not-print"


def ts(minute, second=0):
    return "2026-01-02T10:%02d:%02d.000Z" % (minute, second)


def agent_call(tid, when, desc, background, prompt="do the task", msg_id="msg_1",
               wire=False, agent_type="coder"):
    inp = {"subagent_type": agent_type, "description": desc, "prompt": prompt,
           "run_in_background": background}
    rec = {"parentUuid": None, "isSidechain": False,
           "message": {"model": "m", "id": msg_id, "type": "message",
                       "role": "assistant",
                       "content": [{"type": "tool_use", "id": tid,
                                    "name": "Agent", "input": inp}]},
           "type": "assistant", "uuid": "u-" + tid, "timestamp": when}
    if wire:
        rec["wireToolInputs"] = {tid: dict(inp)}
    return rec


def assistant_text(text, when, msg_id="msg_1"):
    return {"type": "assistant", "timestamp": when,
            "message": {"id": msg_id, "role": "assistant",
                        "content": [{"type": "text", "text": text}]}}


def result(tid, when, status, agent_id):
    text = ("Async agent launched successfully." if status == "async_launched"
            else "report delivered as a message")
    tur = {"status": status, "agentId": agent_id}
    if status == "async_launched":
        tur["outputFile"] = "/tmp/tasks/%s.output" % agent_id
    return {"type": "user", "timestamp": when,
            "message": {"role": "user",
                        "content": [{"type": "tool_result", "tool_use_id": tid,
                                     "content": [{"type": "text", "text": text}]}]},
            "toolUseResult": tur}


def denied(tid, when, text):
    return {"type": "user", "timestamp": when,
            "message": {"role": "user",
                        "content": [{"type": "tool_result", "tool_use_id": tid,
                                     "is_error": True, "content": text}]},
            "toolUseResult": text, "toolDenialKind": "permission-rule"}


def notice_text(agent_id, tid, status, summary):
    return ("<task-notification>\n<task-id>%s</task-id>\n<tool-use-id>%s</tool-use-id>\n"
            "<output-file>/tmp/tasks/%s.output</output-file>\n<status>%s</status>\n"
            "<summary>%s</summary>\n<result>last words of the agent</result>\n"
            "</task-notification>" % (agent_id, tid, agent_id, status, summary))


def notice(agent_id, tid, when, status, summary):
    return {"type": "user", "timestamp": when, "origin": {"kind": "task-notification"},
            "message": {"role": "user",
                        "content": notice_text(agent_id, tid, status, summary)}}


def queue_copy(when, content):
    return {"type": "queue-operation", "operation": "enqueue", "timestamp": when,
            "sessionId": SESSION, "content": content}


def handback(agent_id, when, body="final report"):
    wrapped = ("<agent-message from=\"%s\">\n[Subagent hand-back] %s\n</agent-message>"
               % (agent_id, body))
    return {"type": "user", "timestamp": when,
            "origin": {"kind": "peer", "from": agent_id, "senderTaskId": agent_id,
                       "handback": True, "body": "[Subagent hand-back] " + body},
            "message": {"role": "user", "content": wrapped}}


def send_message(tid, when, to):
    return {"type": "assistant", "timestamp": when,
            "message": {"id": "msg_s" + tid, "role": "assistant",
                        "content": [{"type": "tool_use", "id": tid, "name": "SendMessage",
                                     "input": {"to": to, "message": "carry on"}}]}}


def send_result(tid, when, to):
    return {"type": "user", "timestamp": when,
            "message": {"role": "user",
                        "content": [{"type": "tool_result", "tool_use_id": tid,
                                     "content": "sent"}]},
            "toolUseResult": {"success": True, "resumedAgentId": to}}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="session_agents_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.log = self.tmp / (SESSION + ".jsonl")

    def write_log(self, records, sort_keys=False, tail=""):
        lines = [json.dumps(r, sort_keys=sort_keys) for r in records]
        self.log.write_text("\n".join(lines) + "\n" + tail, encoding="utf-8")

    def write_transcript(self, agent_id, tid, records, desc="task"):
        sub = self.tmp / SESSION / "subagents"
        sub.mkdir(parents=True, exist_ok=True)
        (sub / ("agent-%s.jsonl" % agent_id)).write_text(
            "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        (sub / ("agent-%s.meta.json" % agent_id)).write_text(json.dumps(
            {"agentType": "coder", "description": desc, "toolUseId": tid,
             "requestShape": "background"}), encoding="utf-8")

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *args], cwd=str(self.tmp),
                              capture_output=True, text=True)

    def run_ok(self):
        p = self.run_tool(str(self.log))
        self.assertEqual(p.returncode, 0, "exit %d\nstdout:\n%s\nstderr:\n%s"
                         % (p.returncode, p.stdout, p.stderr))
        return p

    def block(self, out, tid):
        """The output block for one Agent call, found by its tool_use id."""
        parts = out.split("\nAgent call ")
        hits = [p for p in parts[1:] if tid in p.splitlines()[0]]
        self.assertEqual(len(hits), 1, "no single block for %s in:\n%s" % (tid, out))
        return hits[0]

    def field(self, block, name):
        for line in block.splitlines():
            s = line.strip()
            if s.startswith(name + ":"):
                return s[len(name) + 1:].strip()
        self.fail("no %r line in block:\n%s" % (name, block))


class SessionAgents(Base):
    def test_a_foreground_completed_native_order(self):
        tid = "toolu_A1"
        self.write_log([
            assistant_text("sending a pulse", ts(0), msg_id="msg_a"),
            agent_call(tid, ts(0, 1), "Pulse: read facts", False, msg_id="msg_a",
                       agent_type="pulse"),
            result(tid, ts(3), "completed", "aid0000000000000a"),
        ])
        p = self.run_ok()
        b = self.block(p.stdout, tid)
        self.assertIn(ts(0, 1), b.splitlines()[0])
        self.assertEqual(self.field(b, "type"), "pulse")
        self.assertEqual(self.field(b, "description"), "Pulse: read facts")
        self.assertEqual(self.field(b, "mode"), "foreground")
        self.assertTrue(self.field(b, "line").startswith("2"))
        self.assertEqual(self.field(b, "agentId"), "aid0000000000000a")
        self.assertEqual(self.field(b, "outcome"), "completed")
        self.assertEqual(self.field(b, "hand-backs"), "0")
        self.assertEqual(p.stdout.count("\nAgent call "), 1)
        self.assertIn("completed 1", p.stdout.splitlines()[-1])

    def test_b_background_notice_handback_sorted_keys_wire_inputs(self):
        tid, aid = "toolu_B1", "aid0000000000000b"
        text = notice_text(aid, tid, "completed", 'Agent "Build it" finished')
        hb = handback(aid, ts(9))
        self.write_log([
            agent_call(tid, ts(1), "Build it", True, wire=True),
            result(tid, ts(1, 2), "async_launched", aid),
            queue_copy(ts(9), hb["message"]["content"]),
            hb,
            queue_copy(ts(10), text),
            notice(aid, tid, ts(10, 1), "completed", 'Agent "Build it" finished'),
        ], sort_keys=True)
        p = self.run_ok()
        self.assertEqual(p.stdout.count("\nAgent call "), 1)
        b = self.block(p.stdout, tid)
        self.assertEqual(self.field(b, "mode"), "background")
        self.assertEqual(self.field(b, "agentId"), aid)
        self.assertEqual(self.field(b, "outcome"), "completed")
        self.assertEqual(self.field(b, "hand-backs"), "1 (%s)" % ts(9))
        self.assertEqual(self.field(b, "SendMessages"), "0")

    def test_c_failed_notice_with_transcript_last_activity(self):
        tid, aid = "toolu_C1", "aid0000000000000c"
        summary = ('Agent "Batch" failed: Agent terminated early due to an API error: '
                   "API Error: Can't reach the API server (EAI_AGAIN) (error type server_error)")
        self.write_log([
            agent_call(tid, ts(1), "Batch", True),
            result(tid, ts(1, 3), "async_launched", aid),
            notice(aid, tid, ts(30), "failed", summary),
        ])
        long_text = "Revert check matches; opening the PR now. " + "x" * 400
        self.write_transcript(aid, tid, [
            {"type": "user", "timestamp": ts(1, 4), "agentId": aid,
             "message": {"role": "user", "content": "the dispatch prompt"}},
            {"type": "assistant", "timestamp": ts(20), "agentId": aid,
             "message": {"role": "assistant",
                         "content": [{"type": "text", "text": long_text}]}},
            {"type": "assistant", "timestamp": ts(21), "agentId": aid,
             "message": {"role": "assistant",
                         "content": [{"type": "tool_use", "id": "toolu_x", "name": "Bash",
                                      "input": {"command": "true"}}]}},
            {"type": "user", "timestamp": ts(22), "agentId": aid,
             "message": {"role": "user",
                         "content": [{"type": "tool_result", "tool_use_id": "toolu_x",
                                      "content": "ok"}]}},
            {"type": "assistant", "timestamp": ts(29, 59), "agentId": aid,
             "isApiErrorMessage": True, "error": "server_error",
             "message": {"role": "assistant",
                         "content": [{"type": "text", "text": "API Error: EAI_AGAIN"}]}},
        ], desc="Batch")
        p = self.run_ok()
        b = self.block(p.stdout, tid)
        self.assertEqual(self.field(b, "outcome"), "failed: " + summary)
        self.assertEqual(self.field(b, "hand-backs"), "0")
        self.assertEqual(self.field(b, "last timestamp"), ts(29, 59))
        last_text = self.field(b, "last assistant text")
        self.assertTrue(last_text.startswith("Revert check matches"), last_text)
        self.assertLessEqual(len(last_text), 210)
        self.assertNotIn("x" * 300, p.stdout)
        self.assertEqual(self.field(b, "last tool_use"), "Bash at %s" % ts(21))
        self.assertEqual(self.field(b, "ends in API error"), "yes (server_error)")
        self.assertIn("failed 1", p.stdout.splitlines()[-1])

    def test_d_sendmessage_resume_second_handback(self):
        tid, aid, sid = "toolu_D1", "aid0000000000000d", "toolu_D2"
        self.write_log([
            agent_call(tid, ts(1), "Do it", True),
            result(tid, ts(1, 1), "async_launched", aid),
            handback(aid, ts(5), "first report"),
            notice(aid, tid, ts(5, 5), "completed", 'Agent "Do it" finished'),
            send_message(sid, ts(7), aid),
            send_result(sid, ts(7, 1), aid),
            handback(aid, ts(12), "second report"),
            notice(aid, sid, ts(12, 5), "completed", 'Agent "Do it" finished'),
        ])
        p = self.run_ok()
        b = self.block(p.stdout, tid)
        self.assertEqual(self.field(b, "hand-backs"), "2 (%s, %s)" % (ts(5), ts(12)))
        self.assertEqual(self.field(b, "SendMessages"), "1 (%s)" % ts(7))
        self.assertEqual(self.field(b, "outcome"), "completed")
        self.assertEqual(p.stdout.count("\nAgent call "), 1)

    def test_e_hook_denied_call(self):
        tid = "toolu_E1"
        err = ("Error: PreToolUse:Agent hook error: dispatch_guard: the dispatch "
               "lacks section Merge\nsecond line of the reason")
        self.write_log([
            agent_call(tid, ts(1), "Missing a section", True),
            denied(tid, ts(1, 1), err),
        ])
        p = self.run_ok()
        b = self.block(p.stdout, tid)
        self.assertEqual(self.field(b, "outcome"),
                         "denied: Error: PreToolUse:Agent hook error: dispatch_guard: "
                         "the dispatch lacks section Merge")
        self.assertNotIn("second line of the reason", p.stdout)
        self.assertIn("denied 1", p.stdout.splitlines()[-1])

    def test_f_truncated_log(self):
        tid, aid = "toolu_F1", "aid0000000000000f"
        self.write_log([
            agent_call(tid, ts(1), "Long job", True),
            result(tid, ts(1, 1), "async_launched", aid),
        ], tail='{"type": "user", "timestamp": "2026-01-02T10:05:00.000Z", "mess')
        p = self.run_ok()
        self.assertIn("line 3: not JSON (truncated or partial)", p.stdout)
        b = self.block(p.stdout, tid)
        self.assertEqual(self.field(b, "outcome"), "launched, no completion notice")
        self.assertIn("launched, no completion notice 1", p.stdout.splitlines()[-1])

    def test_g_log_ends_after_tool_use(self):
        tid, aid = "toolu_G1", "aid0000000000000g"
        self.write_log([agent_call(tid, ts(1), "Cut off", True)])
        self.write_transcript(aid, tid, [
            {"type": "assistant", "timestamp": ts(2), "agentId": aid,
             "message": {"role": "assistant",
                         "content": [{"type": "text", "text": "Starting."}]}},
        ], desc="Cut off")
        p = self.run_ok()
        b = self.block(p.stdout, tid)
        self.assertEqual(self.field(b, "outcome"), "no result")
        self.assertEqual(self.field(b, "agentId"), aid)
        self.assertEqual(self.field(b, "last timestamp"), ts(2))
        self.assertEqual(self.field(b, "ends in API error"), "no")
        self.assertIn("no result 1", p.stdout.splitlines()[-1])

    def test_h_prompt_never_printed(self):
        tid, aid = "toolu_H1", "aid0000000000000h"
        self.write_log([
            agent_call(tid, ts(1), "Secretive", True, prompt=SENTINEL + " body",
                       wire=True),
            result(tid, ts(1, 1), "async_launched", aid),
        ])
        self.write_transcript(aid, tid, [
            {"type": "user", "timestamp": ts(1, 2), "agentId": aid,
             "message": {"role": "user", "content": SENTINEL + " body"}},
        ], desc="Secretive")
        p = self.run_ok()
        self.assertIn(tid, p.stdout)
        self.assertNotIn(SENTINEL, p.stdout + p.stderr)

    def test_i_missing_file_and_usage(self):
        missing = self.tmp / "no-such-session.jsonl"
        p = self.run_tool(str(missing))
        self.assertEqual(p.returncode, 2)
        self.assertIn(str(missing), p.stderr)
        p = self.run_tool()
        self.assertEqual(p.returncode, 2)
        self.assertIn("usage", p.stderr.lower())

    def test_j_writes_nothing(self):
        tid, aid = "toolu_J1", "aid0000000000000j"
        self.write_log([
            agent_call(tid, ts(1), "Quiet", True),
            result(tid, ts(1, 1), "async_launched", aid),
        ], tail='{"partial')
        self.write_transcript(aid, tid, [
            {"type": "assistant", "timestamp": ts(2), "agentId": aid,
             "message": {"role": "assistant",
                         "content": [{"type": "text", "text": "Working."}]}},
        ])

        def snapshot():
            snap = {}
            for root, dirs, files in os.walk(str(self.tmp)):
                for name in dirs + files:
                    path = os.path.join(root, name)
                    st = os.stat(path)
                    digest = None
                    if os.path.isfile(path):
                        with open(path, "rb") as fh:
                            digest = hashlib.sha256(fh.read()).hexdigest()
                    snap[path] = (st.st_mode, st.st_size, st.st_mtime_ns, digest)
            return snap

        before = snapshot()
        p = self.run_ok()
        self.assertIn(tid, p.stdout)
        self.assertEqual(snapshot(), before)


if __name__ == "__main__":
    unittest.main()
