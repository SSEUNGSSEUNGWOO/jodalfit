/**
 * 사이트맵 세그먼트 구성. `app/sitemap.ts`와 `app/robots.ts`가 공유한다.
 *
 * 한 파일에 담을 수 있는 URL은 5만 개인데 색인 대상 회사만 55,775개(2026-08-22)라
 * generateSitemaps로 쪼갠다. 세그먼트가 나뉘면 GSC가 묶음별 색인률을 따로
 * 보고하므로 어느 구간이 색인되는지도 처음으로 측정할 수 있다.
 *
 * 회사 수가 COMPANY_SEGMENTS * PER_SEGMENT를 넘으면 COMPANY_SEGMENTS를 늘릴 것.
 * 확인: select count(*) from companies where embedding is not null;
 */
export const PER_SEGMENT = 10000;

/** 회사: id 0 ~ COMPANY_SEGMENTS-1 */
export const COMPANY_SEGMENTS = 6;

/** 공고: 진행 중 공고(약 9,800건)를 덮도록 한 세그먼트 */
export const NOTICE_SEGMENT_ID = COMPANY_SEGMENTS;

/** 정적 라우트 + 인사이트 */
export const STATIC_SEGMENT_ID = COMPANY_SEGMENTS + 1;

export const TOTAL_SEGMENTS = STATIC_SEGMENT_ID + 1;
