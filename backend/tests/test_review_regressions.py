"""운영 서비스 호출 없이 캐시 무효화·설명 비용·점수 일관성 회귀 검사.

uv run --no-sync python -m unittest discover -s tests -v
"""
import copy
import threading
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import recommendations as api
from app.api import events as events_api
from app.core.bot_guard import guard_external_traffic
from app.core.rate_limit import limiter
from app.recommender.pipeline import rank_v2
from app.services import recommendation_cache as cache


def query_result(data):
    query = MagicMock()
    for method in ("select", "eq", "in_", "limit"):
        getattr(query, method).return_value = query
    query.execute.return_value = SimpleNamespace(data=data)
    return query


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.notice = {
            "bid_ntce_no": "A", "bid_ntce_ord": "000", "bid_ntce_nm": "유지보수",
            "bid_clse_date": "2099-01-01", "bid_qlfct_rgst_dt": None,
        }
        self.payload = {"results": [self.notice], "_cache_version": cache.CACHE_VERSION}

    def current(self, companies=None, notices=None):
        client = MagicMock()
        client.table.side_effect = [
            query_result(companies if companies is not None else [{"optout_at": None, "is_restricted": False}]),
            query_result(notices if notices is not None else [self.notice]),
        ]
        return cache._current(client, "1234567890", self.payload)

    def test_valid_cache_and_removed_company(self):
        self.assertTrue(self.current())
        self.assertFalse(self.current(companies=[]))

    def test_optout_or_restricted_duplicate_invalidates(self):
        for state in ({"optout_at": "2026-10-28"}, {"is_restricted": True}):
            with self.subTest(state=state):
                self.assertFalse(self.current(companies=[{}, state]))

    def test_new_cancellation_order_invalidates_original(self):
        cancelled = {**self.notice, "bid_ntce_ord": "001", "status": "취소공고"}
        self.assertFalse(self.current(notices=[self.notice, cancelled]))

    def test_registration_deadline_or_notice_change_invalidates(self):
        for changes in ({"bid_qlfct_rgst_dt": "2000-01-01T00:00:00Z"},
                        {"bid_clse_date": "2000-01-01"},
                        {"prtcpt_psbl_rgn_nm": "서울특별시"},
                        {"bid_ntce_nm": "정정공고"}):
            with self.subTest(changes=changes):
                self.assertFalse(self.current(notices=[{**self.notice, **changes}]))
        self.assertFalse(self.current(notices=[]))

    def test_ttl_version_and_state_check_failure_are_misses(self):
        now = datetime.now(timezone.utc)
        for at, version in ((now - timedelta(hours=2), cache.CACHE_VERSION), (now, 1)):
            client = MagicMock()
            client.table.return_value = query_result([{
                "payload": {**self.payload, "_cache_version": version},
                "result_limit": 20, "computed_at": at.isoformat(),
            }])
            with patch.object(cache, "get_admin_client", return_value=client):
                self.assertIsNone(cache.load("1234567890", "v2", 5))
        client.table.return_value = query_result([{
            "payload": self.payload, "result_limit": 20, "computed_at": now.isoformat(),
        }])
        with patch.object(cache, "get_admin_client", return_value=client), \
             patch.object(cache, "_current", side_effect=RuntimeError("offline")):
            self.assertIsNone(cache.load("1234567890", "v2", 5))

    def test_current_hit_hides_cache_metadata_without_mutating_stored_payload(self):
        payload = {**self.payload, "results": [
            {**self.notice, "bid_ntce_no": str(i)} for i in range(6)
        ]}
        client = MagicMock()
        client.table.return_value = query_result([{
            "payload": payload, "result_limit": 20,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }])
        with patch.object(cache, "get_admin_client", return_value=client), \
             patch.object(cache, "_current", return_value=True):
            hit = cache.load("1234567890", "v2", 5)
        self.assertTrue(hit["cached"])
        self.assertEqual(len(hit["results"]), 5)
        self.assertNotIn("_cache_version", hit)
        self.assertEqual(len(payload["results"]), 6)
        self.assertIn("_cache_version", payload)


class StreamTests(unittest.TestCase):
    def test_false_skips_llm_and_records_actual_option(self):
        app = FastAPI()
        app.state.limiter = limiter
        app.include_router(api.router)
        app.dependency_overrides[guard_external_traffic] = lambda: None
        result = {"company": {"bizrno": "1234567890"},
                  "results": [{"bid_ntce_no": "A", "bid_ntce_ord": "000"}]}
        logged = threading.Event()
        with patch.object(api, "recommend", return_value=result), \
             patch.object(api, "explain_summary") as summary, \
             patch.object(api, "explain_recommendation") as card, \
             patch.object(api, "explain_keyword_match") as keyword, \
             patch.object(api, "log_search", side_effect=lambda **_: logged.set()) as log, \
             patch.object(api, "log_impressions"):
            response = TestClient(app).post("/recommendations/stream", json={
                "query": "테스트", "with_explanation": False, "explain_top": 5,
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn('"type": "done"', response.text)
            summary.assert_not_called()
            card.assert_not_called()
            keyword.assert_not_called()
            self.assertTrue(logged.wait(2))
            self.assertFalse(log.call_args.kwargs["with_explanation"])

    def test_true_keeps_company_summary(self):
        app = FastAPI()
        app.state.limiter = limiter
        app.include_router(api.router)
        app.dependency_overrides[guard_external_traffic] = lambda: None
        result = {"company": {"bizrno": "1234567890"},
                  "results": [{"bid_ntce_no": "A", "bid_ntce_ord": "000"}]}
        with patch.object(api, "recommend", return_value=result), \
             patch.object(api, "explain_summary", return_value="summary") as summary, \
             patch.object(api, "log_search"), patch.object(api, "log_impressions"):
            response = TestClient(app).post("/recommendations/stream", json={
                "query": "테스트", "with_explanation": True, "explain_top": 5,
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn('"type": "summary"', response.text)
        summary.assert_called_once()


class ScoreTests(unittest.TestCase):
    def test_display_score_includes_unknown_license_penalty(self):
        from app.services import recommend
        candidate = {"bid_ntce_no": "A", "bid_ntce_ord": "000", "similarity": .8}
        eligibility = {("A", "000"): {"licenses": [{"lcns_lmt_nm": "건축공사업"}], "regions": []}}
        with patch.object(recommend, "_fetch_eligibility", return_value=eligibility), \
             patch.object(recommend, "_fetch_notice_status", return_value=[]), \
             patch.object(recommend, "_fetch_result_embeddings", return_value={}), \
             patch("app.recommender.pipeline.fetch_institution_stats", return_value={}), \
             patch("app.recommender.pipeline.score_notice", return_value=(100.0, [])):
            results = rank_v2(MagicMock(), [copy.deepcopy(candidate)], company_rgn=None,
                              company_terms=set(), company_institutions=set(),
                              company_amt_median=None, company_industry_names=set(), limit=5)
        self.assertEqual(results[0]["score_raw"], 88.0)
        self.assertEqual(results[0]["score"], .44)


class EventSourceTests(unittest.TestCase):
    def test_event_source_is_classified_instead_of_defaulting_to_user(self):
        app = FastAPI()
        app.state.limiter = limiter
        app.include_router(events_api.router)
        app.dependency_overrides[guard_external_traffic] = lambda: None
        for source in ("bot", "internal", "user"):
            with self.subTest(source=source), \
                 patch.object(events_api, "classify_source", return_value=source), \
                 patch.object(events_api, "log_notice_events") as log:
                response = TestClient(app).post("/events", json={"event_type": "save", "bid_ntce_no": "A"})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(log.call_args.args[0][0]["source"], source)


class ProfileFetchTests(unittest.TestCase):
    """벡터도 프로필도 없는 회사 — 요청 시점에 조달청에서 받아 오고, 오타 등급 매칭이면 '못 찾음'으로 돌린다."""

    def _run(self, match, fetched, texts):
        from app.services import recommend as svc
        company = {"bizrno": "1-1", "corp_nm": "회사", "match": match, "embedding": None}
        with patch.object(svc, "find_company", return_value=company), \
             patch.object(svc, "get_admin_client", return_value=MagicMock()), \
             patch.object(svc, "_build_industry_text", side_effect=texts) as build, \
             patch.object(svc, "_fetch_profile_now", return_value=fetched) as fetch, \
             patch.object(svc, "embed_texts", side_effect=RuntimeError("stop")):
            try:
                out = svc._recommend_by_company("회사", 20, 200)
            except RuntimeError:
                out = "embedded"
        return out, build, fetch

    def test_profile_fetched_on_the_spot_then_embedded(self):
        out, build, fetch = self._run("exact", True, [None, "등록업종: 전기공사업"])
        self.assertEqual(out, "embedded")
        fetch.assert_called_once()
        self.assertEqual(build.call_count, 2)

    def test_exact_match_without_profile_keeps_error(self):
        out, _, fetch = self._run("exact", False, [None])
        self.assertEqual(out["error"], "등록업종·공급물품 정보가 없어 추천할 수 없습니다")
        fetch.assert_called_once()

    def test_fuzzy_match_without_profile_is_not_found(self):
        out, _, _ = self._run("fuzzy", False, [None])
        self.assertEqual(out["error"], "회사를 찾을 수 없습니다")
        self.assertIsNone(out["company"])

    def test_fetch_once_per_day_per_company(self):
        from app.services import recommend as svc
        import jobs.ingest_company_details as job
        svc._PROFILE_FETCHED_AT.clear()
        with patch.object(job, "fetch_industries", return_value=[{"indstrytyCd": "0037", "indstrytyNm": "전기공사업"}]) as ind, \
             patch.object(job, "fetch_supply", return_value=[]), \
             patch("app.services.supabase_client.upsert_rows") as up:
            self.assertTrue(svc._fetch_profile_now(MagicMock(), "610-81-93004"))
            self.assertFalse(svc._fetch_profile_now(MagicMock(), "610-81-93004"))
        ind.assert_called_once_with("6108193004")
        self.assertEqual(up.call_args.args[0], "company_industries")
        svc._PROFILE_FETCHED_AT.clear()


if __name__ == "__main__":
    unittest.main()
