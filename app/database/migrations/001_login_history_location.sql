-- Migration 001: login_history.location
-- Adds approximate geolocation (city/region/country) for security audit events.
-- Run in Supabase SQL Editor if your project predates this column.

alter table public.login_history add column if not exists location text;
