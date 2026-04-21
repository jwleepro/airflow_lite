# PROGRESS.md

## 현재 상태 요약

- 파이프라인 정의 source of truth는 DAG 파일(`dags/*.py`) 기준으로 문서화 완료
- 운영 문서에서 Admin UI pipeline 등록 절차를 제거하고 DAG 배포 절차로 전환 완료

## 최근 완료 작업

## 진행 중

- 없음

## 다음 작업

- DAG 기반 discovery rule(`all/prefix/contains/suffix`)을 DAG 정의 레이어에서 설계 및 구현

## 블로커 및 리스크

- 문서 기준은 정리되었으나, discovery rule 기능 자체는 아직 미구현

## 검증 메모

- 문서 정합성 점검:
  - `README.md`와 사용자 매뉴얼에서 DAG-first 정의 모델 문구 반영 확인
  - Admin 화면 pipeline CRUD 제거 상태와 문서 설명 일치 확인

## 인수인계

- 후속 구현 시 pipeline 등록 기능을 Admin UI로 되돌리지 말고 DAG API/로더 확장으로 진행
