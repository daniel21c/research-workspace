# Applied Geography 구성 변경 검수 종결

## 판정

**구성 변경 검수 종결.** 커밋 `73be0232017fb4c89d92cb10e67f90925202b0c1` 및 이에 대응하는 첨부 패키지에서 구성 변경 검수 A·B·C의 반영을 확인했다. 세 문단의 검토 대상이었던 출처 요약과 해석 범위 문제가 해소됐으며, 이 범위에서 추가 문장 수정 요구는 없다. 이전에 종결한 문장 검수를 다시 열지 않는다. 이후 절차는 저자 확인 및 제출 승인 단계로 이관한다.

이 판정은 A·B·C 문단에 관한 후속 검수이며, 전체 연구의 재현성·참고문헌 전체·공개권리·저자 승인·저널 형식을 새로 승인한 것이 아니다.

## 확인 대상 고정

- 저장소: `daniel21c/research-workspace`
- 원고 커밋: `73be0232017fb4c89d92cb10e67f90925202b0c1`
- 첨부 ZIP: `AG_확정본_공동연구자패키지_20260930_73be023.zip`
- ZIP 크기: 22,903,560 bytes
- ZIP SHA-256: `a80744e39bcfb6e2f913a9e3ee0c3bd5b0643b938185e2f44280eeca35853809`
- ZIP Git blob SHA-1: `2ee997c229e5e9253120e680271c082fc0edbf9d` — 지정 커밋의 GitHub 메타데이터와 일치.
- 영문 소스: ZIP의 CRLF 줄바꿈을 LF로 정규화하면 지정 커밋의 Git blob `0c6b85938ec9689791435fdb8b6301abe9b48830`와 일치. 줄바꿈을 제외한 내용이 동일함을 확인.

## A·B·C 판정

| 항목 | 영문 코드 위치 | 실제 영문 PDF 위치 | 판정 |
|---|---|---|---|
| A — 해외 영역 계획 사례 | `a06_text_en.py` 43–52행 | 2–3쪽, 인쇄 줄번호 38–50 | 해결. 베를린의 사회·인구 계획/관측 역할, 런던의 당시 모니터링·조정 역할, 시드니의 2018년 접근 목표를 구분하고, 규모와 제도적 기능 차이 및 공통 서비스 보장이 아님을 명시. |
| B — Q3 선행연구 요약 | 같은 파일 153–161행 | 8쪽, 인쇄 줄번호 175–185 | 해결. Alexander의 HBW/HBO/NHB 큰 목적 구분과 Graells-Garrido의 목적지 교육·소매 접근성 연관 및 지역별 변이를 원문 범위에서 서술. 선행연구가 경계 재배정의 누락 감소를 함의하지 않는다는 한정 유지. |
| C — 공존과 기전 구분 | 같은 파일 345–353행 | 20쪽, 인쇄 줄번호 436–446 | 해결. 범주별 부호와 관계의 크기를 기술하고, 선택된 개별 재배정과 연결해 분석하지 않았음을 명시. 기전의 부정이 아니라 기전 미입증으로 정리. |

B의 조건부 연결 `If … may …`는 §2.4 안의 직접적인 한정과 §2.5의 “양의 연관만으로 누락 감소를 함의하지 않는다”는 설명과 함께 읽으면 연구 동기를 제시하는 문장이다. 추가 수정 요구 없음.

## 대조에 사용한 자료와 확인 범위

- 베를린: Berlin.de 공식 LOR 설명의 사회·인구 변화 계획·예측·관측 역할을 직접 확인.
- 런던: 공식 Policy 2.5 검색 색인의 §2.24 발췌에서 법정 모니터링과 권역 조정을 확인. 공식 전문 페이지는 403을 반환하여 이번에 전문 전체를 다시 읽었다고 주장하지 않는다.
- 시드니: 2018 계획을 구현하는 Randwick City Council의 공식 설명에서 세 도시·30분 목표와 2018년 확정된 다섯 지구계획을 확인. 원 계획 PDF는 웹 도구의 크기 제한 때문에 전문 재독하지 않았다.
- Alexander et al. (2015): 공저자가 공개한 원논문 전문 중 §2.3과 §2.5 확인. §2.5의 세 통행 목적은 HBW/HBO/NHB이고, §2.3에서 더 상세한 활동 분류는 후속 연구로 남김.
- Graells-Garrido et al. (2021): PLOS 게재본문의 초록 및 Results 확인. 전역의 교육·소매 목적지 접근성 연관과 지역별 부호·크기 변이를 확인.
- C: 본 원고 §4.4 및 §3.4의 분석 범위와 대조. 원고 데이터로 기전 유무를 새로 검정한 것은 아님.

출처:
1. https://www.berlin.de/sen/stadt/stadtdaten/stadtwissen/sozialraumorientierte-planungsgrundlagen/lebensweltlich-orientierte-raeume/
2. https://www.london.gov.uk/programmes-strategies/planning/london-plan/past-versions-and-alterations-london-plan/london-plan-2016/london-plan-chapter-two-londons-places/policy-25
3. https://www.yoursay.randwick.nsw.gov.au/Vision2040/background-to-vision-2040
4. https://www.researchgate.net/publication/273480107_Origin-destination_trips_by_purpose_and_time_of_day_inferred_from_mobile_phone_data
5. https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0250080

## 산출물 일관성 확인

- 새 폴더 추출 후 `a07_claims_check.py` 직접 실행: 종료 코드 0, 136/136 통과. 56개 저장 결과표 기반 값 대조 + 80개 원고 반영/자리표시 검사.
- MANIFEST 기재 85개 파일: 크기와 SHA-256 모두 일치.
- 직전 `68178a4`와 공통 저장 결과 37개: 바이트 동일. `values_used.json` 동일.
- 본문 표 4개의 셀 텍스트: 직전 판과 동일. 공통 그림·제출그림 파일 19개: 바이트 동일. 초록·하이라이트 소스 값: 동일.
- 영문 소스의 제목·본문·수식 70개 블록: 실제 DOCX 문단과 일치. 초록과 하이라이트 5개도 일치(Word 표시용 글머리표는 제외).
- 별도 첨부 영문·한국어 PDF: ZIP 내부 해당 PDF와 바이트 동일.
- 초록 직접 계수: 249단어. 하이라이트 최대: 82자. 참고문헌 항목 수: 51개.
- 생성 코드의 `word_count.json` 기록: 7,912단어. 모든 DOCX 문단과 표 셀을 공백 기준으로 별도 계수: 7,990단어.
- 한국어 §5.2의 조정 우월성 잔여 문구 삭제 확인. 첨부 교수님 보고 메모의 지정된 옛 결론·Q3 요약 삭제, 7,912단어·51편 및 `73be023` 참조 반영 확인. 보고 메모 전체 내용의 별도 감사는 수행하지 않음.
- 영문 PDF 2·8·20쪽의 대상 문단을 렌더링하여 읽음. 전체 PDF의 시각 QA를 새로 완료했다고 주장하지 않음.

## 남은 단계

공저자 명단·순서와 최종판 승인, 연구비, CRediT, 실제 AI 사용 범위의 고지 확정, 데이터·코드 공개권리, 선행발표·저작권, 최종 저널 형식 및 제출 승인은 별도 게이트다. 이는 이번 A·B·C 문단의 미해결 지적이 아니다.

세부 기계 점검 기록: `AG_73be023_structure_closure_checks_20260930.json`.
