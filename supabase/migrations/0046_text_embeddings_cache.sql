-- Task 3(배치 잡 공간 스위치)에 필요한 쓰기 쪽 준비물. 0045 가 읽기(컬럼 + match_*_k RPC)를
-- 만들었고, 여기서는 KURE 공간에 **쓰기** 위한 세 가지를 추가한다.
--
-- 1) text_embeddings — 업종 텍스트 임베딩 캐시.
--    compute_company_vectors 는 매일 2.5만 회사의 업종 텍스트를 다시 임베딩한다(2026-10-15 실측
--    24h 5.9만 건). OpenAI API 는 싸고 빨라 괜찮았지만 로컬 CPU 모델(Actions, KURE_BACKEND=torch)은
--    시간당 1만 건이 한계 → 같은 텍스트는 두 번 임베딩하지 않는다. 회사 업종 텍스트는 하루 단위로
--    거의 변하지 않으므로 캐시 적중률이 곧 이 잡의 런타임이다.
--    공고·사전규격·발주계획은 캐시하지 않는다 — 각 행을 평생 한 번만 임베딩한다.
--    1024d 만 저장한다(openai 공간은 캐시 대상 아님). 공간이 더 늘면 그때 차원별 컬럼을 고민.
--
-- 2) embedded_k_at — 공간별 "임베딩 완료 시각" 마커. 기존 embedded_at 을 두 공간이 공유하면
--    한쪽이 채운 시각 때문에 다른 쪽 대상 선택이 막힌다(compute_company_vectors 는 embedded_at
--    으로 티어를 나누고, embed_bid_notices --reembed-all 은 그 시각으로 재처리 여부를 본다).
--
-- 3) update_*_embeddings_k — 0004 batch update RPC 의 `_k` 변형. jsonb 입력 모양(embedding,
--    embedded_at)은 기존과 똑같이 두고 쓰는 컬럼만 embedding_k / embedded_k_at 으로 바꿨다.
--    그래서 잡 코드는 RPC 이름만 갈아끼우면 된다.

begin;

create table if not exists text_embeddings (
  space text not null,
  text_sha1 text not null,
  embedding vector(1024) not null,
  created_at timestamptz not null default now(),
  primary key (space, text_sha1)
);

comment on table text_embeddings is
  '텍스트 임베딩 캐시 (키 = 공간 + 텍스트 sha1). compute_company_vectors 의 업종 텍스트 재임베딩을 막는 용도 — 로컬 CPU 모델은 시간당 1만 건이 한계다. 1024d(kure) 만 저장한다.';

alter table bid_notices  add column if not exists embedded_k_at timestamptz;
alter table companies    add column if not exists embedded_k_at timestamptz;
alter table pre_specs    add column if not exists embedded_k_at timestamptz;
alter table order_plans  add column if not exists embedded_k_at timestamptz;

create or replace function update_bid_notice_embeddings_k(updates jsonb)
returns int
language plpgsql
as $$
declare
  rec record;
  cnt int := 0;
begin
  for rec in
    select * from jsonb_to_recordset(updates)
      as x(bid_ntce_no text, bid_ntce_ord text, embedding text, embedded_at timestamptz)
  loop
    update bid_notices
       set embedding_k = rec.embedding::vector,
           embedded_k_at = rec.embedded_at
     where bid_ntce_no = rec.bid_ntce_no
       and bid_ntce_ord = rec.bid_ntce_ord;
    if found then cnt := cnt + 1; end if;
  end loop;
  return cnt;
end;
$$;


create or replace function update_pre_specs_embeddings_k(updates jsonb)
returns int
language plpgsql
as $$
declare
  rec record;
  cnt int := 0;
begin
  for rec in
    select * from jsonb_to_recordset(updates)
      as x(bf_spec_rgst_no text, embedding text, embedded_at timestamptz)
  loop
    update pre_specs
       set embedding_k = rec.embedding::vector,
           embedded_k_at = rec.embedded_at
     where bf_spec_rgst_no = rec.bf_spec_rgst_no;
    if found then cnt := cnt + 1; end if;
  end loop;
  return cnt;
end;
$$;


create or replace function update_order_plans_embeddings_k(updates jsonb)
returns int
language plpgsql
as $$
declare
  rec record;
  cnt int := 0;
begin
  for rec in
    select * from jsonb_to_recordset(updates)
      as x(order_plan_unty_no text, embedding text, embedded_at timestamptz)
  loop
    update order_plans
       set embedding_k = rec.embedding::vector,
           embedded_k_at = rec.embedded_at
     where order_plan_unty_no = rec.order_plan_unty_no;
    if found then cnt := cnt + 1; end if;
  end loop;
  return cnt;
end;
$$;


create or replace function update_company_embeddings_k(updates jsonb)
returns int
language plpgsql
as $$
declare
  rec record;
  cnt int := 0;
begin
  for rec in
    select * from jsonb_to_recordset(updates)
      as x(bizrno text, embedding text, embedded_at timestamptz)
  loop
    update companies
       set embedding_k = rec.embedding::vector,
           embedded_k_at = rec.embedded_at
     where bizrno = rec.bizrno;
    if found then cnt := cnt + 1; end if;
  end loop;
  return cnt;
end;
$$;

notify pgrst, 'reload schema';

commit;
