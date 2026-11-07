import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  // Fail loudly in development so missing env vars are caught early.
  // In production the build will still succeed, but auth calls will fail.
  console.warn(
    "Supabase environment variables are missing. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local"
  );
}

const resolvedUrl = supabaseUrl && supabaseUrl.length > 0
  ? supabaseUrl
  : "https://placeholder.supabase.co";
const resolvedKey = supabaseAnonKey && supabaseAnonKey.length > 0
  ? supabaseAnonKey
  : "placeholder-anon-key";

export const supabase = createClient(
  resolvedUrl,
  resolvedKey,
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  }
);

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);