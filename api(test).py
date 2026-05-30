import requests

# # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
# # url = 'https://www.alphavantage.co/query?function=ETF_PROFILE&symbol=IAU&apikey=ARUN8KP5SSX81J2U'
# # r = requests.get(url)
# # data = r.json()

# import requests

# # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
# url = 'https://www.alphavantage.co/query?function=WTI&interval=weekly&apikey=ARUN8KP5SSX81J2U'
# r = requests.get(url)
# data = r.json()

# print(data)
# print(data)

url = 'https://www.alphavantage.co/query?function=OVERVIEW&symbol=CVX&apikey=ARUN8KP5SSX81J2U'
r = requests.get(url)
data = r.json()

print(data)

# #XOM

# tradingagents/dataflows/fred_common.py

# from datetime import date, timedelta
# from typing import List, Optional

# from tradingagents.dataflows.fred_common import get_series_observations
# FRED_API_KEY='5cf9956857ca184667876289f41f58cd'
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()
# def _last_n_valid(obs_list, n):
#     """observations 리스트에서 값이 유효한 마지막 n개만 뒤에서부터 추출(시간 오름차순으로 반환)."""
#     valid = [o for o in obs_list if o.get("value") not in (None, "", ".")]
#     return valid[-n:] if len(valid) >= n else valid

# def _format_table(rows, header=("Date", "Value")) -> str:
#     """간단한 Markdown 표 생성 (우측 정렬은 값 컬럼만)."""
#     lines = []
#     lines.append(f"| {header[0]} | {header[1]} |")
#     lines.append("|---|---:|")
#     for d, v in rows:
#         lines.append(f"| {d} | {v} |")
#     return "\n".join(lines)


# def get_macro_data(
#     series_ids: Optional[List[str]] = None,
#     start_date: Optional[str] = None,
#     end_date: Optional[str] = None,
#     frequency: Optional[str] = None,
# ) -> str:
#     """
#     FRED 매크로 스냅샷을 LLM 친화적 JSON 문자열로 반환합니다.
#     - 기본 시리즈: FEDFUNDS(m), UNRATE(m), CPIAUCSL(m), GDP(q), DCOILWTICO(d)
#     - 구간: 월(최근 12), 분기(최근 4), 일(최근 30)
#     - 반환: JSON string (키 고정 스키마)
#     """
#     from datetime import date, timedelta
#     import json

#     default_series = ["FEDFUNDS", "UNRATE", "CPIAUCSL", "GDP", "DCOILWTICO"]
#     native_freq = {"FEDFUNDS": "m", "UNRATE": "m", "CPIAUCSL": "m", "GDP": "q", "DCOILWTICO": "d"}
#     trend_take  = {"FEDFUNDS": 12, "UNRATE": 12, "CPIAUCSL": 12, "GDP": 4, "DCOILWTICO": 30}
#     titles = {
#         "FEDFUNDS": "Federal Funds Rate",
#         "UNRATE": "Unemployment Rate",
#         "CPIAUCSL": "CPI (All Urban Consumers, SA Index)",
#         "GDP": "Real GDP",
#         "DCOILWTICO": "WTI Crude Oil",
#     }

#     # 요청 시리즈: 기본 + 사용자 지정(중복 제거, 순서 보존)
#     sids = list(dict.fromkeys(default_series + (series_ids or [])))

#     today = date.today()
#     if not end_date:
#         end_date = today.isoformat()
#     if not start_date:
#         start_date = (today - timedelta(days=365 * 3)).isoformat()

#     def _last_n_valid(obs_list, n):
#         valid = [o for o in obs_list if o.get("value") not in (None, "", ".")]
#         return valid[-n:] if len(valid) >= n else valid

#     def _fmt_date_by_freq(d: str, f: str) -> str:
#         # FRED 날짜는 보통 YYYY-MM-01 같은 형식
#         if f == "m":
#             return d[:7]  # YYYY-MM
#         if f == "q":
#             # 월→분기 변환 (01/04/07/10 시작 가정)
#             y, m = int(d[:4]), int(d[5:7])
#             q = 1 if m <= 3 else 2 if m <= 6 else 3 if m <= 9 else 4
#             return f"{y}-Q{q}"
#         # 일별
#         return d  # YYYY-MM-DD

#     series_payloads = []

#     for sid in sids:
#         try:
#             eff_freq = native_freq.get(sid)  # 전달된 frequency는 무시하고 원주기 사용
#             payload = get_series_observations(
#                 series_id=sid,
#                 start_date=start_date,
#                 end_date=end_date,
#                 frequency=eff_freq,
#                 units=None,
#             )
#             obs = payload.get("observations", [])
#             last_n = _last_n_valid(obs, trend_take.get(sid, 12))

#             if not last_n:
#                 series_payloads.append({
#                     "id": sid,
#                     "title": titles.get(sid, sid),
#                     "frequency": eff_freq,
#                     "latest": None,
#                     "trend": [],
#                     "error": "no_data"
#                 })
#                 continue

#             # 최신값
#             last = last_n[-1]
#             latest_date_raw = last.get("date", "N/A")
#             latest_val = last.get("value", "N/A")
#             latest_date = _fmt_date_by_freq(latest_date_raw, eff_freq)

#             # 추세(시간 오름차순)
#             trend = [{"date": _fmt_date_by_freq(o["date"], eff_freq), "value": o["value"]} for o in last_n]

#             series_payloads.append({
#                 "id": sid,
#                 "title": titles.get(sid, sid),
#                 "frequency": eff_freq,            # 'm'/'q'/'d'
#                 "latest": {"date": latest_date, "value": latest_val},
#                 "trend": trend
#             })
#         except Exception as e:
#             series_payloads.append({
#                 "id": sid,
#                 "title": titles.get(sid, sid),
#                 "frequency": native_freq.get(sid),
#                 "latest": None,
#                 "trend": [],
#                 "error": str(e)
#             })

#     result = {
#         "as_of": end_date,
#         "series": series_payloads
#     }
#     # LLM 파싱 안정성을 위해 공백 최소화
#     return json.dumps(result, ensure_ascii=False, separators=(",", ":"))



# if __name__ == "__main__":
#     md = get_macro_data()
#     print(md)