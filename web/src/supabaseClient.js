import { createClient } from "@supabase/supabase-js";

// These are PUBLIC values (the anon key is meant for the browser; row-level
// security protects the data). Defaults let the app deploy out of the box;
// set the VITE_* env vars in Vercel to point at a different project.
const DEFAULT_URL = "https://aviyosgketrynhkczfoo.supabase.co";
const DEFAULT_ANON =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF2aXlvc2drZXRyeW5oa2N6Zm9vIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY3NDI1MzYsImV4cCI6MjEwMjMxODUzNn0.wroPwYmcUJpBB8TOlXnsPsCItidr9N0KKLnM1hgVMwY";
const DEFAULT_LEAGUE = "d9142041-374e-4b7f-99a7-21853b86645c";

const url = import.meta.env.VITE_SUPABASE_URL || DEFAULT_URL;
const anon = import.meta.env.VITE_SUPABASE_ANON_KEY || DEFAULT_ANON;

export const LEAGUE_ID = import.meta.env.VITE_LEAGUE_ID || DEFAULT_LEAGUE;

export const supabase = createClient(url, anon);
