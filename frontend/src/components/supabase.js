import { createClient } from "@supabase/supabase-js";

// Replace these with your actual Supabase project values
// You can find them at: https://app.supabase.com → Project Settings → API
const SUPABASE_URL  = process.env.REACT_APP_SUPABASE_URL  || "https://your-project.supabase.co";
const SUPABASE_ANON = process.env.REACT_APP_SUPABASE_ANON || "your-anon-key";

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON);