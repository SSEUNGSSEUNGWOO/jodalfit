-- 임베딩 batch update RPC
-- supabase-py의 .upsert()는 INSERT처럼 동작해서 NOT NULL 컬럼 충돌.
-- 임베딩 갱신은 UPDATE만 해야 함 → RPC로 batch 처리.

create or replace function update_bid_notice_embeddings(updates jsonb)
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
       set embedding = rec.embedding::vector,
           embedded_at = rec.embedded_at
     where bid_ntce_no = rec.bid_ntce_no
       and bid_ntce_ord = rec.bid_ntce_ord;
    if found then cnt := cnt + 1; end if;
  end loop;
  return cnt;
end;
$$;


create or replace function update_pre_specs_embeddings(updates jsonb)
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
       set embedding = rec.embedding::vector,
           embedded_at = rec.embedded_at
     where bf_spec_rgst_no = rec.bf_spec_rgst_no;
    if found then cnt := cnt + 1; end if;
  end loop;
  return cnt;
end;
$$;


create or replace function update_order_plans_embeddings(updates jsonb)
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
       set embedding = rec.embedding::vector,
           embedded_at = rec.embedded_at
     where order_plan_unty_no = rec.order_plan_unty_no;
    if found then cnt := cnt + 1; end if;
  end loop;
  return cnt;
end;
$$;


create or replace function update_company_embeddings(updates jsonb)
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
       set embedding = rec.embedding::vector,
           embedded_at = rec.embedded_at
     where bizrno = rec.bizrno;
    if found then cnt := cnt + 1; end if;
  end loop;
  return cnt;
end;
$$;
