# jodalfit · Logo 10 Halves

채워진 삼각형(회사 이력) + 윤곽 삼각형(공고)이 대각선을 따라 정확히 맞물려 하나의 사각형이 되는 형태. Fill과 Stroke의 대비가 “두 조각이 들어맞는다”는 메시지의 핵심입니다.

## 파일 구성

```
symbol/
  jodalfit-symbol-color.svg   #166534 (Primary Green)
  jodalfit-symbol-ink.svg     #18181B (Ink, 1색 인쇄용)
  jodalfit-symbol-white.svg   #FFFFFF (다크 배경용)

wordmark/
  jodalfit-wordmark-color.svg
  jodalfit-wordmark-ink.svg
  jodalfit-wordmark-white.svg
```

## 사양

- **viewBox**: 200 × 200 (심볼), 720 × 200 (워드마크)
- **Triangles**: (35,35)–(165,35)–(35,165) 채움 + (165,35)–(165,165)–(35,165) 윤곽
- **Stroke**: 9px · `stroke-linejoin="miter"` (모서리 정밀도)
- **Color tokens**: Primary `#166534` · Ink `#18181B` · Surface `#FFFFFF`
- **Wordmark font**: Manrope 700 (fallback: Pretendard, system-ui)

## 사용 시 주의

1. **Fill / Stroke 관계 절대 유지** — 두 삼각형이 동일 fill이거나 동일 stroke가 되면 의미 소실. 항상 “하나는 채움, 하나는 윤곽”이어야 함
2. **클리어 스페이스**: 심볼 주변에 35px(@ 200 grid = 17.5%) 여백 유지
3. **최소 사이즈**: 24px 이하에서 stroke-width를 7px로 옵티컬 조정 별도 버전 권장
4. **회전·뒤집기 금지** — 대각선 방향이 좌상→우하로 고정. 변경 시 가시성과 의미가 바뀜
5. **워드마크 폰트**: 최종 배포 전 텍스트를 outline path로 변환 권장
6. **컬러**: Primary Green / Ink / White 외 사용 금지. 그라데이션·드롭섀도 금지

## 라이센스

내부 브랜드 자산. 외부 사용은 별도 승인 필요.
