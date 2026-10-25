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
