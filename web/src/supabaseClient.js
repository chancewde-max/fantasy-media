import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const anon = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const LEAGUE_ID = import.meta.env.VITE_LEAGUE_ID;

if (!url || !anon) {
  // Surface misconfiguration early instead of silent blank screens.
  console.error("Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY");
}

export const supabase = createClient(url, anon);
