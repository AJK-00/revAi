/**
 * supabaseDb.js
 * All database operations for revAi using Supabase.
 *
 * Tables required (see supabase_schema.sql):
 *   profiles   (id, email, display_name, avatar_url, created_at)
 *   sessions   (id, user_id, title, repo_url, created_at, updated_at)
 *   messages   (id, session_id, sender, text, created_at)
 */

import { supabase } from "./supabase";

// ─────────────────────────────────────────────
// AUTH
// ─────────────────────────────────────────────

export async function signUp(email, password, displayName) {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: { data: { display_name: displayName } },
  });
  if (error) throw error;
  return data;
}

export async function signIn(email, password) {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) throw error;
  return data;
}

export async function signOut() {
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
}

export async function getUser() {
  const { data: { user } } = await supabase.auth.getUser();
  return user;
}

export function onAuthChange(callback) {
  const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
    callback(session?.user || null);
  });
  return () => subscription.unsubscribe();
}

// ─────────────────────────────────────────────
// PROFILE
// ─────────────────────────────────────────────

export async function getProfile(userId) {
  const { data, error } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", userId)
    .single();
  if (error && error.code !== "PGRST116") throw error;
  return data;
}

export async function upsertProfile(userId, updates) {
  const { data, error } = await supabase
    .from("profiles")
    .upsert({ id: userId, ...updates, updated_at: new Date().toISOString() })
    .select()
    .single();
  if (error) throw error;
  return data;
}

// ─────────────────────────────────────────────
// SESSIONS
// ─────────────────────────────────────────────

export async function getAllSessions(userId) {
  const { data, error } = await supabase
    .from("sessions")
    .select("*")
    .eq("user_id", userId)
    .order("updated_at", { ascending: false });
  if (error) throw error;
  return data || [];
}

export async function getSession(sessionId) {
  const { data, error } = await supabase
    .from("sessions")
    .select("*")
    .eq("id", sessionId)
    .single();
  if (error) throw error;
  return data;
}

export async function createSession(userId, repoUrl = "") {
  const now = new Date().toISOString();
  const { data, error } = await supabase
    .from("sessions")
    .insert({
      user_id:    userId,
      title:      repoUrl ? _shortenUrl(repoUrl) : "New chat",
      repo_url:   repoUrl,
      created_at: now,
      updated_at: now,
    })
    .select()
    .single();
  if (error) throw error;
  return data;
}

export async function updateSession(sessionId, patch) {
  const { data, error } = await supabase
    .from("sessions")
    .update({ ...patch, updated_at: new Date().toISOString() })
    .eq("id", sessionId)
    .select()
    .single();
  if (error) throw error;
  return data;
}

export async function deleteSession(sessionId) {
  // messages cascade-delete via FK (see schema)
  const { error } = await supabase
    .from("sessions")
    .delete()
    .eq("id", sessionId);
  if (error) throw error;
}

// ─────────────────────────────────────────────
// MESSAGES
// ─────────────────────────────────────────────

export async function getMessages(sessionId) {
  const { data, error } = await supabase
    .from("messages")
    .select("*")
    .eq("session_id", sessionId)
    .order("created_at", { ascending: true });
  if (error) throw error;
  return (data || []).map(m => ({ sender: m.sender, text: m.text }));
}

export async function appendMessage(sessionId, sender, text) {
  const { error } = await supabase
    .from("messages")
    .insert({
      session_id: sessionId,
      sender,
      text,
      created_at: new Date().toISOString(),
    });
  if (error) throw error;

  // Auto-title session from first user message
  if (sender === "user") {
    const msgs = await getMessages(sessionId);
    if (msgs.length === 1) {
      await updateSession(sessionId, {
        title: text.slice(0, 45) + (text.length > 45 ? "…" : ""),
      });
    }
  }
}

// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────

function _shortenUrl(url) {
  try {
    const parts = url.replace("https://github.com/", "").split("/");
    return parts.slice(0, 2).join("/");
  } catch {
    return url.slice(0, 40);
  }
}