"""
이 스크립트는 서울대병원 홈페이지에 게시된 수술치료 게시물 중 '퇴원 후 주의사항' 관련 글을 크롤링하여
원문 문장을 수집하고 카테고리를 매핑한 뒤 CSV 파일로 저장하는 작업을 수행합니다.

[사용 라이브러리]
- Selenium: 4.33.0
- BeautifulSoup: 4.13.4
- pandas: 2.2.3

[수집 방식]
- 게시글 번호를 기반으로 게시글 URL 구성
- 제목에 '퇴원'과 '주의' 키워드가 포함된 글만 추출
- 본문 중 마침표 없는 짧은 문장을 중간 제목(category)으로 간주
- 해당 카테고리 아래의 문장들을 마침표 기준으로 분할 후 수집
- 그림 설명 등 불필요한 내용은 제외
- 각 문장에는 ID, 카테고리, URL, 수집자 정보 등을 포함
- 수집된 카테고리는 비슷한 항목으로 통일

[저장 포맷]
- id: 문장 고유 번호
- category: 안내 카테고리 (ex. 식사, 운동, 병원 방문 등)
- original_text: 수집된 원문 문장
- simple_text: 리라이팅될 쉬운 문장 (초기값 "추가 예정")
- source: 원문 URL
- collector: 수집자 이름

[수작업 후처리]
- 수집한 문장은 크롤링 이후 직접 정제함
- simple_text 컬럼은 직접 리라이팅하여 채워넣음
"""


import csv
import re
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# 크롤링 설정
URL_BASE = "https://www.snuh.org/board/B016/view.do?bbs_no="
fieldnames = ["id", "category", "original_text", "simple_text", "source", "collector"]
output_rows = []
id_counter = 1

# 중복 카테고리 매핑
category_to_intent = {
    "식사": "식사", "식이": "식사", "식사와 영양": "식사",
    "운동": "운동", "운동 및 활동": "운동", "골반근육 강화운동": "운동", "골반근육강화운동": "운동",
    "목욕 및 샤워": "목욕 및 샤워", "상처관리 및 샤워": "목욕 및 샤워",
    "상처 관리": "상처 관리",
    "통증 관리": "통증 관리", "통증관리": "통증 관리",
    "일상생활": "일상생활", "흡연과 음주": "일상생활",
    "병원방문": "병원 방문", "병원을 방문해야 할 상황": "병원 방문",
    "배변과 좌욕": "배변 및 배뇨", "배뇨": "배변 및 배뇨", "요실금": "배변 및 배뇨",
    "복압성 요실금": "배변 및 배뇨", "소변줄을 가지고 퇴원하는 경우": "배변 및 배뇨",
    "장유착": "주의사항", "림프부종 예방": "주의사항", "복대": "주의사항",
    "안전관리": "주의사항", "발기부전": "주의사항", "기타": "주의사항",
    "장애인 등록": "장애인 등록"
}

# 크롤링 실행
for bbs_no in range(3580, 3612):  # 수집 범위
    try:
        url = URL_BASE + str(bbs_no)
        driver = webdriver.Chrome()
        driver.get(url)
        time.sleep(2)

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        title_elem = soup.select_one("div.viewTitle > h3")
        if not title_elem:
            print(f"[{bbs_no}] 제목 없음, 건너뜀")
            driver.quit()
            continue

        title = title_elem.get_text(strip=True)
        if "퇴원" not in title or "주의" not in title:
            print(f"[{bbs_no}] 제목 조건 불충족, 건너뜀")
            driver.quit()
            continue

        source_string = url
        content_div = soup.select_one("div.viewContent")
        if not content_div:
            print(f"[{bbs_no}] 본문 없음, 건너뜀")
            driver.quit()
            continue

        current_category = None
        for p in content_div.find_all("p"):
            text = p.get_text(strip=True).replace('\xa0', ' ').strip()

            if not text or "그림" in text:
                continue

            # 카테고리 판단
            if len(text) <= 20 and '.' not in text:
                current_category = text
                continue

            if current_category:
                clean_text = text.lstrip("• ").strip()
                sentences = [s.strip() for s in re.split(r'\.\s*', clean_text) if s.strip()]
                for sentence in sentences:
                    output_rows.append({
                        "id": id_counter,
                        "category": current_category,
                        "original_text": sentence + ".",
                        "simple_text": "추가 예정",
                        "source": source_string,
                        "collector": "김하영"
                    })
                    id_counter += 1

        print(f"[{bbs_no}] 처리 완료: {title}")

    except Exception as e:
        print(f"[{bbs_no}] 오류 발생: {e}")
    finally:
        driver.quit()

# Pandas로 후처리
df = pd.DataFrame(output_rows)

# category 정리
df["category"] = df["category"].map(category_to_intent)

# 유효한 문장만 남기고, 중복 제거
df = df[df["original_text"].notna() & (df["original_text"].str.strip() != "")]
df = df.drop_duplicates(subset=["original_text"]).reset_index(drop=True)

# 기존 id 컬럼이 있으면 제거
if "id" in df.columns:
    df = df.drop(columns=["id"])
    
# 새 id 부여
df.insert(0, "id", df.index + 1)

# 저장
df.to_csv("process_data_hy.csv", index=False, encoding="utf-8")
print(f"\n최종 저장 완료: data.csv (총 {len(df)}개 문장)")