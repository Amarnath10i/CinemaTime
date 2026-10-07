"use client";

/** Shown in place of a movie grid when there's nothing to list, or the API can't be reached. */
export function EmptyState({ serverDown = false, label = "titles" }) {
  return (
    <div className="pt-24 pb-12 text-center px-4 max-w-2xl mx-auto">
      {serverDown ? (
        <>
          <h3 className="text-2xl font-bold text-white mb-4">Can&apos;t reach the CinemaTime server</h3>
          <p className="text-gray-400 text-lg mb-8">
            Movies, shows and trailers will show up as soon as it&apos;s back. Please try again in a moment.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-3 bg-white text-black font-bold rounded hover:bg-gray-200 transition-colors"
          >
            Try Again
          </button>
        </>
      ) : (
        <>
          <h3 className="text-2xl font-bold text-white mb-4">Nothing here yet</h3>
          <p className="text-gray-400 text-lg">
            We don&apos;t have any {label} to show here. Try another category.
          </p>
        </>
      )}
    </div>
  );
}
