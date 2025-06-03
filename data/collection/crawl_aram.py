# -*- coding: utf-8 -*-
"""
이 스크립트는 서울아산병원 홈페이지 건강정보 > 수술/치료 후 관리 게시물에서
'퇴원 후 주의사항' 관련 문장을 자동 수집하여 CSV 파일로 저장합니다.

[사용 라이브러리]
- Selenium: 4.33.0
- BeautifulSoup: 4.13.4
- csv, re, os, time 등 기본 모듈

[수집 방식]
- 부위별 관리 항목 리스트 페이지에서 각 항목의 상세페이지 URL 수집
- 상세 페이지 내 '주의사항' 섹션(dl.descDl > dt 포함)에 해당하는 dd 텍스트만 추출
- 문장은 마침표(.), 물음표(?), 느낌표(!) 기준으로 나누되 한글 포함 문장만 필터링
- 중복 링크 제거 및 비어 있는 항목 제외
- 수집된 문장마다 ID, URL, 수집자명 등 메타정보 포함하여 리스트 구성

[저장 포맷]
- id: 문장 고유 번호 (3자리 숫자)
- original_text: 추출된 원문 문장
- simple_text: 리라이팅될 쉬운 문장 (초기값은 빈 문자열)
- source: 원문 상세 페이지 URL
- collector: 수집자 이름

[수작업 후처리]
- 수집된 문장은 이후 별도로 직접 정제
- simple_text 컬럼은 사람이 직접 리라이팅하여 채움
- 필요 시 category 필드 수동 추가 가능

[출력 파일]
- asan_management_sentences.csv
- 파일이 이미 열려 있거나 권한 문제가 있을 경우 에러 출력
"""

import os
import re
import csv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

# —————— 설정 ——————
BASE_MAIN_URL        = "https://www.amc.seoul.kr/asan/healthinfo/management/managementSubmain.do"
CATEGORY_SELECTOR    = "a[href*='managementList.do?partId=']"
DETAIL_LIST_SELECTOR = "strong.contTitle a"
DETAIL_DL_SELECTOR   = "dl.descDl"
DOMAIN               = "https://www.amc.seoul.kr"

FIELDNAMES = ["id", "original_text", "simple_text", "source", "collector"]
COLLECTOR  = "조아람"

OUTPUT_FILE = "asan_management_sentences.csv"
# ——————————————————————————


def split_sentences(text: str) -> list[str]:
    """
    마침표(.), 물음표(?), 느낌표(!) 뒤에서만 분리하고
    한글이 포함된 문장만 반환합니다.
    """
    parts = re.split(r'(?<=[\.\!?])\s+', text)
    return [p.strip() for p in parts if re.search(r'[가-힣]', p)]


def extract_caution(soup: BeautifulSoup) -> str:
    """
    dl.descDl 아래 dt/dd 페어 중 dt에 '주의'가 들어간 곳의 dd 텍스트만 반환.
    """
    dl = soup.select_one(DETAIL_DL_SELECTOR)
    if not dl:
        return ""
    for dt in dl.find_all('dt'):
        if '주의' in dt.get_text():
            dd = dt.find_next_sibling('dd')
            if dd:
                return dd.get_text(separator=" ", strip=True)
    return ""


def main():
    # 0) 기존 파일 잠금 해제
    if os.path.exists(OUTPUT_FILE):
        try:
            os.remove(OUTPUT_FILE)
        except PermissionError:
            print(f"{OUTPUT_FILE} 파일이 열려 있어 삭제할 수 없습니다. 먼저 닫아 주세요.")
            return

    # 1) Selenium 드라이버 설정
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.page_load_strategy = 'eager'
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait   = WebDriverWait(driver, 5)

    # 2) 부위별 카테고리 링크 수집
    driver.get(BASE_MAIN_URL)
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, CATEGORY_SELECTOR)))
    cat_elems = driver.find_elements(By.CSS_SELECTOR, CATEGORY_SELECTOR)
    categories = []
    seen = set()
    for el in cat_elems:
        href = el.get_attribute('href')
        if not href:
            continue
        url = href if href.startswith('http') else DOMAIN + href
        if url not in seen:
            seen.add(url)
            categories.append(url)

    results = []
    idx = 1

    # 3) 카테고리별·페이지별 순회
    for cat_url in categories:
        page = 1
        while True:
            driver.get(f"{cat_url}&pageIndex={page}")
            try:
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, DETAIL_LIST_SELECTOR)))
            except TimeoutException:
                break

            detail_els = driver.find_elements(By.CSS_SELECTOR, DETAIL_LIST_SELECTOR)
            detail_urls = []
            for el in detail_els:
                try:
                    href = el.get_attribute('href')
                except StaleElementReferenceException:
                    continue
                if href:
                    detail_urls.append(href if href.startswith('http') else DOMAIN + href)
            if not detail_urls:
                break

            # 4) 상세 페이지 방문 → '주의사항' 추출 → 문장 분리 → 결과 추가
            for detail_url in detail_urls:
                driver.get(detail_url)
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, DETAIL_DL_SELECTOR)))
                except TimeoutException:
                    continue

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                orig_text = extract_caution(soup)
                for sent in split_sentences(orig_text):
                    results.append({
                        'id':            f"{idx:03}",
                        'original_text': sent,
                        'simple_text':   "",              # 비워둠
                        'source':        detail_url,       # 해당 상세 페이지 URL 사용
                        'collector':     COLLECTOR
                    })
                    idx += 1

                time.sleep(0.1)

            page += 1

    driver.quit()

    # 5) CSV 저장
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(results)
    except PermissionError:
        print(f"{OUTPUT_FILE}에 쓸 수 없습니다. 디스크 권한을 확인해 주세요.")
        return

    print(f"완료: 총 {len(results)}건 → {OUTPUT_FILE}")
    print("저장 위치:", os.path.abspath(OUTPUT_FILE))

if __name__ == "__main__":
    main()
