"""公司自動搜尋服務 - 爬取 104 + GCIS 官方 API + 海外公司登記 API，計算宿曜相性"""
import logging
import os
import re
from datetime import date, timedelta
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from shukuyo.services.sukuyodo import sukuyodo_service, SukuyodoService

logger = logging.getLogger(__name__)

# 104 JSON API
_104_SEARCH_URL = "https://www.104.com.tw/jobs/search/api/jobs"
_104_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.104.com.tw/jobs/search/",
    "Accept": "application/json, text/plain, */*",
}

# GCIS 經濟部商工登記開放資料 API
# 直接打 GCIS 會被擋（Render 在美國），改走 Vercel proxy
_GCIS_API_ID = "6BBA2268-1367-4B42-9CCA-BC17499EBE8C"
_GCIS_API_URL = f"https://shukuyo.dashai.dev/proxy/gcis/{_GCIS_API_ID}"

# findcompany 查詢設立日期（備援）
_FINDCOMPANY_BASE = "https://www.findcompany.com.tw"
_FINDCOMPANY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}

# 104 地區碼
AREA_CODES = {
    "tainan": "6001014000",     # 台南市善化區
    "tainan_all": "6001000000", # 台南市全區
    "kaohsiung": "6003000000",  # 高雄市
    "stsp": "6001014000",       # 南科（善化區）
}


class CompanySearchService:
    """公司搜尋與相性計算服務"""

    def __init__(self):
        self._founding_date_cache: dict[str, str | None] = {}

    async def search_104(
        self,
        keywords: str,
        area: str = "6001014000",
        pages: int = 2,
    ) -> list[dict]:
        """
        爬取 104 職缺搜尋結果

        Args:
            keywords: 搜尋關鍵字
            area: 104 地區碼
            pages: 搜尋頁數（每頁約 20 筆）

        Returns:
            公司名稱、職缺等資訊列表
        """
        results = []
        seen_companies = set()

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for page in range(1, pages + 1):
                params = {
                    "keyword": keywords,
                    "area": area,
                    "page": str(page),
                }

                try:
                    headers = {
                        **_104_HEADERS,
                        "Referer": f"https://www.104.com.tw/jobs/search/?keyword={quote(keywords)}&area={area}",
                    }
                    resp = await client.get(
                        _104_SEARCH_URL,
                        params=params,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    logger.warning("104 搜尋第 %d 頁失敗: %s", page, e)
                    continue

                job_list = data.get("data", [])
                if not job_list:
                    break

                for job in job_list:
                    cust_name = job.get("custName", "").strip()
                    if not cust_name or cust_name in seen_companies:
                        continue
                    seen_companies.add(cust_name)

                    # 取得職缺頁面 URL
                    link = job.get("link", {})
                    job_url = link.get("job", "")

                    results.append({
                        "company_name": cust_name,
                        "job_title": job.get("jobName", "") or job.get("jobNameSnippet", ""),
                        "location": job.get("jobAddrNoDesc", "") or job.get("jobAddress", ""),
                        "job_url": job_url,
                    })

        return results

    async def lookup_founding_date(
        self,
        company_name: str,
        country: str = "tw",
    ) -> str | None:
        """
        查詢公司設立日期（依國家選擇資料源）

        Args:
            company_name: 公司名稱（全名或關鍵字）
            country: 國家碼 (tw/jp/us)

        Returns:
            設立日期字串 (YYYY-MM-DD) 或 None
        """
        cache_key = f"{country}:{company_name}"
        if cache_key in self._founding_date_cache:
            return self._founding_date_cache[cache_key]

        result = None
        if country == "tw":
            result = await self._lookup_gcis(company_name)
            if not result:
                result = await self._lookup_findcompany(company_name)
        elif country == "jp":
            result = await self._lookup_gbizinfo(company_name)
        elif country == "us":
            result = await self._lookup_opencorporates(company_name)

        self._founding_date_cache[cache_key] = result
        return result

    async def lookup_104_company_url(self, company_name: str) -> str | None:
        """
        用公司名稱查詢 104 公司頁面連結

        Args:
            company_name: 公司名稱（全名或關鍵字）

        Returns:
            104 公司頁面 URL 或 None
        """
        search_name = self._normalize_company_name(company_name)

        if not search_name:
            return None

        result = await self._search_104_for_company_url(search_name)
        if result:
            return result

        # 104 偵測到純公司名時不回傳職缺（companyKeyword=true）
        # 附加通用關鍵字繞過此限制
        return await self._search_104_for_company_url(f"{search_name} 工程師", search_name)

    async def _search_104_for_company_url(
        self,
        keyword: str,
        match_name: str | None = None,
    ) -> str | None:
        """用 keyword 查 104，從結果中比對 match_name 取 link.cust"""
        if match_name is None:
            match_name = keyword

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            params = {"keyword": keyword, "page": "1"}
            headers = {
                **_104_HEADERS,
                "Referer": f"https://www.104.com.tw/jobs/search/?keyword={quote(keyword)}",
            }
            try:
                resp = await client.get(_104_SEARCH_URL, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.warning("104 查詢 %s 失敗: %s", keyword, e)
                return None

        job_list = data.get("data", [])
        if not job_list:
            return None

        for job in job_list:
            cust_name = job.get("custName", "").strip()
            if match_name in cust_name:
                cust_url = job.get("link", {}).get("cust", "")
                if cust_url:
                    if cust_url.startswith("//"):
                        cust_url = f"https:{cust_url}"
                    return cust_url

        return None

    @staticmethod
    def _normalize_company_name(name: str) -> str:
        """正規化公司名稱：移除法人後綴、英文前綴/底線"""
        result = name
        for suffix in ["股份有限公司", "有限公司"]:
            result = result.replace(suffix, "")
        # 移除英文前綴 + 底線/橫線分隔（如 "I-TEK_一德" → "一德"）
        result = re.sub(r'^[A-Za-z0-9\s._-]+[_\-・]', '', result)
        result = re.sub(r'^[A-Za-z0-9\s._-]+\s+', '', result)
        return result.strip()

    async def search_gcis(self, keyword: str) -> list[dict]:
        """GCIS 公司名稱搜尋，回傳公司列表含設立日期"""
        search_name = self._normalize_company_name(keyword)

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(_GCIS_API_URL, params={
                    "$format": "json",
                    "$filter": f"Company_Name like {search_name} and Company_Status eq 01",
                    "$top": "10",
                })
                if resp.status_code != 200 or not resp.text.startswith("["):
                    return []
                data = resp.json()
            except Exception as e:
                logger.warning("GCIS 搜尋 %s 失敗: %s", keyword, e)
                return []

        results = []
        for company in data:
            setup_date = self._roc_to_western(company.get("Company_Setup_Date", ""))
            if not setup_date:
                continue
            results.append({
                "name": company.get("Company_Name", ""),
                "business_no": company.get("Business_Accounting_NO", ""),
                "founding_date": setup_date,
                "responsible": company.get("Responsible_Name", ""),
                "capital": company.get("Capital_Stock_Amount", "0"),
            })
        return results

    async def _lookup_gcis(self, company_name: str) -> str | None:
        """從 GCIS 官方 API 查詢設立日期（透過 Vercel proxy 避免美國 IP 被擋）"""
        search_name = self._normalize_company_name(company_name)

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(_GCIS_API_URL, params={
                    "$format": "json",
                    "$filter": f"Company_Name like {search_name} and Company_Status eq 01",
                    "$top": "5",
                })
                if resp.status_code != 200 or not resp.text.startswith("["):
                    return None
                data = resp.json()
            except Exception as e:
                logger.warning("GCIS 查詢 %s 失敗: %s", company_name, e)
                return None

        if not data:
            return None

        # 找最符合的公司（名稱包含原始關鍵字）
        for company in data:
            name = company.get("Company_Name", "")
            if search_name not in name:
                continue
            roc_date = company.get("Company_Setup_Date", "")
            return self._roc_to_western(roc_date)

        # 沒有完全符合的，用第一筆
        roc_date = data[0].get("Company_Setup_Date", "")
        return self._roc_to_western(roc_date)

    @staticmethod
    def _roc_to_western(roc_date: str) -> str | None:
        """民國 7 碼日期轉西曆 YYYY-MM-DD"""
        if not roc_date or len(roc_date) != 7:
            return None
        try:
            year = int(roc_date[:3]) + 1911
            month = roc_date[3:5]
            day = roc_date[5:7]
            result = f"{year}-{month}-{day}"
            date.fromisoformat(result)  # 驗證格式
            return result
        except (ValueError, IndexError):
            return None

    async def _lookup_findcompany(self, company_name: str) -> str | None:
        """從 findcompany.com.tw 查詢設立日期（備援）"""
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                url = f"{_FINDCOMPANY_BASE}/{company_name}"
                resp = await client.get(url, headers=_FINDCOMPANY_HEADERS)
                if resp.status_code != 200:
                    return None
                html = resp.text
            except Exception as e:
                logger.warning("findcompany 查詢 %s 失敗: %s", company_name, e)
                return None

        return self._parse_findcompany_date(html)

    async def _lookup_gbizinfo(self, company_name: str) -> str | None:
        """gBizINFO v2 (經濟産業省) 查詢日本公司設立日

        Step 1: search by name → 取得 corporate_number
        Step 2: detail by corporate_number → 取得 date_of_establishment
        """
        token = os.environ.get("GBIZINFO_API_TOKEN")
        if not token:
            logger.warning("GBIZINFO_API_TOKEN 未設定，無法查詢日本公司")
            return None

        base = "https://api.info.gbiz.go.jp/hojin/v2/hojin"
        headers = {"X-hojinInfo-api-token": token}

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Step 1: search
            try:
                resp = await client.get(
                    base,
                    params={"name": company_name, "page": "1"},
                    headers=headers,
                )
                if resp.status_code != 200:
                    logger.warning("gBizINFO 查詢 %s 失敗: HTTP %d", company_name, resp.status_code)
                    return None
                data = resp.json()
            except Exception as e:
                logger.warning("gBizINFO 查詢 %s 失敗: %s", company_name, e)
                return None

            items = data.get("hojin-infos", [])
            if not items:
                return None

            # 找最符合的結果（名稱包含搜尋字，排除閉鎖）
            best = None
            for item in items:
                name = item.get("name", "")
                status = item.get("status", "")
                if company_name in name and status != "閉鎖":
                    best = item
                    break
            if not best:
                # fallback: 第一筆非閉鎖的
                for item in items:
                    if item.get("status", "") != "閉鎖":
                        best = item
                        break
            if not best:
                best = items[0]

            corp_num = best.get("corporate_number")
            if not corp_num:
                return None

            # Step 2: detail — 取設立日期
            try:
                resp2 = await client.get(
                    f"{base}/{corp_num}",
                    headers=headers,
                )
                if resp2.status_code != 200:
                    logger.warning("gBizINFO detail %s 失敗: HTTP %d", corp_num, resp2.status_code)
                    return None
                detail = resp2.json()
            except Exception as e:
                logger.warning("gBizINFO detail %s 失敗: %s", corp_num, e)
                return None

        # detail 回傳也是 hojin-infos 陣列
        detail_items = detail.get("hojin-infos", [])
        detail_info = detail_items[0] if detail_items else detail

        estab = detail_info.get("date_of_establishment", "")
        if estab:
            estab = estab.replace("/", "-").split("T")[0]
            try:
                date.fromisoformat(estab)
                return estab
            except ValueError:
                pass

        # fallback: founding_year 只有年份
        year = detail_info.get("founding_year")
        if year:
            return f"{year}-01-01"

        return None

    async def _lookup_opencorporates(self, company_name: str) -> str | None:
        """OpenCorporates 查詢美國公司 incorporation date (免費 200/月)"""
        api_key = os.environ.get("OPENCORPORATES_API_KEY")
        if not api_key:
            logger.warning("OPENCORPORATES_API_KEY 未設定，無法查詢美國公司")
            return None

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    "https://api.opencorporates.com/v0.4.8/companies/search",
                    params={
                        "q": company_name,
                        "jurisdiction_code": "us",
                        "api_token": api_key,
                    },
                )
                if resp.status_code != 200:
                    logger.warning("OpenCorporates 查詢 %s 失敗: HTTP %d", company_name, resp.status_code)
                    return None
                data = resp.json()
            except Exception as e:
                logger.warning("OpenCorporates 查詢 %s 失敗: %s", company_name, e)
                return None

        companies = data.get("results", {}).get("companies", [])
        if not companies:
            return None

        # 找最符合的結果
        best = None
        name_lower = company_name.lower()
        for entry in companies:
            c = entry.get("company", {})
            c_name = c.get("name", "").lower()
            if name_lower in c_name:
                best = c
                break
        if not best:
            best = companies[0].get("company", {})

        inc_date = best.get("incorporation_date")
        if inc_date:
            try:
                date.fromisoformat(inc_date)
                return inc_date
            except ValueError:
                pass

        return None

    async def search_global(
        self,
        company_name: str,
        country: str,
        birth_date: date,
    ) -> dict | None:
        """
        全球公司查詢：查設立日 → 算相性

        Args:
            company_name: 公司名稱
            country: 國家碼 (tw/jp/us)
            birth_date: 使用者生日

        Returns:
            公司資訊 + 相性結果，或 None
        """
        founding_date_str = await self.lookup_founding_date(company_name, country)
        if not founding_date_str:
            return None

        try:
            founding_date = date.fromisoformat(founding_date_str)
        except ValueError:
            return None

        try:
            compat = sukuyodo_service.calculate_compatibility(birth_date, founding_date)
        except Exception as e:
            logger.warning("相性計算失敗 %s: %s", company_name, e)
            return None

        score = compat.get("score", 0)
        relation = compat.get("relation", {})
        relation_type = relation.get("type", "")
        direction = relation.get("direction", "")

        country_labels = {"tw": "台灣", "jp": "日本", "us": "美國"}

        return {
            "name": company_name,
            "founding_date": founding_date_str,
            "country": country,
            "country_name": country_labels.get(country, country),
            "source": {"tw": "gcis", "jp": "gbizinfo", "us": "opencorporates"}.get(country, ""),
            "score": score,
            "relation_name": relation.get("name", ""),
            "relation_type": relation_type,
            "direction": direction,
            "distance_type": relation.get("distance_type", ""),
            "distance_type_name": relation.get("distance_type_name", ""),
            "element_bonus": compat.get("element_bonus", 0),
            "verdict": self._get_verdict(relation_type, direction, score),
            "person1_mansion": compat.get("person1", {}).get("mansion", ""),
            "person1_element": compat.get("person1", {}).get("element", ""),
            "person2_mansion": compat.get("person2", {}).get("mansion", ""),
            "person2_element": compat.get("person2", {}).get("element", ""),
        }

    def _parse_findcompany_date(self, html: str) -> str | None:
        """從 findcompany.com.tw HTML 解析設立日期"""
        soup = BeautifulSoup(html, "html.parser")

        for el in soup.find_all(["td", "span", "div"]):
            text = el.get_text(strip=True)
            if text == "設立日期":
                next_el = el.find_next_sibling()
                if next_el:
                    date_text = next_el.get_text(strip=True)
                    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", date_text)
                    if m:
                        return m.group(0)

        dates = re.findall(r"\d{4}-\d{2}-\d{2}", html)
        if dates:
            for d in dates:
                try:
                    parsed = date.fromisoformat(d)
                    if parsed.year < 2025:
                        return d
                except ValueError:
                    continue

        return None

    async def search_and_calculate(
        self,
        keywords: str,
        area: str,
        birth_date: date,
        min_score: int = 0,
    ) -> list[dict]:
        """
        搜尋 104 職缺 → 查設立日期 → 算相性 → 排序

        Args:
            keywords: 搜尋關鍵字
            area: 104 地區碼
            birth_date: 使用者生日
            min_score: 最低分數門檻（0 表示不篩選）

        Returns:
            按分數排序的公司相性結果
        """
        # 1. 搜尋 104（過濾海外職缺）
        _overseas = ["美國", "美西", "美中", "美東", "海外", "USA", "US)", "California", "Arizona", "Texas"]
        raw_companies = await self.search_104(keywords, area)
        companies = [
            c for c in raw_companies
            if not any(kw in c.get("location", "") or kw in c.get("job_title", "") for kw in _overseas)
        ]
        if not companies:
            return []

        # 2. 對每間公司嘗試查設立日期 + 算相性
        #    查不到設立日期也回傳（score=0），讓前端決定是否顯示
        results = []
        for company in companies:
            base_result = {
                "name": company["company_name"],
                "job_title": company["job_title"],
                "location": company["location"],
                "job_url": company["job_url"],
            }

            # 嘗試查設立日期（可能因 IP 限制查不到）
            founding_date_str = await self.lookup_founding_date(company["company_name"])

            if not founding_date_str:
                results.append({
                    **base_result,
                    "founding_date": "",
                    "score": 0,
                    "relation_name": "",
                    "relation_type": "",
                    "direction": "",
                    "distance_type": "",
                    "distance_type_name": "",
                    "element_bonus": 0,
                    "verdict": "",
                    "person1_mansion": "",
                    "person1_element": "",
                    "person2_mansion": "",
                    "person2_element": "",
                })
                continue

            try:
                founding_date = date.fromisoformat(founding_date_str)
            except ValueError:
                continue

            # 3. 計算相性
            try:
                compat = sukuyodo_service.calculate_compatibility(birth_date, founding_date)
            except Exception as e:
                logger.warning("相性計算失敗 %s: %s", company["company_name"], e)
                continue

            score = compat.get("score", 0)
            relation = compat.get("relation", {})
            relation_type = relation.get("type", "")
            direction = relation.get("direction", "")
            verdict = self._get_verdict(relation_type, direction, score)

            results.append({
                **base_result,
                "founding_date": founding_date_str,
                "score": score,
                "relation_name": relation.get("name", ""),
                "relation_type": relation_type,
                "direction": direction,
                "distance_type": relation.get("distance_type", ""),
                "distance_type_name": relation.get("distance_type_name", ""),
                "element_bonus": compat.get("element_bonus", 0),
                "verdict": verdict,
                "person1_mansion": compat.get("person1", {}).get("mansion", ""),
                "person1_element": compat.get("person1", {}).get("element", ""),
                "person2_mansion": compat.get("person2", {}).get("mansion", ""),
                "person2_element": compat.get("person2", {}).get("element", ""),
            })

        # 4. 篩選 + 排序
        if min_score > 0:
            results = [r for r in results if r["score"] >= min_score]

        results.sort(key=lambda r: r["score"], reverse=True)
        return results

    def batch_analyze(
        self,
        birth_date: date,
        year: int,
        companies: list[dict],
        mode: str = "seeker",
        lang: str = "zh-TW",
    ) -> dict:
        """
        批次分析公司：相性 + 公司流年 + 梯隊排名 + 綜合戰略

        Args:
            birth_date: 使用者生日
            year: 分析年份
            companies: [{id, name, founding_date, memo?, job_url?}]
            mode: "seeker" (求職者看公司) 或 "hr" (公司看候選人)

        Returns:
            使用者流年 + 每間公司的綜合分析 + 梯隊統計
        """
        # 1. 計算使用者九曜流年（只做一次）
        user_yearly = sukuyodo_service.calculate_yearly_fortune(birth_date, year)

        # 2. 逐間公司計算
        results = []
        for company in companies:
            founding_date_str = company.get("founding_date", "")
            try:
                founding = date.fromisoformat(founding_date_str)
            except (ValueError, TypeError):
                continue

            # 相性
            try:
                compat = sukuyodo_service.calculate_compatibility(birth_date, founding, mode=mode, lang=lang)
            except Exception:
                continue

            score = compat.get("score", 0)
            relation = compat.get("relation", {})
            relation_type = relation.get("type", "")
            direction = relation.get("direction", "")

            # 公司九曜流年（輕量：只取 kuyou_star + overall + career）
            try:
                company_yearly = sukuyodo_service.calculate_yearly_fortune(founding, year)
                company_kuyou = company_yearly.get("kuyou_star", {})
                company_fortune = {
                    "kuyou_star": company_kuyou,
                    "overall": company_yearly.get("fortune", {}).get("overall", 50),
                    "career": company_yearly.get("fortune", {}).get("career", 50),
                }
            except Exception:
                company_kuyou = {}
                company_fortune = {"kuyou_star": {}, "overall": 50, "career": 50}

            company_level = company_kuyou.get("level", "末吉")

            # 梯隊
            tier = self._calculate_tier(score, company_level, relation_type, direction, mode, lang)

            memo = company.get("memo", "")

            # 投遞建議 / HR 選才建議
            recommendation = self._build_recommendation(
                tier, score, company_level, relation_type, direction, mode, lang
            )

            results.append({
                "id": company.get("id", ""),
                "name": company.get("name", ""),
                "compatibility": {
                    "score": score,
                    "relation": relation,
                    "person2": compat.get("person2", {}),
                    "direction_analysis": compat.get("direction_analysis", {}),
                },
                "company_fortune": company_fortune,
                "tier": tier,
                "recommendation": recommendation,
                "memo": memo,
                "job_url": company.get("job_url", ""),
            })

        # 3. 按梯隊 + 分數排序
        results.sort(key=lambda r: (r["tier"]["rank"], -r["compatibility"]["score"]))

        # 4. 設定 priority
        for i, r in enumerate(results, 1):
            r["recommendation"]["priority"] = i

        # 5. 梯隊統計
        tier_summary = {"tier_1": 0, "tier_2": 0, "tier_3": 0, "tier_4": 0}
        for r in results:
            key = f"tier_{r['tier']['rank']}"
            tier_summary[key] = tier_summary.get(key, 0) + 1

        return {
            "user": {
                "mansion": user_yearly.get("your_mansion", {}),
                "yearly_fortune": {
                    "kuyou_star": user_yearly.get("kuyou_star", {}),
                    "overall": user_yearly.get("fortune", {}).get("overall", 50),
                    "career": user_yearly.get("fortune", {}).get("career", 50),
                },
            },
            "companies": results,
            "tier_summary": tier_summary,
            "strategic_summary": self._build_strategic_summary(results, user_yearly, mode, lang),
        }

    def _build_strategic_summary(self, results: list, user_yearly: dict, mode: str = "seeker", lang: str = "zh-TW") -> dict:
        """跨公司綜合戰略建議

        根據所有公司的相性、梯隊、流年等綜合資料，產出策略性總結。

        Args:
            results: 已排序的公司分析結果列表
            user_yearly: 使用者流年資料
            mode: "seeker" 或 "hr"

        Returns:
            首選推薦、分類建議、方向洞察
        """
        if not results:
            return {"top_pick": None, "categories": {}, "direction_insight": ""}

        # 載入 JSON 模板
        json_data = SukuyodoService._load_guidance_json(lang)
        stpl = json_data.get("strategic", {})
        cat_reason_tpl = stpl.get("category_reason", "{dir_label}（{score}分）— {dir_text}")
        fortune_good_tpl = stpl.get("fortune_good", "，加上公司今年流年{level}，時機很好")

        # 分類邏輯
        best_match = []
        growth_potential = []
        safe_bet = []
        watch_out = []

        # 方向一句話總結 — 從 JSON hr_summary 讀取
        direction_summary = {}
        for d in ["命", "栄", "衰", "安", "危", "成", "壊", "友", "親", "業", "胎"]:
            if mode == "hr":
                hs = json_data.get("hr_summary", {}).get(d, {})
                direction_summary[d] = hs.get("summary", SukuyodoService.get_hr_summary(d))
            else:
                direction_summary[d] = SukuyodoService.get_career_summary(d, lang)

        for r in results:
            name = r.get("name", "")
            score = r["compatibility"]["score"]
            relation = r["compatibility"]["relation"]
            rel_type = relation.get("type", "")
            direction = relation.get("direction", "")
            company_level = r.get("company_fortune", {}).get("kuyou_star", {}).get("level", "")
            rel_name = relation.get("name", "")
            dir_text = direction_summary.get(direction, "")
            dir_label = f"{rel_name}/{direction}" if direction else rel_name

            reason = cat_reason_tpl.format(dir_label=dir_label, score=score, dir_text=dir_text)

            if rel_type == "eishin" or score >= 85:
                if company_level in ("大吉", "半吉"):
                    reason += fortune_good_tpl.format(level=company_level)
                best_match.append({"name": name, "reason": reason})
            elif rel_type in ("gyotai", "mei"):
                growth_potential.append({"name": name, "reason": reason})
            elif 60 <= score < 85:
                safe_bet.append({"name": name, "reason": reason})
            else:
                watch_out.append({"name": name, "reason": reason})

        # 首選推薦
        top = results[0]
        top_relation = top["compatibility"]["relation"]
        top_direction = top_relation.get("direction", "")
        top_score = top["compatibility"]["score"]
        top_rel_name = top_relation.get("name", "")
        top_dir_summary = direction_summary.get(top_direction, "")
        top_company_level = top.get("company_fortune", {}).get("kuyou_star", {}).get("level", "")

        top_reason_tpl = stpl.get("top_pick_reason", "{rel_name}・{tier_label}・{score}分 — {dir_summary}")
        top_reason = top_reason_tpl.format(
            rel_name=top_rel_name, tier_label=top["tier"]["label"],
            score=top_score, dir_summary=top_dir_summary
        )
        if top_company_level:
            top_reason += stpl.get("fortune_suffix", "，公司今年流年{level}").format(level=top_company_level)

        top_pick = {"name": top.get("name", ""), "reason": top_reason}

        # 方向洞察
        user_mansion = user_yearly.get("your_mansion", {})
        user_element = user_mansion.get("element", "")
        user_mansion_name = user_mansion.get("name_jp", "")
        user_kuyou = user_yearly.get("kuyou_star", {})
        user_level = user_kuyou.get("level", "")
        user_star = user_kuyou.get("name", "")

        insight_parts = []
        if mode == "hr":
            mansion_tpl = stpl.get("insight_company_mansion", "公司本命宿為{mansion}（{element}屬性）")
        else:
            mansion_tpl = stpl.get("insight_user_mansion", "你的本命宿是{mansion}（{element}屬性）")
        if user_element and user_mansion_name:
            insight_parts.append(mansion_tpl.format(mansion=user_mansion_name, element=user_element))

        kuyou_tpl = stpl.get("insight_kuyou", "今年走{star}，運勢等級{level}")
        if user_star and user_level:
            insight_parts.append(kuyou_tpl.format(star=user_star, level=user_level))

        eishin_count = sum(1 for r in results if r["compatibility"]["relation"].get("type") == "eishin")
        total = len(results)
        if eishin_count > 0:
            if mode == "hr":
                eishin_tpl = stpl.get("insight_eishin_hr", "{total} 位候選人中有 {count} 位是栄親關係，與公司契合度高")
            else:
                eishin_tpl = stpl.get("insight_eishin_seeker", "投遞的 {total} 間公司中有 {count} 間是栄親關係，整體組合相當不錯")
            insight_parts.append(eishin_tpl.format(total=total, count=eishin_count))

        dir_counts = {}
        for r in results:
            dd = r["compatibility"]["relation"].get("direction", "")
            if dd:
                dir_counts[dd] = dir_counts.get(dd, 0) + 1
        if dir_counts:
            dominant = max(dir_counts, key=dir_counts.get)
            if dir_counts[dominant] >= 2:
                dom_tpl = stpl.get("insight_dominant", "方向以「{direction}」居多（{count} 位），{summary}")
                insight_parts.append(dom_tpl.format(
                    direction=dominant, count=dir_counts[dominant],
                    summary=direction_summary.get(dominant, "")
                ))

        direction_insight = "。".join(insight_parts) + "。" if insight_parts else ""

        return {
            "top_pick": top_pick,
            "categories": {
                "best_match": best_match,
                "growth_potential": growth_potential,
                "safe_bet": safe_bet,
                "watch_out": watch_out,
            },
            "direction_insight": direction_insight,
        }

    def calculate_lucky_dates(
        self,
        birth_date: date,
        start_date: date | None = None,
        days: int = 30,
    ) -> dict:
        """
        計算吉凶日期清單

        根據個人每日運勢的 career 分數，篩選出吉日和凶日。
        good_dates: career >= 80 且無暗黒/凌犯
        bad_dates: career <= 48 或有安壊/暗黒/凌犯

        Args:
            birth_date: 使用者出生日期
            start_date: 起始日期（預設 today）
            days: 查詢天數

        Returns:
            { good_dates, bad_dates, dark_weeks }
        """
        if start_date is None:
            start_date = date.today()

        weekday_names = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
        good_dates = []
        bad_dates = []
        dark_ranges: list[tuple[date, date]] = []
        current_dark_start: date | None = None

        for i in range(days):
            target = start_date + timedelta(days=i)
            try:
                fortune = sukuyodo_service.calculate_daily_fortune(birth_date, target)
            except Exception:
                continue

            scores = fortune.get("fortune", {})
            career = scores.get("career", 50)
            level = scores.get("level_name", "")
            day_mansion = fortune.get("day_mansion", {})
            mansion_rel = fortune.get("mansion_relation", {})
            sanki = fortune.get("sanki", {})
            ryouhan = fortune.get("ryouhan", {})
            special = fortune.get("special_day")

            is_dark = sanki.get("is_dark_week", False) if sanki else False
            is_ryouhan = ryouhan.get("active", False) if ryouhan else False
            rel_type = mansion_rel.get("type", "") if mansion_rel else ""

            # 暗黒の一週間追蹤
            if is_dark:
                if current_dark_start is None:
                    current_dark_start = target
            else:
                if current_dark_start is not None:
                    dark_ranges.append((current_dark_start, target - timedelta(days=1)))
                    current_dark_start = None

            # 組裝 flags 和 reason
            flags = []
            reasons = []
            if special:
                flags.append(special.get("name", ""))
            if rel_type == "mei":
                flags.append("命宿日")
            if is_dark:
                flags.append("暗黒の一週間")
            if is_ryouhan:
                flags.append("凌犯期間")
            if rel_type == "ankai":
                flags.append("安壊")

            weekday = weekday_names[target.weekday()]

            entry = {
                "date": target.isoformat(),
                "weekday": weekday,
                "career": career,
                "level": level,
                "day_mansion": day_mansion.get("name_jp", ""),
                "relation": mansion_rel.get("name", "") if mansion_rel else "",
                "flags": flags,
                "reason": " + ".join(flags) if flags else level,
            }

            # 吉日: career >= 80 且無負面因素
            if career >= 80 and not is_dark and not is_ryouhan and rel_type != "ankai":
                good_dates.append(entry)
            # 凶日: career <= 48 或有安壊/暗黒/凌犯
            elif career <= 48 or is_dark or is_ryouhan or rel_type == "ankai":
                bad_dates.append(entry)

        # 結尾暗黒期間
        if current_dark_start is not None:
            dark_ranges.append((current_dark_start, start_date + timedelta(days=days - 1)))

        dark_weeks = [
            {"start": s.isoformat(), "end": e.isoformat()}
            for s, e in dark_ranges
        ]

        return {
            "good_dates": good_dates,
            "bad_dates": bad_dates,
            "dark_weeks": dark_weeks,
        }

    def _calculate_tier(
        self,
        compat_score: int,
        company_kuyou_level: str,
        relation_type: str,
        direction: str,
        mode: str = "seeker",
        lang: str = "zh-TW",
    ) -> dict:
        """計算梯隊排名"""
        is_good_fortune = company_kuyou_level in ("大吉", "半吉")
        is_great_fortune = company_kuyou_level == "大吉"
        is_bad_fortune = company_kuyou_level == "大凶"

        if compat_score >= 90 and is_great_fortune:
            rank = 1
        elif (compat_score >= 65 and is_good_fortune) or (compat_score >= 90 and is_good_fortune):
            rank = 2
        elif compat_score >= 90 and is_bad_fortune:
            rank = 3
        else:
            rank = 4

        # 安壊壊方向降一級
        if relation_type == "ankai" and direction == "壊" and rank < 4:
            rank += 1

        css_classes = {1: "tier-1", 2: "tier-2", 3: "tier-3", 4: "tier-4"}

        # 從 JSON 字典檔讀取 tier 標籤（支援多語系）
        json_data = SukuyodoService._load_guidance_json(lang)
        tier_mode = "hr" if mode == "hr" else "seeker"
        tier_data = json_data.get("tiers", {}).get(tier_mode, {}).get(str(rank))

        if tier_data:
            label = tier_data.get("label", f"Tier {rank}")
            reason = tier_data.get("reason", "")
        else:
            # Fallback: 硬編碼中文
            if mode == "hr":
                labels = {1: "高度契合", 2: "良好適配", 3: "特定適配", 4: "需配套安排"}
                reasons = {1: "與公司氣場高度一致，今年時機極佳", 2: "適配度良好，正常安排即可發揮", 3: "有特定專長可發揮，需搭配合適職位", 4: "宿曜相性需較多磨合，依方向建議安排適合的職位仍能貢獻"}
            else:
                labels = {1: "高度適合", 2: "適合發展", 3: "可磨合", 4: "需磨合"}
                reasons = {1: "與公司氣場高度契合，今年時機極佳", 2: "適配度良好，正常準備即可發揮", 3: "有發展空間，但公司今年運勢需留意", 4: "宿曜相性需較多磨合，參考下方原典建議選擇適合的部門"}
            label = labels[rank]
            reason = reasons[rank]

        return {
            "rank": rank,
            "label": label,
            "css_class": css_classes[rank],
            "reason": reason,
        }

    def _build_recommendation(
        self,
        tier: dict,
        score: int,
        company_level: str,
        relation_type: str,
        direction: str,
        mode: str = "seeker",
        lang: str = "zh-TW",
    ) -> dict:
        """產生投遞建議（含方向分析的白話說明）"""
        rank = tier["rank"]
        action_items = []

        if mode == "hr":
            return self._build_recommendation_hr(rank, score, company_level, relation_type, direction, lang)

        # 從 JSON 字典讀取 recommendation 模板
        json_data = SukuyodoService._load_guidance_json(lang)
        rec_data = json_data.get("recommendation", {}).get("seeker", {}).get(str(rank), {})

        # 方向摘要（從 JSON hr_summary 或 fallback 到硬編碼）
        career_summary = SukuyodoService.get_career_summary(direction, lang)

        # 原典引用前綴
        sutra_ref_tpl = json_data.get("recommendation", {}).get("sutra_ref_template", "原典「{sutra}」— ")
        guidance_items = SukuyodoService.get_direction_guidance(direction, "seeker", lang)
        first_sutra = ""
        if guidance_items.get("suitable"):
            first_sutra = guidance_items["suitable"][0].get("sutra", "")
        elif guidance_items.get("timing_poor"):
            first_sutra = guidance_items["timing_poor"][0].get("sutra", "")
        sutra_ref = sutra_ref_tpl.format(sutra=first_sutra) if first_sutra else ""

        # Summary
        prefix = rec_data.get("summary_prefix", tier["label"])
        summary = f"{prefix} — {sutra_ref}{career_summary}"

        # Action items
        for item in rec_data.get("action_items", []):
            action_items.append(item)

        # 方向的具體行動建議
        advice = SukuyodoService.get_action_advice(direction, lang)
        if advice:
            action_items.append(advice)

        # 安壊特別提醒
        ankai_warns = json_data.get("recommendation", {}).get("ankai_warn", {})
        if relation_type == "ankai" and direction == "壊":
            action_items.append(ankai_warns.get("壊_seeker", ""))
        elif relation_type == "ankai" and direction == "安":
            action_items.append(ankai_warns.get("安_seeker", ""))

        return {
            "priority": 0,
            "summary": summary,
            "action_items": [a for a in action_items if a],
        }

    def _build_recommendation_hr(
        self,
        rank: int,
        score: int,
        company_level: str,
        relation_type: str,
        direction: str,
        lang: str = "zh-TW",
    ) -> dict:
        """HR 模式：適才適所建議（每個人都有適合的位置）

        宿曜經的本質是人際關係適才適所，放在對的地方就會發展得很好。
        因此 HR 建議不是「要不要錄用」，而是「放哪裡最好 + 需要什麼配套」。
        """
        action_items = []

        # 從 JSON 字典讀取
        json_data = SukuyodoService._load_guidance_json(lang)
        rec_data = json_data.get("recommendation", {}).get("hr", {}).get(str(rank), {})

        hr_summary_data = json_data.get("hr_summary", {}).get(direction, {})
        hr_summary = hr_summary_data.get("summary", SukuyodoService.get_hr_summary(direction))
        hr_advice = hr_summary_data.get("action_advice", SukuyodoService.get_hr_action_advice(direction))

        # 原典引用
        sutra_ref_tpl = json_data.get("recommendation", {}).get("sutra_ref_template", "原典「{sutra}」— ")
        guidance_items = SukuyodoService.get_direction_guidance(direction, "hr", lang)
        first_sutra = guidance_items["suitable"][0].get("sutra", "") if guidance_items.get("suitable") else ""
        sutra_ref = sutra_ref_tpl.format(sutra=first_sutra) if first_sutra else ""

        prefix = rec_data.get("summary_prefix", "")
        summary = f"{prefix} — {sutra_ref}{hr_summary}"

        for item in rec_data.get("action_items", []):
            action_items.append(item)
        if hr_advice:
            action_items.append(hr_advice)

        ankai_warns = json_data.get("recommendation", {}).get("ankai_warn", {})
        if relation_type == "ankai" and direction == "壊":
            action_items.append(ankai_warns.get("壊_hr", ""))
        elif relation_type == "ankai" and direction == "安":
            action_items.append(ankai_warns.get("安_hr", ""))

        return {
            "priority": 0,
            "summary": summary,
            "action_items": action_items,
        }

    def _get_verdict(self, relation_type: str, direction: str, score: int) -> str:
        """根據關係類型和方向判定推薦等級"""
        if relation_type == "eishin":
            return "推薦"
        if relation_type == "gyotai":
            return "適合"
        if relation_type == "ankai":
            if direction == "壊":
                return "避開"
            return "留意"
        if relation_type == "kisei":
            if direction == "危":
                return "留意"
            return "可考慮"
        if relation_type == "yusui":
            return "留意"
        if relation_type == "mei":
            return "中性"
        # fallback
        if score >= 80:
            return "推薦"
        if score >= 65:
            return "可考慮"
        return "留意"


    # ================================================================
    # 104 公司職缺撈取 + 原典匹配
    # ================================================================

    # 原典方向 → 職缺關鍵字對照表
    _SUTRA_JOB_KEYWORDS: dict[str, list[str]] = {
        "修道學問": ["研發", "工程師", "研究", "實驗", "技術", "分析", "設計", "開發"],
        "學問": ["研發", "工程師", "研究", "實驗", "技術", "分析"],
        "學習進修": ["研發", "工程師", "研究", "實驗", "助理工程師"],
        "考證照": ["品保", "品管", "安全", "環安", "衛生"],
        "成就法": ["專案", "PM", "生管", "管理師", "主管"],
        "合和長年藥法": ["研發", "製程", "長期", "技術"],
        "完成專案": ["專案", "PM", "生管", "管理"],
        "入官拜職": ["主管", "經理", "管理", "幹部", "儲備"],
        "對見大人": ["業務", "行銷", "公關", "企劃", "外貿"],
        "興營買賣": ["業務", "採購", "外貿", "商務", "銷售"],
        "結交": ["人資", "HR", "行政", "公關", "客服"],
        "歡宴聚會": ["公關", "活動", "企劃", "行銷"],
        "婚姻": [],
        "移徙": ["物流", "倉儲", "運輸", "調度"],
        "造作園宅": ["營建", "工程", "設施", "廠務"],
        "裁著新衣": ["設計", "美編", "藝術", "企劃"],
        "療病": ["醫療", "護理", "藥", "衛生", "安全"],
        "降伏": ["法務", "稽核", "審計", "安全"],
        "鎮壓": ["品保", "品管", "稽核"],
    }

    async def fetch_company_jobs(
        self,
        company_name: str,
        birth_date: date,
        founding_date: date,
        lang: str = "zh-TW",
    ) -> dict:
        """
        撈取特定公司的 104 職缺 + 原典方向匹配

        1. 用公司名搜 104
        2. 過濾只保留該公司的職缺
        3. 算相性取 guidance.suitable
        4. 比對每個職缺是否匹配原典方向

        Returns:
            { company_url, jobs: [{ title, location, url, sutra_match, match_reason }] }
        """
        # 1. 搜 104 取該公司的所有職缺（不去重公司）
        search_name = company_name
        for suffix in ["股份有限公司", "有限公司"]:
            search_name = search_name.replace(suffix, "")
        search_name = search_name.strip()

        if not search_name:
            return {"company_url": None, "jobs": []}

        all_jobs = await self._search_104_all_jobs(search_name)

        # 過濾只保留目標公司
        matched_jobs = [
            j for j in all_jobs
            if search_name in j["company_name"]
        ]

        # 2. 查公司頁面 URL
        company_url = await self.lookup_104_company_url(company_name)

        # 3. 算相性取 guidance
        suitable_items: list[dict] = []
        try:
            compat = sukuyodo_service.calculate_compatibility(
                birth_date, founding_date, lang=lang
            )
            da = compat.get("direction_analysis", {})
            guidance = da.get("guidance", {})
            suitable_items = guidance.get("suitable", [])
            # 也取反向
            inv_guidance = da.get("inverse_guidance", {})
            suitable_items += inv_guidance.get("suitable", [])
        except Exception as e:
            logger.warning("相性計算失敗: %s", e)

        # 4. 建立匹配關鍵字集
        match_keywords: list[tuple[str, list[str]]] = []
        for item in suitable_items:
            sutra_text = item.get("sutra", "")
            for sutra_key, job_kws in self._SUTRA_JOB_KEYWORDS.items():
                if sutra_key in sutra_text and job_kws:
                    match_keywords.append((sutra_text, job_kws))
                    break

        # 5. 比對每個職缺（名稱 + 工作內容）
        result_jobs = []
        for job in matched_jobs:
            title = job["job_title"]
            desc = job.get("description", "")
            search_text = f"{title} {desc}"
            sutra_match = False
            match_reason = None

            for sutra_text, kws in match_keywords:
                if any(kw in search_text for kw in kws):
                    sutra_match = True
                    match_reason = sutra_text
                    break

            result_jobs.append({
                "title": title,
                "location": job["location"],
                "url": job["job_url"],
                "sutra_match": sutra_match,
                "match_reason": match_reason,
            })

        # 推薦排前面
        result_jobs.sort(key=lambda j: (not j["sutra_match"], j["title"]))

        return {
            "company_url": company_url,
            "jobs": result_jobs,
        }

    async def _search_104_all_jobs(
        self,
        keyword: str,
        area: str = "",
        pages: int = 3,
    ) -> list[dict]:
        """搜 104 職缺，不做公司去重（保留同公司多職缺）"""
        results = []
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for page in range(1, pages + 1):
                params = {"keyword": keyword, "page": str(page), "pagesize": "30"}
                if area:
                    params["area"] = area
                headers = {
                    **_104_HEADERS,
                    "Referer": f"https://www.104.com.tw/jobs/search/?keyword={quote(keyword)}&area={area}",
                }
                try:
                    resp = await client.get(_104_SEARCH_URL, params=params, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    logger.warning("104 搜尋第 %d 頁失敗: %s", page, e)
                    continue

                job_list = data.get("data", [])
                if not job_list:
                    break

                for job in job_list:
                    cust_name = job.get("custName", "").strip()
                    if not cust_name:
                        continue
                    link = job.get("link", {})
                    job_url = link.get("job", "")
                    if job_url and not job_url.startswith("http"):
                        job_url = f"https://www.104.com.tw/job/{job_url}"
                    results.append({
                        "company_name": cust_name,
                        "job_title": job.get("jobName", "") or job.get("jobNameSnippet", ""),
                        "location": job.get("jobAddrNoDesc", "") or job.get("jobAddress", ""),
                        "job_url": job_url,
                        "description": job.get("description", ""),
                    })

        return results


company_search_service = CompanySearchService()
