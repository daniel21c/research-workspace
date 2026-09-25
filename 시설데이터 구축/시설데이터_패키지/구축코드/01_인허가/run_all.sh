#!/bin/bash
# 모든 유형 빌드(순차). 사용: bash run_all.sh [유형 ...]
cd "$(dirname "$0")"
TYPES=${@:-의원 병원급 약국 산후조리업 안전상비의약품판매업소 안경업 동물병원 체육시설업 공연장 영화상영관 대규모점포 식료품소매 이용업 미용업 세탁업 목욕장업 주유소 휴게음식점 일반음식점}
for T in $TYPES; do (cd "$T" && echo "== $T $(date -u +%T)" && python3 -W ignore "build_$T.py") ; done
