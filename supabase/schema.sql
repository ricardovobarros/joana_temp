-- Correr no Supabase: SQL Editor -> New query -> colar tudo -> Run

create table if not exists public.temperature_readings (
    id bigint generated always as identity primary key,
    created_at timestamptz not null default now(),
    temperature_c numeric(4, 1) not null,
    humidity numeric(4, 1)
);

create index if not exists temperature_readings_created_at_idx
    on public.temperature_readings (created_at desc);

create table if not exists public.timer_sessions (
    id bigint generated always as identity primary key,
    started_at timestamptz not null,
    ended_at timestamptz,
    duration_seconds integer,
    end_reason text check (end_reason in ('button', 'app', 'auto12h', 'reboot', 'unknown'))
);

create index if not exists timer_sessions_started_at_idx
    on public.timer_sessions (started_at desc);

-- Só pode existir uma sessão aberta (timer a correr) de cada vez
create unique index if not exists timer_sessions_one_open_idx
    on public.timer_sessions ((true)) where ended_at is null;

-- Mínimo e máximo por dia (UTC), para consultar no painel do Supabase.
-- O site agrupa por dia no fuso horário do browser.
create or replace view public.daily_temperature_stats
with (security_invoker = true) as
select
    (created_at at time zone 'UTC')::date as day_utc,
    min(temperature_c) as temp_min,
    max(temperature_c) as temp_max,
    round(avg(temperature_c), 1) as temp_avg,
    count(*) as readings
from public.temperature_readings
group by 1
order by 1 desc;

-- RLS ativo e sem políticas: a chave pública (anon) não acede a nada.
-- O backend usa a service role key, que ignora o RLS.
alter table public.temperature_readings enable row level security;
alter table public.timer_sessions enable row level security;

create table if not exists public.sleep_sessions (
    id bigint generated always as identity primary key,
    started_at timestamptz not null,
    ended_at timestamptz,
    duration_seconds integer,
    end_reason text check (end_reason in ('button', 'app', 'reboot', 'unknown'))
);

-- Projetos criados antes do controlo de sono pelo site não aceitavam `app`.
alter table public.sleep_sessions
    drop constraint if exists sleep_sessions_end_reason_check;
alter table public.sleep_sessions
    add constraint sleep_sessions_end_reason_check
    check (end_reason in ('button', 'app', 'reboot', 'unknown'));

create index if not exists sleep_sessions_started_at_idx
    on public.sleep_sessions (started_at desc);

create unique index if not exists sleep_sessions_one_open_idx
    on public.sleep_sessions ((true)) where ended_at is null;

alter table public.sleep_sessions enable row level security;

-- Cada toque é um horário próprio. Dormir não precisa de um acordar correspondente.
create table if not exists public.sleep_events (
    id bigint generated always as identity primary key,
    happened_at timestamptz not null,
    kind text not null check (kind in ('sleep', 'wake')),
    source text not null default 'unknown' check (source in ('button', 'app', 'unknown'))
);

create index if not exists sleep_events_happened_at_idx
    on public.sleep_events (happened_at desc);

alter table public.sleep_events enable row level security;

-- Copia o histórico antigo só enquanto a tabela nova ainda está vazia.
insert into public.sleep_events (happened_at, kind, source)
select started_at, 'sleep', 'unknown'
from public.sleep_sessions
where not exists (select 1 from public.sleep_events);

insert into public.sleep_events (happened_at, kind, source)
select ended_at,
       'wake',
       case
           when end_reason in ('button', 'app') then end_reason
           else 'unknown'
       end
from public.sleep_sessions
where ended_at is not null
  and not exists (select 1 from public.sleep_events where kind = 'wake');
