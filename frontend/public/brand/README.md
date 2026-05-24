# jodalfit · Logo 09 Registration

조달 문서·정밀 인쇄의 시각 어휘를 차용한 로고. 네 모서리 등록 마크가 중앙의 도트(매칭된 1개)를 정렬·고정합니다.

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
- **Stroke**: 10px @ 200 grid · `stroke-linecap="butt"` 고정
- **Center dot**: r = 13
- **Color tokens**: Primary `#166534` · Ink `#18181B` · Surface `#FFFFFF`
- **Wordmark font**: Manrope 700 (fallback: Pretendard, system-ui)

## 사용 시 주의

1. **클리어 스페이스**: 심볼 주변에 모서리 마크 길이(35px @ 200 grid = 17.5%) 만큼 여백 유지
2. **최소 사이즈**: 24px 이하에서는 stroke-width를 8px로 옵티컬 조정한 별도 버전 권장
3. **워드마크 폰트**: 최종 배포 전 텍스트를 outline path로 변환 권장 (Manrope 미설치 환경에서 fallback 폰트로 렌더링됨)
4. **컬러**: Primary Green과 Ink 외 색상 사용 금지. 그라데이션·드롭섀도·3D 효과 금지
5. **변형 금지**: 모서리 마크의 길이·각도, 중앙 도트의 크기·위치는 절대 변경 금지

## 라이센스

내부 브랜드 자산. 외부 사용은 별도 승인 필요.
