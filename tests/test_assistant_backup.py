"""
The assistant's backup chain, tested against a FAKE Gemini and a FAKE Groq that
run on this computer. Each test tells the fakes how to behave (answer, say
"busy", or be too slow) and checks which AI the student's answer came from.
No real AI is called and no key is needed.
"""
import json
import os
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BEHAVE = {}          # "gemini-main" / "gemini-lite" / "groq" / "groq-small"  ->  "ok" | "busy" | "slow" | "empty"
CALLS = []           # which fake was asked, in order


class FakeAI(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert "urllib" not in self.headers.get("User-Agent", "urllib"), \
            "Python's default User-Agent: Groq's Cloudflare blocks it (error 1010)"
        if self.path.startswith("/groq"):
            who = "groq-small" if body["model"] == "groq-small" else "groq"
        else:
            who = "gemini-lite" if "lite" in self.path else "gemini-main"
        CALLS.append(who)
        how = BEHAVE.get(who, "ok")
        if how == "slow":
            time.sleep(2)                                   # longer than the test's wait
        if how == "busy":
            return self.send(503, {"error": {"code": 503, "message": "high demand"}})
        text = "" if how == "empty" else f"answer from {who}"
        if who.startswith("groq"):
            assert body["messages"][0]["role"] == "system", "Groq wasn't given the rules"
            assert body["reasoning_format"] == "hidden", "Groq's thinking would show"
            self.send(200, {"choices": [{"message": {"content": text}}]})
        else:
            assert "system_instruction" in body, "Gemini wasn't given the rules"
            self.send(200, {"candidates": [{"content": {"parts": [{"text": text}]}}]})

    def send(self, code, data):
        raw = json.dumps(data).encode()
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass                                            # the caller already gave up (timeout)


class TestBackupChain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake = ThreadingHTTPServer(("127.0.0.1", 0), FakeAI)
        threading.Thread(target=cls.fake.serve_forever, daemon=True).start()
        port = cls.fake.server_address[1]
        cls.saved = dict(os.environ)                 # put the settings back afterwards
        os.environ.update({
            "GEMINI_API_KEY": "test-gemini", "GROQ_API_KEY": "test-groq",
            "AI_MODEL": "gemini-main", "AI_BACKUP_MODEL": "gemini-lite",
            "AI_GEMINI_URL": f"http://127.0.0.1:{port}/gemini/{{model}}",
            "AI_GROQ_URL": f"http://127.0.0.1:{port}/groq",
            "GROQ_MODEL": "groq-big", "GROQ_BACKUP_MODEL": "groq-small",
            "AI_ORDER": "gemini,groq",                   # most tests: Gemini first
            "AI_WAIT_SECONDS": "0.5",
        })
        os.environ.pop("AI_FAKE", None)
        import assistant
        cls.ai = assistant

    @classmethod
    def tearDownClass(cls):
        cls.fake.shutdown()
        os.environ.clear(); os.environ.update(cls.saved)

    def ask(self, **behave):
        BEHAVE.clear(); BEHAVE.update(behave); CALLS.clear()
        history = [{"role": "user", "parts": [{"text": "hi"}]},
                   {"role": "model", "parts": [{"text": "Hello!"}]}]
        return self.ai.ask_ai("rules", history, "What do I have tomorrow?")

    def test_main_model_answers(self):
        self.assertEqual(self.ask(), "answer from gemini-main")
        self.assertEqual(CALLS, ["gemini-main"])

    def test_busy_main_is_asked_once_more(self):
        """Google says 'busy' (503): ask the same model again, then the lighter one."""
        self.assertEqual(self.ask(**{"gemini-main": "busy"}), "answer from gemini-lite")
        self.assertEqual(CALLS, ["gemini-main", "gemini-main", "gemini-lite"])

    def test_slow_main_is_not_asked_again(self):
        """Google is too slow: don't wait for it twice, go straight to the lighter model."""
        self.assertEqual(self.ask(**{"gemini-main": "slow"}), "answer from gemini-lite")
        self.assertEqual(CALLS, ["gemini-main", "gemini-lite"])

    def test_groq_answers_when_gemini_is_down(self):
        self.assertEqual(self.ask(**{"gemini-main": "busy", "gemini-lite": "busy"}), "answer from groq")
        self.assertEqual(CALLS[-1], "groq")

    def test_groq_second_model(self):
        self.assertEqual(self.ask(**{"gemini-main": "busy", "gemini-lite": "slow", "groq": "busy"}),
                         "answer from groq-small")

    def test_groq_first_by_default(self):
        """The live default: Groq first, Gemini only if both Groq models fail."""
        os.environ.pop("AI_ORDER")
        try:
            self.assertEqual(self.ask(), "answer from groq")
            self.assertEqual(CALLS, ["groq"])
            self.assertEqual(self.ask(groq="busy", **{"groq-small": "busy"}), "answer from gemini-main")
            self.assertEqual(CALLS, ["groq", "groq-small", "gemini-main"])
        finally:
            os.environ["AI_ORDER"] = "gemini,groq"

    def test_empty_answer_moves_on(self):
        self.assertEqual(self.ask(**{"gemini-main": "empty"}), "answer from gemini-lite")

    def test_all_down_says_busy(self):
        with self.assertRaises(self.ai.Refused) as caught:
            self.ask(**{"gemini-main": "busy", "gemini-lite": "slow", "groq": "busy", "groq-small": "empty"})
        self.assertIn("busy", str(caught.exception))

    def test_only_groq_key(self):
        """With just a Groq key, the assistant still works (and Gemini isn't tried)."""
        key = os.environ.pop("GEMINI_API_KEY")
        try:
            self.assertTrue(self.ai.enabled())
            self.assertEqual(self.ask(), "answer from groq")
            self.assertEqual(CALLS, ["groq"])
        finally:
            os.environ["GEMINI_API_KEY"] = key


if __name__ == "__main__":
    unittest.main()
