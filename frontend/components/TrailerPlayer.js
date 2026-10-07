"use client";
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";

let apiPromise = null;

// Load the YouTube IFrame API once per page. It lets us detect videos that
// can't be embedded (deleted, private, embedding disabled) and move on.
function loadYouTubeApi() {
  if (typeof window === "undefined") return Promise.reject(new Error("no window"));
  if (window.YT && window.YT.Player) return Promise.resolve(window.YT);
  if (!apiPromise) {
    apiPromise = new Promise((resolve, reject) => {
      const previous = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        if (typeof previous === "function") previous();
        resolve(window.YT);
      };
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      tag.async = true;
      tag.onerror = () => {
        apiPromise = null;
        reject(new Error("YouTube API failed to load"));
      };
      document.head.appendChild(tag);
    });
  }
  return apiPromise;
}

export function youtubeThumb(key) {
  return `https://i.ytimg.com/vi/${key}/mqdefault.jpg`;
}

export function youtubeWatchUrl(key) {
  return `https://www.youtube.com/watch?v=${key}`;
}

export function youtubeSearchUrl(title, year) {
  return `https://www.youtube.com/results?search_query=${encodeURIComponent(`${title} ${year || ""} official trailer`.trim())}`;
}

/**
 * Plays videos[startIndex], skipping to the next video whenever YouTube
 * reports one as unplayable. Calls onUnavailable once none are left.
 *
 * background: muted-friendly, chromeless, looping, and non-interactive (for
 * the home hero). The ref exposes mute() / unMute().
 */
export const TrailerPlayer = forwardRef(function TrailerPlayer(
  { videos, startIndex = 0, background = false, muted = false, onIndexChange, onUnavailable, className = "" },
  ref
) {
  const hostRef = useRef(null);
  const playerRef = useRef(null);
  const [index, setIndex] = useState(startIndex);
  const [apiFailed, setApiFailed] = useState(false);
  const callbacks = useRef({});
  callbacks.current = { onIndexChange, onUnavailable, count: videos?.length || 0, muted, index };

  const listKey = (videos || []).map((v) => v.key).join(",");
  useEffect(() => setIndex(startIndex), [startIndex, listKey]);

  const current = videos?.[index];

  useImperativeHandle(ref, () => ({
    mute: () => playerRef.current?.mute?.(),
    unMute: () => playerRef.current?.unMute?.(),
  }), []);

  useEffect(() => {
    if (!current || apiFailed) return;
    let cancelled = false;

    loadYouTubeApi()
      .then((YT) => {
        if (cancelled || !hostRef.current) return;
        // The API replaces this node with its iframe; React never manages it.
        const mount = document.createElement("div");
        hostRef.current.replaceChildren(mount);
        playerRef.current = new YT.Player(mount, {
          videoId: current.key,
          width: "100%",
          height: "100%",
          playerVars: {
            autoplay: 1,
            mute: callbacks.current.muted ? 1 : 0,
            controls: background ? 0 : 1,
            rel: 0,
            playsinline: 1,
            iv_load_policy: 3,
            ...(background ? { loop: 1, playlist: current.key, disablekb: 1, fs: 0 } : {}),
          },
          events: {
            onReady: (e) => {
              if (callbacks.current.muted) e.target.mute();
              e.target.playVideo();
            },
            onError: () => {
              const { count, index: i, onIndexChange: changed, onUnavailable: unavailable } = callbacks.current;
              if (i + 1 < count) {
                setIndex(i + 1);
                changed?.(i + 1);
              } else {
                unavailable?.();
              }
            },
          },
        });
      })
      .catch(() => {
        if (!cancelled) setApiFailed(true);
      });

    return () => {
      cancelled = true;
      try {
        playerRef.current?.destroy();
      } catch {}
      playerRef.current = null;
    };
  }, [current?.key, background, apiFailed]);

  if (!current) return null;

  if (apiFailed) {
    // Without the API we can't detect broken videos, but a plain embed still plays.
    const params = new URLSearchParams({
      autoplay: "1",
      mute: muted ? "1" : "0",
      controls: background ? "0" : "1",
      rel: "0",
      playsinline: "1",
      ...(background ? { loop: "1", playlist: current.key } : {}),
    });
    return (
      <div className={className}>
        <iframe
          src={`https://www.youtube.com/embed/${current.key}?${params}`}
          title={current.name}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          referrerPolicy="strict-origin-when-cross-origin"
          allowFullScreen
          className="w-full h-full"
        />
      </div>
    );
  }

  return <div ref={hostRef} className={className} />;
});
