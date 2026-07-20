-- Run in Supabase's SQL Editor before using db.py
-- (Dashboard > SQL Editor > New query > Run)

create table if not exists findings (
    id uuid primary key default gen_random_uuid(),
    topic text not null,
    found boolean not null,
    headline text not null,
    category text not null,
    why_it_matters text not null,
    source_url text not null,
    created_at timestamptz not null default now()
);

-- RLS skipped on purpose -- single-user internal tool. A public-facing
-- version would want row-level security scoping rows per user.
