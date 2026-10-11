"use client";
import { useCallback, useEffect, useState } from "react";

// Liked movies live in the browser only: no account needed. The For You page
// sends their ids to /api/for-you, which ranks the catalog from them.
const KEY = "cinematime.likes.v1";
const EVENT = "cinematime-likes";

function read() {
  try {
    const raw = window.localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function write(likes) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(likes));
  } catch {
    // private mode or storage full: likes last for this page view only
  }
  window.dispatchEvent(new Event(EVENT));
}

export function useLikes() {
  const [likes, setLikes] = useState([]);

  useEffect(() => {
    const sync = () => setLikes(read());
    sync();
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync); // other tabs
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const isLiked = useCallback((id) => likes.some((m) => m.id === id), [likes]);

  const toggle = useCallback((movie) => {
    const current = read();
    const next = current.some((m) => m.id === movie.id)
      ? current.filter((m) => m.id !== movie.id)
      : [{ id: movie.id, title: movie.title, poster: movie.poster || null, at: Date.now() }, ...current];
    write(next);
  }, []);

  const clear = useCallback(() => write([]), []);

  return { likes, isLiked, toggle, clear };
}
