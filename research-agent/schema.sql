-- Run this in the Supabase project's SQL Editor before using db.py.
-- (Dashboard, then SQL Editor, then New query, paste this in, and Run)

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

-- RLS is skipped here on purpose. This is a single-user internal tool,
-- not something end users hit directly. A version of this exposed to
-- multiple people, or through a public API, would want row-level
-- security enabled, scoping rows to whoever created them.
