# 이 저장소의 Antigravity 작업 규칙

상위 `D:\Research\GEMINI.md`의 기존 모델 정책을 유지합니다. 최신 사용자 승인 범위와 [공통 인수인계](공통_작업_인수인계.md), 해당 하위 `GUIDELINE_*.md`, [자동 기록 절차](.research-sync/README.md)를 읽습니다.

사용자가 승인한 인수인계 자동 갱신·작업별 로컬 자동 커밋은 **단일 파일 담당 에이전트가 직접 명령을 실행**합니다. 앱 DB·대화 원문을 옮기거나 내부 추론을 공유하지 않습니다. Codex 모델 라우팅을 Antigravity 모델 설정으로 가져오지 않습니다.

1. 편집 전에 지정 Python으로 `tools/research_sync.py begin --app antigravity --task <새 고유ID>`를 실행합니다.
2. 이번 승인 범위의 정확한 상대경로만 `claim --task <ID> <경로...>`로 편집 전에 선언합니다. 다른 작업자의 기존 변경·미추적 파일을 자신의 것으로 채택하지 않습니다.
3. 실제 작업·검증 뒤 `note`에 변경·결정, 근거, 미해결 사항, 다음 단계를 기록하고 `verify`에 이미 수행한 검증 결과를 선언합니다.
4. `finish --dry-run` 확인 후 `finish`, `status`를 실행합니다. 중단은 `--outcome interrupted`, 불명은 `--outcome unknown`입니다. 보류 사유를 알리고 포괄적 Git 명령으로 우회하지 않습니다.

정확한 명령 예시는 자동 기록 절차에 있습니다. 이 방식은 에이전트 규칙 준수에 의존하며 네이티브 Antigravity 완료 hook/상시 감시를 설치한 것이 아닙니다. 종료 문장만으로 과학적 검증 완료를 선언하지 않습니다. 자동 원격 전송, 스케줄러·서비스·Git hook 설치, 원자료 변경 권한은 추가되지 않습니다.
