import os
import time
import requests
from datetime import date, timedelta
from typing import List, Dict, Any, Optional

API_BASE = "https://api.stlouisfed.org/fred"
TIMEOUT = 15
MAX_RETRIES = 3

class FREDAPIError(Exception):
    pass

def get_api_key() -> str:
    key = os.getenv("FRED_API_KEY")
    if not key:
        raise FREDAPIError("FRED_API_KEY environment variable not set.")
    return key

def _make_api_request(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generic FRED API call returning JSON.
    Automatically injects api_key and file_type=json.
    Retries on transient errors.
    """
    api_key = get_api_key()
    url = f"{API_BASE}/{path}"
    headers = {"User-Agent": "TradingAgents/1.0"}
    q = dict(params or {})
    q["api_key"] = api_key
    q["file_type"] = "json"

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=q, headers=headers, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            # FRED는 실패 시 HTTP 200 + error_message를 줄 수 있으므로 가볍게 점검
            if "error_message" in data:
                raise FREDAPIError(data["error_message"])
            return data
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(1.5 * attempt)
                continue
            raise FREDAPIError(f"FRED request failed: {e}") from e

def get_series_observations(
    series_id: str,
    start_date: str,
    end_date: str,
    frequency: Optional[str] = None,
    units: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch a FRED series observations time range.

    Args:
        series_id: e.g. "FEDFUNDS", "UNRATE", "CPIAUCSL", "GDP", "DCOILWTICO"
        start_date: 'YYYY-MM-DD'
        end_date: 'YYYY-MM-DD'
        frequency: 'd' (daily), 'w' (weekly), 'm' (monthly), 'q' (quarterly) ...
        units: transformation units (e.g., 'lin', 'chg', 'ch1', 'pch', 'pc1', 'pca', 'cch', 'cca', 'log')

    Returns:
        dict with observations array
    """
    params: Dict[str, Any] = {
        "series_id": series_id,
        "observation_start": start_date,
        "observation_end": end_date,
    }
    if frequency:
        params["frequency"] = frequency
    if units:
        params["units"] = units

    return _make_api_request("series/observations", params)
# tradingagents/dataflows/fred_common.py

from datetime import date, timedelta

def get_macro_data(
    series_ids: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    frequency: Optional[str] = None,
) -> str:
    """
    FRED 매크로 스냅샷을 LLM 친화적 JSON 문자열로 반환합니다.
    - 기본 시리즈: FEDFUNDS(m), UNRATE(m), CPIAUCSL(m), GDP(q), DCOILWTICO(d)
    - 구간: 월(최근 12), 분기(최근 4), 일(최근 30)
    - 반환: JSON string (키 고정 스키마)
    """
    from datetime import date, timedelta
    import json

    default_series = ["FEDFUNDS", "UNRATE", "CPIAUCSL", "GDP", "DCOILWTICO"]
    native_freq = {"FEDFUNDS": "m", "UNRATE": "m", "CPIAUCSL": "m", "GDP": "q", "DCOILWTICO": "d"}
    trend_take  = {"FEDFUNDS": 12, "UNRATE": 12, "CPIAUCSL": 12, "GDP": 4, "DCOILWTICO": 30}
    titles = {
        "FEDFUNDS": "Federal Funds Rate",
        "UNRATE": "Unemployment Rate",
        "CPIAUCSL": "CPI (All Urban Consumers, SA Index)",
        "GDP": "Real GDP",
        "DCOILWTICO": "WTI Crude Oil",
    }

    # 요청 시리즈: 기본 + 사용자 지정(중복 제거, 순서 보존)
    sids = list(dict.fromkeys(default_series + (series_ids or [])))

    today = date.today()
    if not end_date:
        end_date = today.isoformat()
    if not start_date:
        start_date = (today - timedelta(days=365 * 3)).isoformat()

    def _last_n_valid(obs_list, n):
        valid = [o for o in obs_list if o.get("value") not in (None, "", ".")]
        return valid[-n:] if len(valid) >= n else valid

    def _fmt_date_by_freq(d: str, f: str) -> str:
        # FRED 날짜는 보통 YYYY-MM-01 같은 형식
        if f == "m":
            return d[:7]  # YYYY-MM
        if f == "q":
            # 월→분기 변환 (01/04/07/10 시작 가정)
            y, m = int(d[:4]), int(d[5:7])
            q = 1 if m <= 3 else 2 if m <= 6 else 3 if m <= 9 else 4
            return f"{y}-Q{q}"
        # 일별
        return d  # YYYY-MM-DD

    series_payloads = []

    for sid in sids:
        try:
            eff_freq = native_freq.get(sid)  # 전달된 frequency는 무시하고 원주기 사용
            payload = get_series_observations(
                series_id=sid,
                start_date=start_date,
                end_date=end_date,
                frequency=eff_freq,
                units=None,
            )
            obs = payload.get("observations", [])
            last_n = _last_n_valid(obs, trend_take.get(sid, 12))

            if not last_n:
                series_payloads.append({
                    "id": sid,
                    "title": titles.get(sid, sid),
                    "frequency": eff_freq,
                    "latest": None,
                    "trend": [],
                    "error": "no_data"
                })
                continue

            # 최신값
            last = last_n[-1]
            latest_date_raw = last.get("date", "N/A")
            latest_val = last.get("value", "N/A")
            latest_date = _fmt_date_by_freq(latest_date_raw, eff_freq)

            # 추세(시간 오름차순)
            trend = [{"date": _fmt_date_by_freq(o["date"], eff_freq), "value": o["value"]} for o in last_n]

            series_payloads.append({
                "id": sid,
                "title": titles.get(sid, sid),
                "frequency": eff_freq,            # 'm'/'q'/'d'
                "latest": {"date": latest_date, "value": latest_val},
                "trend": trend
            })
        except Exception as e:
            series_payloads.append({
                "id": sid,
                "title": titles.get(sid, sid),
                "frequency": native_freq.get(sid),
                "latest": None,
                "trend": [],
                "error": str(e)
            })

    result = {
        "as_of": end_date,
        "series": series_payloads
    }
    # LLM 파싱 안정성을 위해 공백 최소화
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"))


### V1
# def get_macro_data(
#     series_ids: Optional[List[str]] = None,
#     start_date: Optional[str] = None,
#     end_date: Optional[str] = None,
#     frequency: Optional[str] = None,
# ) -> str:
#     """
#     FRED 매크로 스냅샷(최신 + 최근 추세) Markdown 반환.
#     - 기본 시리즈: FEDFUNDS, UNRATE, CPIAUCSL(월별), GDP(분기), DCOILWTICO(일별)
#     - 추세 표시 구간:
#         * FEDFUNDS / UNRATE / CPIAUCSL: 최근 12개월
#         * GDP: 최근 4분기
#         * DCOILWTICO: 최근 30일
#     - start/end 미지정 시: end=today, start=today-3년 (충분히 넉넉하게 받아온 뒤 뒤에서 N개만 자름)
#     - frequency 인자는 전달되어도 각 시리즈 원주기로 강제합니다.
#     """
#     from datetime import date, timedelta  # 외부 모듈 추가 없음 (표준만 사용)

#     # 기본 시리즈 / 원주기 / 추세 구간
#     default_series = ["FEDFUNDS", "UNRATE", "CPIAUCSL", "GDP", "DCOILWTICO"]
#     native_freq = {"FEDFUNDS": "m", "UNRATE": "m", "CPIAUCSL": "m", "GDP": "q", "DCOILWTICO": "d"}
#     trend_take = {"FEDFUNDS": 12, "UNRATE": 12, "CPIAUCSL": 12, "GDP": 4, "DCOILWTICO": 30}
#     titles = {
#         "FEDFUNDS": "Federal Funds Rate (Monthly) – Last 12",
#         "UNRATE": "Unemployment Rate (Monthly) – Last 12",
#         "CPIAUCSL": "CPI (All Urban Consumers, SA Index) (Monthly) – Last 12",
#         "GDP": "Real GDP (Quarterly) – Last 4",
#         "DCOILWTICO": "WTI Crude Oil (Daily) – Last 30",
#     }

#     # 요청 시리즈: 기본 + 사용자 지정 유니온(중복 제거)
#     sids = list(dict.fromkeys(default_series + (series_ids or [])))

#     today = date.today()
#     if not end_date:
#         end_date = today.isoformat()
#     if not start_date:
#         # 월/분기/일 모두 커버되도록 충분히 과거부터
#         start_date = (today - timedelta(days=365 * 3)).isoformat()

#     def _last_n_valid(obs_list, n):
#         # 유효값만 남기고 마지막 n개(시간 오름차순으로 반환)
#         valid = [o for o in obs_list if o.get("value") not in (None, "", ".")]
#         return valid[-n:] if len(valid) >= n else valid

#     def _mk_table(rows, head_left: str, head_right: str) -> str:
#         lines = [f"| {head_left} | {head_right} |"]
#         lines += [f"| {d} | {v} |" for d, v in rows]
#         return "\n".join(lines)

#     latest_lines = []
#     sections = []

#     for sid in sids:
#         try:
#             # 각 시리즈는 원주기로 강제
#             eff_freq = native_freq.get(sid)
#             payload = get_series_observations(
#                 series_id=sid,
#                 start_date=start_date,
#                 end_date=end_date,
#                 frequency=eff_freq,
#                 units=None,
#             )
#             obs = payload.get("observations", [])
#             take_n = trend_take.get(sid, 12)  # 기본 12
#             last_n = _last_n_valid(obs, take_n)

#             if not last_n:
#                 latest_lines.append(f"- **{sid}**: N/A")
#                 sections.append(f"#### {titles.get(sid, sid)}\n데이터 없음\n")
#                 continue

#             # 최신값
#             last = last_n[-1]
#             last_date = last.get("date", "N/A")
#             last_val = last.get("value", "N/A")
#             latest_lines.append(f"- **{sid}** latest: **{last_val}** (as of {last_date})")

#             # 추세 표
#             rows = [(o["date"], o["value"]) for o in last_n]
#             table_md = _mk_table(rows, "Date", sid)
#             sections.append(f"#### {titles.get(sid, sid)}\n{table_md}\n")

#         except Exception as e:
#             latest_lines.append(f"- **{sid}**: ERROR fetching data ({e})")
#             sections.append(f"#### {titles.get(sid, sid)}\nERROR: {e}\n")

#     header = f"### Macro Snapshot (FRED) – Latest & Recent Trends (as of {end_date})\n"
#     bullets = "\n".join(latest_lines)
#     body = "\n".join(sections)
#     return f"{header}{bullets}\n\n{body}"
