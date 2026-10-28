# 2027 연차 꿀조합

연차 개수를 넣으면 2027년 공휴일과 대체공휴일에 맞춰 가장 길게 쉬는 연차 조합을 짜 주는 웹 계산기입니다.

- `index.html`: 계산기 (정적 페이지, GitHub Pages로 배포)
- `diary/make_diary.py`: 연차 계획이 표시된 굿노트용 다이어리 PDF 생성기
  - `python3 diary/make_diary.py --leave 15 --out diary-15.pdf` (reportlab 필요)
  - 폰트: IBM Plex Sans KR, Black Han Sans (SIL Open Font License)

공휴일 기준: 2026년 10월 관공서 공휴일 규정(노동절·제헌절 포함, 대체공휴일 반영).
