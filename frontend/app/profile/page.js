"use client";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useAuth } from "../../context/AuthContext";
import { useSubscriptions } from "../../context/SubscriptionContext";

export default function ProfilePage() {
  const { user, logout, updatePreferences } = useAuth();
  const { subscriptions, toggleSubscription, isSubscribed, getSubscribedProviders, platforms, syncing, syncToCloud } = useSubscriptions();
  const [activeTab, setActiveTab] = useState("platforms");
  const [saving, setSaving] = useState(false);

  const handleSavePreferences = async () => {
    setSaving(true);
    await updatePreferences({ subscriptions: Array.from(subscriptions) });
    setSaving(false);
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white mb-4">Please sign in to view your profile</h2>
          <p className="text-gray-400">Your preferences will sync across all devices</p>
        </div>
      </div>
    );
  }

  const subscribedPlatforms = getSubscribedProviders();

  return (
    <main className="min-h-screen bg-dark-900 pb-20">
      <div className="max-w-4xl mx-auto px-6 md:px-12 pt-24">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <h1 className="text-4xl md:text-5xl font-black font-outfit uppercase tracking-tighter text-white mb-2">
            Profile & Settings
          </h1>
          <p className="text-gray-400">Manage your streaming platforms and preferences</p>
        </motion.div>

        {/* Profile Card */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass rounded-2xl p-6 mb-8 border border-white/10">
          <div className="flex items-center gap-6">
            <div className="w-20 h-20 rounded-full bg-accent/20 flex items-center justify-center font-bold text-accent text-3xl flex-shrink-0">
              {user?.name?.[0]?.toUpperCase() || "U"}
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-white">{user?.name}</h2>
              <p className="text-gray-400">{user?.email}</p>
              <p className="text-sm text-gray-500 mt-1">Member since {new Date(user?.created_at || Date.now()).toLocaleDateString()}</p>
            </div>
            <button
              onClick={logout}
              className="px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-gray-300 hover:text-white hover:bg-white/10 transition-colors text-sm font-medium"
            >
              Sign Out
            </button>
          </div>
        </motion.div>

        {/* Tabs */}
        <div className="glass rounded-2xl border border-white/10 overflow-hidden">
          <div className="flex border-b border-white/10">
            {[
              { id: "platforms", label: "My Platforms", count: subscribedPlatforms.length },
              { id: "sync", label: "Cloud Sync", count: null }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 py-4 px-6 text-center font-medium transition-all ${
                  activeTab === tab.id
                    ? "text-white border-b-2 border-accent bg-white/5"
                    : "text-gray-400 hover:text-white hover:bg-white/5"
                }`}
              >
                {tab.label}
                {tab.count !== null && (
                  <span className="ml-2 px-2 py-0.5 text-xs bg-accent/20 text-accent rounded-full">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Platforms Tab */}
          <AnimatePresence mode="wait">
            {activeTab === "platforms" && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="p-6"
              >
                <div className="mb-6">
                  <h3 className="text-lg font-bold text-white mb-2">Streaming Subscriptions</h3>
                  <p className="text-gray-400 text-sm">
                    Toggle the platforms you subscribe to. Only these will appear in "Where to Watch" filters.
                    {syncing && <span className="ml-2 text-xs text-accent animate-pulse">(Syncing...)</span>}
                  </p>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  {platforms.map((platform) => {
                    const subscribed = isSubscribed(platform.id);
                    return (
                      <motion.button
                        key={platform.id}
                        onClick={() => { toggleSubscription(platform.id); handleSavePreferences(); }}
                        whileTap={{ scale: 0.98 }}
                        className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                          subscribed
                            ? "border-accent/50 bg-accent/10"
                            : "border-white/10 hover:border-accent/30 hover:bg-white/5"
                        }`}
                      >
                        <div
                          className="w-12 h-12 rounded-lg flex items-center justify-center font-bold text-white text-sm flex-shrink-0"
                          style={{ backgroundColor: platform.color }}
                        >
                          {platform.icon}
                        </div>
                        <div className="flex-1 min-w-0 text-left">
                          <p className="font-medium text-white truncate">{platform.name}</p>
                          <p className="text-xs text-gray-400">India</p>
                        </div>
                        <div className="relative w-11 h-6 rounded-full transition-colors flex items-center pr-1">
                          <div
                            className={`w-5 h-5 rounded-full bg-white shadow-md transition-transform ${
                              subscribed ? "translate-x-full" : "translate-x-0"
                            }`}
                          />
                        </div>
                      </motion.button>
                    );
                  })}
                </div>

                {subscribedPlatforms.length === 0 && (
                  <div className="text-center py-12 text-gray-500">
                    <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <p className="text-lg">No platforms selected yet</p>
                    <p className="text-sm mt-1">Toggle platforms above to personalize your "Where to Watch" results</p>
                  </div>
                )}
              </motion.div>
            )}

            {/* Sync Tab */}
            {activeTab === "sync" && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="p-6"
              >
                <div className="max-w-2xl">
                  <h3 className="text-lg font-bold text-white mb-2">Cloud Synchronization</h3>
                  <p className="text-gray-400 text-sm mb-6">
                    Your platform preferences are saved locally and can be synced to the cloud.
                    This allows your settings to follow you across all devices.
                  </p>

                  <div className="glass rounded-xl p-6 border border-white/10 mb-6">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <p className="font-medium text-white">Supabase Cloud Sync</p>
                        <p className="text-sm text-gray-400">Sync preferences across devices</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`w-3 h-3 rounded-full ${process.env.NEXT_PUBLIC_SUPABASE_URL ? "bg-green-500" : "bg-gray-500"}`} />
                        <span className={`text-sm ${process.env.NEXT_PUBLIC_SUPABASE_URL ? "text-green-400" : "text-gray-400"}`}>
                          {process.env.NEXT_PUBLIC_SUPABASE_URL ? "Configured" : "Not Configured"}
                        </span>
                      </div>
                    </div>

                    <button
                      onClick={async () => {
                        setSaving(true);
                        await syncToCloud();
                        setSaving(false);
                      }}
                      disabled={saving || !process.env.NEXT_PUBLIC_SUPABASE_URL}
                      className="w-full py-3 px-4 bg-accent text-black font-bold rounded-lg hover:bg-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {saving ? (
                        <>
                          <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          Syncing...
                        </>
                      ) : (
                        "Sync Now"
                      )}
                    </button>

                    {!process.env.NEXT_PUBLIC_SUPABASE_URL && (
                      <div className="mt-4 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-sm text-yellow-400">
                        <p className="font-medium mb-2">To enable cloud sync:</p>
                        <ol className="space-y-1 list-decimal list-inside">
                          <li>Create a free project at <a href="https://supabase.com" target="_blank" className="underline hover:text-yellow-300">supabase.com</a></li>
                          <li>Go to Settings → API and copy your Project URL and anon/public key</li>
                          <li>Add to Vercel Environment Variables:
                            <code className="block bg-black/30 px-2 py-1 rounded mt-1 text-xs">NEXT_PUBLIC_SUPABASE_URL</code>
                            <code className="block bg-black/30 px-2 py-1 rounded mt-1 text-xs">NEXT_PUBLIC_SUPABASE_ANON_KEY</code>
                          </li>
                          <li>Add to Railway/Render Backend Environment Variables:
                            <code className="block bg-black/30 px-2 px-2 py-1 rounded mt-1 text-xs">SUPABASE_URL</code>
                            <code className="block bg-black/30 px-2 py-1 rounded mt-1 text-xs">SUPABASE_SERVICE_KEY</code> (use service_role key)
                          </li>
                          <li>Redeploy both frontend and backend</li>
                        </ol>
                      </div>
                    )}
                  </div>

                  <div className="glass rounded-xl p-6 border border-white/10">
                    <h4 className="font-medium text-white mb-4">Local Storage Status</h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-gray-400">Platform Preferences</p>
                        <p className="font-mono text-accent">{subscriptions.size} platforms</p>
                      </div>
                      <div>
                        <p className="text-gray-400">Auth Token</p>
                        <p className="font-mono text-accent">Active</p>
                      </div>
                      <div>
                        <p className="text-gray-400">Last Sync</p>
                        <p className="font-mono text-accent">Never (local only)</p>
                      </div>
                      <div>
                        <p className="text-gray-400">Storage Size</p>
                        <p className="font-mono text-accent">~1 KB</p>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </main>
  );
}