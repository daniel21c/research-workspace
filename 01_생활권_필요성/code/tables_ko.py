# -*- coding: utf-8 -*-
"""영문 표(code/manuscript_src/tables/*.md)를 한국어 표(tables_ko/)로 옮긴다. fig_manuscript.py로 표를 다시 만든 뒤 실행."""
import re
from pathlib import Path
SRC = Path(__file__).parent / "manuscript_src"; A = SRC / "tables"; B = SRC / "tables_ko"; B.mkdir(exist_ok=True)
M = [
("# Table 1. Planning hierarchy of Seoul.", "# 표 1. 서울의 계획 위계."),
("# Table 2. Planned public-service bundle: Domains, facility cells and placement budget.", "# 표 2. 계획 공공서비스 묶음: 분야, 시설 격자, 배치 추가량."),
("# Table 3. Bundle completion rate by walking-time threshold (% of residents).", "# 표 3. 보행 시간 문턱별 묶음 완결률(주민 %)."),
("# Table 4. Three report cards by placement rule.", "# 표 4. 배치 규칙별 세 성적표."),
("Note: ", "주: "),
("Greedy placement. Access-poor: residents in the cells with the poorest pre-placement neighbourhood access (top 20%, ties included). Thresholds: library 15 min, public kindergarten 10 min.", "탐욕 배치. 접근 취약: 배치 전 주변 접근이 가장 나쁜 격자의 주민(상위 20%, 동률 포함). 문턱: 도서관 15분, 국공립유치원 10분."),
("Facility-by-facility planning and bundle maximisation are exact integer programmes (gap 0); the coordinated rule is greedy; the minimum standards are integer programmes solved within time limits (living zones 4 h, gu and dong 1.5 h; Table A.1). Bottom-20: residents who reached the fewest domains before placement.", "시설별 계획과 묶음 최대화는 정확한 정수계획(갭 0), 조정 규칙은 탐욕법, 최저선은 시간 제한 정수계획(생활권 4시간, 자치구·행정동 1.5시간; 표 A.1). 하위 20%: 배치 전 닿는 분야가 가장 적은 주민."),
("# Table 1 Planning hierarchy of Seoul", "# 표 1 서울의 계획 위계"),
("Mean population (2024)", "평균 인구(2024)"), ("Population range", "인구 범위"), ("Mean area (km²)", "평균 면적(km²)"),
("| Unit |", "| 단위 |"), ("| Number |", "| 개수 |"), ("Official living zone", "공식 생활권"), ("Administrative dong", "행정동"), ("Grid cell (100 m, populated)", "격자(100 m, 인구 있음)"), ("| Gu |", "| 자치구 |"),
("Each living zone contains 3.7 dong on average (range 1–7); each gu contains 4.6 living zones (range 3–7).", "생활권 하나는 평균 3.7개 행정동(1~7개)을, 자치구 하나는 평균 4.6개 생활권(3~7개)을 담는다."),
("# Table 2 Planned public-service bundle: domains, facility cells and placement budget", "# 표 2 계획 공공서비스 묶음: 분야, 시설 격자, 배치 추가량"),
("N = net increase in facility-occupied 100 m cells, 2020→2025 (total 381). Park layer: 2018 living-zone plan layer, fixed for both years. Youth and children = youth centres ∪ community child centres (current list, fixed). Childcare cells count all childcare centres, public and private, and fell as private centres closed; the budget counts public centres only.", "N = 시설이 있는 100 m 격자의 2020~2025년 순증(합계 381). 공원 층은 2018년 생활권계획 층으로 두 시점 고정. 청소년아동 = 청소년수련시설 ∪ 지역아동센터(현재 목록, 고정). 보육 격자는 국공립·민간 어린이집 전체를 세며, 민간 폐원으로 줄었다. 배치 추가량은 국공립만이다."),
("| Domain |", "| 분야 |"), ("Facility cells 2020", "시설 격자 2020"), ("Facility cells 2025", "시설 격자 2025"), ("Placed type (N)", "배치 유형(N)"),
("fixed (not placed)", "고정(배치 안 함)"), ("Public library (31)", "공공도서관 (31)"), ("Senior facility (93)", "노인이용시설 (93)"), ("Youth centre (11)", "청소년수련시설 (11)"), ("Public childcare centre (200)", "국공립어린이집 (200)"), ("Public sports facility (46)", "공공체육시설 (46)"),
("| Park |", "| 공원 |"), ("| Public library |", "| 공공도서관 |"), ("| Senior leisure |", "| 노인여가 |"), ("| Youth and children |", "| 청소년아동 |"), ("| Childcare |", "| 보육 |"), ("| Public sports |", "| 공공체육 |"),
("# Table 3 Bundle completion rate (% of residents) by walking-time threshold", "# 표 3 보행 시간 문턱별 묶음 완결률(주민 %)"),
("| Bundle |", "| 묶음 |"), (" 10 min", " 10분"), (" 15 min", " 15분"), ("Logan et al. 4 amenities", "Logan et al. 4개 편의시설"), ("Everyday functions (7 categories)", "일상 기능(7개 범주)"), ("Planned public services (6 domains)", "계획 공공서비스(6개 분야)"),
("# Table 4 Three report cards by placement rule", "# 표 4 배치 규칙별 세 성적표"),
("## (a) Single facilities (library, public kindergarten)", "## (a) 단일 시설(도서관, 국공립유치원)"), ("## (b) Six-domain bundle (10 min)", "## (b) 6개 분야 묶음(10분)"),
("Greedy placement. Access-poor: residents in the cells with the poorest pre-placement neighbourhood access (top 20%, ties included). Thresholds: library 15 min, public kindergarten 10 min.", "탐욕 배치. 접근 취약: 배치 전 주변 접근이 가장 나쁜 격자의 주민(상위 20%, 동률 포함). 문턱: 도서관 15분, 국공립유치원 10분."),
("Facility-by-facility planning and bundle maximisation are exact integer programmes (gap 0); the coordinated rule is greedy; the minimum standards are integer programmes solved within time limits (living zones 4 h, gu and dong 1.5 h; Table A.1). Bottom-20: residents who reached the fewest domains before placement.", "시설별 계획과 묶음 최대화는 정확한 정수계획(갭 0), 조정 규칙은 탐욕법, 최저선은 시간 제한 정수계획(생활권 4시간, 자치구·행정동 1.5시간; 표 A.1). 하위 20%: 배치 전 닿는 분야가 가장 적은 주민."),
("| Rule |", "| 규칙 |"), ("| Facility |", "| 시설 |"), (" total access (%)", " 총량 접근(%)"), (" access-poor reached (%)", " 접근 취약 도달(%)"), (" living zones below minimum", " 최저선 미달 생활권"),
(" completion (%)", " 완결률(%)"), (" bottom-20 (%)", " 하위 20%(%)"), (" zero-completion zones", " 0명 생활권"),
("Living-zone minimum + access-poor weighting", "생활권 최저선 + 접근 취약 가중"), ("Grid access-poor weighting", "격자 접근 취약 가중"), ("Grid efficiency", "격자 효율"),
("| Library |", "| 도서관 |"), ("| Public kindergarten |", "| 국공립유치원 |"),
("Grid: facility-by-facility (exact)", "격자: 시설별 계획(정확해)"), ("Grid: bundle maximisation (exact)", "격자: 묶음 최대화(정확해)"), ("Grid: coordinated (P=2)", "격자: 조정(P=2)"),
("Living-zone minimum 5%", "생활권 최저선 5%"), ("Gu minimum 5%", "자치구 최저선 5%"), ("Dong minimum 5%", "행정동 최저선 5%"),
("Living-zone minimum", "생활권 최저선"), ("Gu minimum", "자치구 최저선"),
]
for f in sorted(A.glob("Table*.md")):
    t = f.read_text(encoding="utf-8")
    for a, b in M: t = t.replace(a, b)
    left = sorted(set(w for w in re.findall(r"[A-Za-z]{4,}", t) if w not in ("Logan", "Table")))
    (B / f.name).write_text(t, encoding="utf-8"); print(f.name, left)
