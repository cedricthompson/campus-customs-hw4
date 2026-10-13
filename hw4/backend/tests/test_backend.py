"""Backend tests for Campus Customs. No AI calls, no extra dependencies.

Run from backend/:  .venv/bin/python -m unittest discover tests -v

Tests that write to the database use a temporary copy, so the real
data/campus_customs.db is never changed.
"""

import atexit
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import audit  # noqa: E402
import db  # noqa: E402

# Tests must never write to the real output/audit_trail.json.
_AUDIT_TMP = tempfile.mkdtemp(prefix="audit-test-")
audit.AUDIT_PATH = Path(_AUDIT_TMP) / "audit_trail.json"
atexit.register(shutil.rmtree, _AUDIT_TMP, ignore_errors=True)
from models import AgentOutput, ChatRequest, ChatTurn, ProductDetails, SizeStock  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from pydantic_ai import ModelRetry  # noqa: E402
from pydantic_ai.messages import ModelRequest, ToolReturnPart, UserPromptPart  # noqa: E402

import tools  # noqa: E402


class CategoryTests(unittest.TestCase):
    def test_every_product_has_a_real_category(self):
        with db.get_db() as conn:
            types = [r[0] for r in conn.execute("SELECT garment_type FROM catalogue")]
        cats = {db.category_for(t) for t in types}
        self.assertNotIn("Other", cats)
        self.assertEqual(cats, set(db.CATEGORIES))


class SearchTests(unittest.TestCase):
    def test_blue_includes_navy_and_royal(self):
        names = {c for p in tools.search_products(color="blue", in_stock_only=False).products for c in p.colors}
        self.assertTrue(any("navy" in c for c in names))

    def test_grey_equals_gray(self):
        a = tools.search_products(color="grey")
        b = tools.search_products(color="gray")
        self.assertEqual(a.total_in_stock, b.total_in_stock)
        self.assertGreater(a.total_in_stock, 0)

    def test_category_words_shoppers_use(self):
        self.assertEqual(tools.search_products(category="tees").total_including_sold_out, 25)
        self.assertEqual(tools.search_products(category="quarter zip").total_including_sold_out, 11)
        self.assertEqual(tools.search_products(category="Hoodies").total_including_sold_out, 27)

    def test_sort_orders(self):
        low = [p.price for p in tools.search_products(category="Hoodies", sort="price_low").products]
        high = [p.price for p in tools.search_products(category="Hoodies", sort="price_high").products]
        self.assertEqual(low, sorted(low))
        self.assertEqual(high, sorted(high, reverse=True))

    def test_size_filter_only_returns_sizes_in_stock(self):
        for p in tools.search_products(category="Hoodies", size="XL").products:
            self.assertIn("XL", p.sizes_in_stock)

    def test_no_match_gives_real_alternatives(self):
        r = tools.search_products(category="Hoodies", color="pink")
        self.assertEqual(r.total_including_sold_out, 0)
        self.assertEqual(r.relaxed_filters, ["color"])
        self.assertTrue(r.alternatives)
        self.assertTrue(all(a.category == "Hoodies" for a in r.alternatives))

    def test_unknown_item_gives_one_pick_per_category(self):
        r = tools.search_products(garment_type="sneakers")
        self.assertEqual(r.relaxed_filters, ["all"])
        self.assertEqual(len({a.category for a in r.alternatives}), len(r.alternatives))

    def test_similar_products_excludes_itself_and_stays_in_category(self):
        sims = tools.similar_products("basic-hoodie-big-yale")
        self.assertTrue(sims)
        self.assertTrue(all(s.product_id != "basic-hoodie-big-yale" and s.category == "Hoodies" for s in sims))

    def test_stock_statuses(self):
        self.assertEqual(tools.check_stock("Baseball Left Chest Crewneck", "XL").status, "sold_out")
        self.assertEqual(tools.check_stock("davenport crewneck", "medium").status, "in_stock")

    def test_unknown_product_ids_are_dropped_from_cards(self):
        cards = tools.product_cards(["basic-hoodie-big-yale", "not-a-real-product"])
        self.assertEqual([c.product_id for c in cards], ["basic-hoodie-big-yale"])


class ValidationTests(unittest.TestCase):
    def test_blank_and_control_only_messages_rejected(self):
        for bad in ["", "   ", "\x00\x07"]:
            with self.assertRaises(ValidationError):
                ChatRequest(message=bad)

    def test_message_is_cleaned(self):
        self.assertEqual(ChatRequest(message="  hi\x07 there ").message, "hi there")

    def test_too_long_message_rejected(self):
        with self.assertRaises(ValidationError):
            ChatRequest(message="a" * 2001)

    def test_agent_output_ids_deduped_and_capped(self):
        out = AgentOutput(reply=" ok ", product_ids=["a", "a", "b", "c", "d", "e", "f", "g"])
        self.assertEqual(out.product_ids, ["a", "b", "c", "d", "e", "f"])
        self.assertEqual(out.reply, "ok")

    def test_blank_agent_reply_rejected(self):
        with self.assertRaises(ValidationError):
            AgentOutput(reply="  ")


class AgentGuardTests(unittest.TestCase):
    """The output validator that blocks invented prices, discounts, and product ids."""

    @classmethod
    def setUpClass(cls):
        import agent  # needs backend/.env, but makes no API call

        cls.agent = agent

    def ctx(self, tool_content, user_text="hi", viewing=None):
        msgs = [
            ModelRequest(parts=[UserPromptPart(content=user_text)]),
            ModelRequest(parts=[ToolReturnPart(tool_name="search_products", content=tool_content, tool_call_id="1")]),
        ]
        deps = SimpleNamespace(viewing_product=viewing)
        return SimpleNamespace(messages=msgs, deps=deps)

    def test_invented_price_is_rejected(self):
        ctx = self.ctx({"products": [{"product_id": "x", "price": 58.0}]})
        with self.assertRaises(ModelRetry):
            self.agent.grounded_in_catalogue(ctx, AgentOutput(reply="It's only $39!"))

    def test_real_price_passes(self):
        ctx = self.ctx({"products": [{"product_id": "x", "price": 58.0}]})
        out = self.agent.grounded_in_catalogue(ctx, AgentOutput(reply="It's $58.", product_ids=["x"]))
        self.assertEqual(out.product_ids, ["x"])

    def test_price_the_shopper_typed_may_be_repeated(self):
        ctx = self.ctx({"products": []}, user_text="anything under $60?")
        self.agent.grounded_in_catalogue(ctx, AgentOutput(reply="Here's what's under $60."))

    def test_discount_claim_is_rejected(self):
        ctx = self.ctx({"products": [{"product_id": "x", "price": 58.0}]})
        with self.assertRaises(ModelRetry):
            self.agent.grounded_in_catalogue(ctx, AgentOutput(reply="Use promo code BULLDOG for 20% off!"))

    def test_ids_no_tool_returned_are_dropped(self):
        ctx = self.ctx({"products": [{"product_id": "x", "price": 58.0}]})
        out = self.agent.grounded_in_catalogue(ctx, AgentOutput(reply="ok", product_ids=["x", "made-up"]))
        self.assertEqual(out.product_ids, ["x"])

    def test_current_page_product_counts_as_known(self):
        viewing = ProductDetails(
            product_id="p", name="P", garment_type="hoodie", description="d", colors=[], price=68.0,
            stock_by_size=[SizeStock(size="M", quantity=1, sold_out=False)], sizes_in_stock=["M"], total_stock=1,
        )
        ctx = self.ctx({}, viewing=viewing)
        out = self.agent.grounded_in_catalogue(ctx, AgentOutput(reply="This one is $68.", product_ids=["p"]))
        self.assertEqual(out.product_ids, ["p"])

    def test_history_is_trimmed(self):
        turns = [ChatTurn(role="user" if i % 2 == 0 else "assistant", content="x" * 1000) for i in range(30)]
        kept = self.agent.trim_history(turns)
        self.assertLessEqual(len(kept), self.agent.HISTORY_MAX_MESSAGES)
        self.assertLessEqual(sum(len(t.content) for t in kept), self.agent.HISTORY_MAX_TOTAL_CHARS)
        self.assertEqual(kept[0].role, "user")


class HistoryIsolationTests(unittest.TestCase):
    """Saved chats belong to one customer only. Uses a temporary copy of the database."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.real_path = db.DB_PATH
        db.DB_PATH = Path(self.tmp.name) / "test.db"
        shutil.copy(self.real_path, db.DB_PATH)
        import history

        self.history = history

    def tearDown(self):
        db.DB_PATH = self.real_path
        self.tmp.cleanup()

    def test_each_customer_sees_only_their_messages(self):
        with db.get_db(write=True) as conn:
            conn.execute("DELETE FROM chat_messages")
        self.history.save_exchange(1, "A's secret question", "reply to A", [])
        self.history.save_exchange(3, "B's question", "reply to B", [])
        a = [m.content for m in self.history.load_for_page(1)]
        b = [m.content for m in self.history.load_for_page(3)]
        self.assertEqual(a, ["A's secret question", "reply to A"])
        self.assertEqual(b, ["B's question", "reply to B"])
        self.assertEqual(self.history.load_for_page(999), [])


class ChatErrorHandlingTests(unittest.TestCase):
    """The chat route's limits and friendly errors, with the AI call replaced by a stub."""

    @classmethod
    def setUpClass(cls):
        import asyncio

        import main
        from fastapi import HTTPException
        from starlette.requests import Request

        cls.asyncio, cls.main, cls.HTTPException, cls.Request = asyncio, main, HTTPException, Request

    def request(self, path="/api/chat", session=None):
        scope = {"type": "http", "method": "POST", "path": path, "headers": [], "query_string": b"",
                 "session": session if session is not None else {}}
        return self.Request(scope)

    def run_chat_with(self, fake_ask):
        real = self.main.ask
        self.main.ask = fake_ask
        try:
            return self.asyncio.run(self.main.chat(ChatRequest(message="hi"), self.request(session={"chat_guest_id": "t"})))
        finally:
            self.main.ask = real

    def test_timeout_becomes_friendly_504(self):
        async def slow(*a):
            raise self.asyncio.TimeoutError()

        with self.assertRaises(self.HTTPException) as cm:
            self.run_chat_with(slow)
        self.assertEqual(cm.exception.status_code, 504)
        self.assertEqual(cm.exception.detail, self.main.CHAT_TIMEOUT)

    def test_model_failure_becomes_friendly_502(self):
        async def broken(*a):
            raise RuntimeError("sqlite3.OperationalError: secret internals")

        with self.assertRaises(self.HTTPException) as cm:
            self.run_chat_with(broken)
        self.assertEqual(cm.exception.status_code, 502)
        self.assertNotIn("sqlite", cm.exception.detail)

    def test_duplicate_send_gets_409(self):
        self.main._chats_in_flight.add("guest:dup")
        try:
            with self.assertRaises(self.HTTPException) as cm:
                self.asyncio.run(self.main.chat(ChatRequest(message="hi"), self.request(session={"chat_guest_id": "dup"})))
            self.assertEqual(cm.exception.status_code, 409)
        finally:
            self.main._chats_in_flight.discard("guest:dup")

    def test_in_flight_lock_is_released_after_an_error(self):
        async def broken(*a):
            raise RuntimeError("boom")

        with self.assertRaises(self.HTTPException):
            self.run_chat_with(broken)
        self.assertNotIn("guest:t", self.main._chats_in_flight)

    def test_rate_limit_after_12_messages_a_minute(self):
        key = "guest:rate-test"
        self.main._recent_chats.pop(key, None)
        results = [self.main._too_many_recent(key) for _ in range(13)]
        self.assertEqual(results, [False] * 12 + [True])

    def test_unexpected_error_handler_hides_details(self):
        resp = self.asyncio.run(self.main.friendly_server_error(self.request("/api/products"), ValueError("secret")))
        self.assertEqual(resp.status_code, 500)
        self.assertNotIn(b"secret", resp.body)

    def test_bad_chat_input_handler_is_friendly(self):
        from fastapi.exceptions import RequestValidationError

        resp = self.asyncio.run(self.main.friendly_validation_error(self.request("/api/chat"), RequestValidationError([])))
        self.assertEqual(resp.status_code, 400)
        self.assertIn(b"Please type a message", resp.body)


class AuditTrailTests(unittest.TestCase):
    """The append-only audit trail (run against a temporary file)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.real = audit.AUDIT_PATH
        audit.AUDIT_PATH = Path(self.tmp.name) / "audit_trail.json"
        audit.current_run.set(None)

    def tearDown(self):
        audit.AUDIT_PATH = self.real
        audit.current_run.set(None)
        self.tmp.cleanup()

    def test_appends_and_keeps_valid_json(self):
        for i in range(25):
            audit.record({"event": "tool_call", "tool": "t", "n": i})
        records = audit.read_all()
        self.assertEqual([r["n"] for r in records], list(range(25)))
        self.assertTrue(all(r["timestamp"].endswith("+00:00") for r in records))

    def test_existing_records_survive_a_restart(self):
        audit.record({"event": "first"})
        import importlib

        path = audit.AUDIT_PATH
        importlib.reload(audit)  # simulate the backend restarting
        audit.AUDIT_PATH = path
        audit.record({"event": "second"})
        self.assertEqual([r["event"] for r in audit.read_all()], ["first", "second"])

    def test_unreadable_trail_is_never_overwritten(self):
        audit.AUDIT_PATH.write_text("not json {")
        audit.record({"event": "x"})
        self.assertEqual(audit.AUDIT_PATH.read_text(), "not json {")
        self.assertIn('"event": "x"', audit.AUDIT_PATH.with_suffix(".recovery.jsonl").read_text())

    def test_logging_failure_does_not_raise(self):
        audit.AUDIT_PATH = Path(self.tmp.name) / "missing-dir" / "\0bad" / "audit.json"
        audit.record({"event": "x"})  # must not raise

    def test_redaction(self):
        text = "email ada@yale.edu password=hunter2 key pk-abcdef123456 token=xyz"
        r = audit.redact(text)
        for secret in ("ada@yale.edu", "hunter2", "pk-abcdef123456", "xyz"):
            self.assertNotIn(secret, r)

    def test_tool_calls_are_recorded_validated_and_deduplicated(self):
        search = next(t for t in tools.AGENT_TOOLS if t.__name__ == "search_products")
        audit.start_run("guest", "/")
        r1 = search(category="Hoodies", max_price=-5, keyword="  hood\x00 ")
        r2 = search(category="Hoodies", max_price=-5, keyword="  hood\x00 ")
        self.assertIs(r1, r2)  # second identical call reused, no second query
        calls = [r for r in audit.read_all() if r["event"] == "tool_call"]
        self.assertEqual([c["outcome"] for c in calls], ["ok", "duplicate_call_reused"])
        self.assertEqual(calls[0]["tool"], "search_products")
        self.assertIn("keyword='hood'", calls[0]["arguments"])  # control chars stripped
        self.assertNotIn("max_price", calls[0]["arguments"])  # negative price ignored
        self.assertIn("27 matches", calls[0]["result"])
        self.assertTrue(calls[0]["run_id"])


class AgentRunAuditTests(unittest.TestCase):
    """A full agent run with PydanticAI's offline TestModel (no network, no cost):
    it calls the real tools, so run_start, tool_call, and run_end must all be recorded."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.real = audit.AUDIT_PATH
        audit.AUDIT_PATH = Path(self.tmp.name) / "audit_trail.json"

    def tearDown(self):
        audit.AUDIT_PATH = self.real
        self.tmp.cleanup()

    def test_full_run_is_audited_from_start_to_stop(self):
        import asyncio

        import agent
        from pydantic_ai.models.test import TestModel

        deps = agent.AgentDeps(customer=None, page=None, viewing_product=None)
        with agent.agent.override(model=TestModel(call_tools=["search_products"])):
            out = asyncio.run(agent.ask("show me hoodies", [], deps))
        self.assertIsInstance(out, AgentOutput)
        events = [r["event"] for r in audit.read_all()]
        self.assertEqual(events[0], "run_start")
        self.assertIn("tool_call", events)
        self.assertEqual(events[-1], "run_end")
        end = audit.read_all()[-1]
        self.assertEqual(end["stop_reason"], "final_output")
        self.assertGreaterEqual(end["tool_calls"], 1)
        self.assertEqual(len({r["run_id"] for r in audit.read_all()}), 1)  # all tied to one run


class ExecutionLimitTests(unittest.TestCase):
    """The real agent and its real limits, driven by a scripted FunctionModel (no network)."""

    def setUp(self):
        import asyncio

        import agent

        self.asyncio, self.agent = asyncio, agent
        self.tmp = tempfile.TemporaryDirectory()
        self.real = audit.AUDIT_PATH
        audit.AUDIT_PATH = Path(self.tmp.name) / "audit_trail.json"
        self.deps = agent.AgentDeps(customer=None, page=None, viewing_product=None)

    def tearDown(self):
        audit.AUDIT_PATH = self.real
        self.tmp.cleanup()

    def _run(self, model):
        with self.agent.agent.override(model=model):
            return self.asyncio.run(self.agent.ask("show me hoodies", [], self.deps))

    def test_runaway_tool_loop_stops_at_configured_limits(self):
        from pydantic_ai.exceptions import UsageLimitExceeded
        from pydantic_ai.messages import ModelResponse, ToolCallPart
        from pydantic_ai.models.function import FunctionModel

        calls = {"n": 0}

        def always_search(messages, info):  # a model that never stops calling tools
            calls["n"] += 1
            return ModelResponse(parts=[ToolCallPart("search_products", {"keyword": f"hood {calls['n']}"})])

        with self.assertRaises(UsageLimitExceeded):
            self._run(FunctionModel(always_search))
        limits = self.agent.RUN_LIMITS
        self.assertLessEqual(calls["n"], limits.request_limit)  # never more than 8 model requests
        records = audit.read_all()
        tool_calls = [r for r in records if r["event"] == "tool_call"]
        self.assertLessEqual(len(tool_calls), limits.tool_calls_limit)  # never more than 10 tool calls
        self.assertEqual(records[-1]["event"], "run_end")
        self.assertEqual(records[-1]["stop_reason"], "usage_limit_exceeded")

    def test_slow_model_hits_timeout_and_is_recorded(self):
        from pydantic_ai.models.function import FunctionModel

        async def stall(messages, info):
            await self.asyncio.sleep(5)

        real_timeout = self.agent.RUN_TIMEOUT_SECONDS
        self.agent.RUN_TIMEOUT_SECONDS = 0.3
        try:
            with self.assertRaises(self.asyncio.TimeoutError):
                self._run(FunctionModel(stall))
        finally:
            self.agent.RUN_TIMEOUT_SECONDS = real_timeout
        end = audit.read_all()[-1]
        self.assertEqual((end["event"], end["stop_reason"]), ("run_end", "timeout"))

    def test_limit_errors_reach_the_shopper_as_friendly_messages(self):
        import main
        from fastapi import HTTPException
        from pydantic_ai.exceptions import UsageLimitExceeded
        from starlette.requests import Request

        scope = {"type": "http", "method": "POST", "path": "/api/chat", "headers": [], "query_string": b"",
                 "session": {"chat_guest_id": "limits"}}
        for exc, status in [(UsageLimitExceeded("tool_calls_limit of 10"), 502), (self.asyncio.TimeoutError(), 504)]:
            async def boom(*a, _e=exc):
                raise _e

            real = main.ask
            main.ask = boom
            try:
                with self.assertRaises(HTTPException) as cm:
                    self.asyncio.run(main.chat(ChatRequest(message="hi"), Request(scope)))
            finally:
                main.ask = real
            self.assertEqual(cm.exception.status_code, status)
            self.assertNotIn("limit", cm.exception.detail.lower())  # no internals shown
            self.assertNotIn("guest:limits", main._chats_in_flight)  # lock released


class SafetyEnforcementTests(unittest.TestCase):
    """Safety rules enforced in code, not just in the prompt."""

    @classmethod
    def setUpClass(cls):
        import agent

        cls.agent = agent

    def ctx(self):
        msgs = [ModelRequest(parts=[ToolReturnPart(tool_name="search_products", content={"products": [{"product_id": "x", "price": 58.0}]}, tool_call_id="1")])]
        return SimpleNamespace(messages=msgs, deps=SimpleNamespace(viewing_product=None))

    def test_transaction_claims_are_rejected(self):
        for claim in [
            "Great news, your order has been placed!",
            "I've processed your payment of $58.",
            "Your refund was issued.",
            "It will arrive by Friday.",
            "Plus free shipping!",
        ]:
            with self.assertRaises(ModelRetry, msg=claim):
                self.agent.grounded_in_catalogue(self.ctx(), AgentOutput(reply=claim))

    def test_honest_refusals_are_allowed(self):
        for ok in [
            "I can't place orders in chat, but you can buy it on the product page.",
            "I'm not able to process payments or refunds. Please visit the shop at 57 Broadway.",
            "I can't promise a delivery date.",
        ]:
            self.agent.grounded_in_catalogue(self.ctx(), AgentOutput(reply=ok))

    def test_agent_tools_are_read_only_catalogue_lookups(self):
        self.assertEqual(
            sorted(t.__name__ for t in tools.AGENT_TOOLS),
            ["check_stock", "get_product_details", "search_products", "similar_products"],
        )
        with db.get_db() as conn:  # the connection the tools use
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("UPDATE catalogue SET price = 1")

    def test_tools_never_read_the_users_table(self):
        src = Path(tools.__file__).read_text().lower()
        self.assertNotIn("from users", src)
        self.assertNotIn("password", src)


if __name__ == "__main__":
    unittest.main()
