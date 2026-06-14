-- 0010에서 match_pre_specs에 인자(min_opnin_clse_date)를 추가했지만 시그니처가 달라
-- 옛 2-인자 버전이 별도 overload로 남아 PostgREST가 호출 시 PGRST203 충돌.
-- 옛 버전을 drop해서 3-인자 버전만 남긴다.

drop function if exists match_pre_specs(vector, int);
