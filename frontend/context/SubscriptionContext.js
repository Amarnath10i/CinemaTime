"use client";
import { createContext, useContext, useState, useEffect, useCallback } from "react";

const SubscriptionContext = createContext(null);

// Indian OTT Platforms Configuration
export const INDIAN_OTT_PLATFORMS = [
  { id: 8, name: "Netflix", color: "#E50914", icon: "N" },
  { id: 9, name: "Amazon Prime Video", color: "#00A8E1", icon: "P" },
  { id: 337, name: "Disney+ Hotstar", color: "#1A1A2E", icon: "D+" },
  { id: 356, name: "JioCinema", color: "#0066FF", icon: "J" },
  { id: 358, name: "Sony LIV", color: "#FF6B00", icon: "S" },
  { id: 359, name: "ZEE5", color: "#FF0000", icon: "Z" },
  { id: 68, name: "Apple TV+", color: "#000000", icon: "A" },
  { id: 384, name: "MX Player", color: "#FF3366", icon: "MX" },
  { id: 385, name: "Voot", color: "#6C5CE7", icon: "V" },
  { id: 386, name: "Aha", color: "#FF6B35", icon: "A" },
  { id: 387, name: "Sun NXT", color: "#FFD700", icon: "SN" },
  { id: 388, name: "Hoichoi", color: "#E91E63", icon: "H" },
  { id: 389, name: "Eros Now", color: "#00BFA5", icon: "E" },
  { id: 390, name: "Lionsgate Play", color: "#1A1A2E", icon: "LP" },
  { id: 391, name: "Mubi", color: "#00D4AA", icon: "M" },
  { id: 392, name: "DocuBay", color: "#FF6F61", icon: "DB" },
  { id: 393, name: "ManoramaMAX", color: "#0066CC", icon: "MM" },
];

const STORAGE_KEY = "cinema_time_subscriptions";

export function SubscriptionProvider({ children }) {
  const [subscriptions, setSubscriptions] = useState(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        try {
          return new Set(JSON.parse(stored));
        } catch {
          return new Set();
        }
      }
    }
    return new Set();
  });

  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    setIsLoaded(true);
  }, []);

  useEffect(() => {
    if (isLoaded) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(subscriptions)));
    }
  }, [subscriptions, isLoaded]);

  const toggleSubscription = useCallback((providerId) => {
    setSubscriptions((prev) => {
      const next = new Set(prev);
      if (next.has(providerId)) {
        next.delete(providerId);
      } else {
        next.add(providerId);
      }
      return next;
    });
  }, []);

  const isSubscribed = useCallback((providerId) => {
    return subscriptions.has(providerId);
  }, [subscriptions]);

  const getSubscribedProviders = useCallback(() => {
    return INDIAN_OTT_PLATFORMS.filter((p) => subscriptions.has(p.id));
  }, [subscriptions]);

  const value = {
    subscriptions,
    toggleSubscription,
    isSubscribed,
    getSubscribedProviders,
    platforms: INDIAN_OTT_PLATFORMS,
  };

  return (
    <SubscriptionContext.Provider value={value}>
      {children}
    </SubscriptionContext.Provider>
  );
}

export function useSubscriptions() {
  const context = useContext(SubscriptionContext);
  if (!context) {
    throw new Error("useSubscriptions must be used within a SubscriptionProvider");
  }
  return context;
}