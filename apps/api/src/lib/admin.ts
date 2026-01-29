import { supabaseAdmin } from "@/lib/supabase";

export async function isAdmin(userId: string): Promise<boolean> {
  const { data, error } = await supabaseAdmin
    .schema("apl")
    .from("user_profile")
    .select("role")
    .eq("id", userId)
    .single();

  if (error) {
    throw error;
  }
  return data?.role === "ADMIN";
}
