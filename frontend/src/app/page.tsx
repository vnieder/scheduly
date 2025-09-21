export default function Home() {
  return (
    <section className="mx-auto max-w-3xl px-4 sm:px-6 py-16 sm:py-24">
      <div className="text-center space-y-4 sm:space-y-6">
        <h1 className="text-3xl sm:text-5xl font-semibold tracking-tight">
          Build your dream schedule
        </h1>
        <p className="text-sm sm:text-base text-black/60 dark:text-white/60">
          Tell us your school to get started.
        </p>
      </div>

      <div className="mt-8 sm:mt-10">
        <label htmlFor="school" className="sr-only">
          What college do you attend?
        </label>
        <div className="relative">
          <input
            id="school"
            type="text"
            placeholder="What college do you attend?"
            className="w-full h-12 sm:h-14 rounded-2xl border border-black/[.12] dark:border-white/[.18] bg-white dark:bg-black/40 px-4 pr-28 text-base sm:text-lg outline-none focus:ring-2 focus:ring-black/10 dark:focus:ring-white/20 shadow-sm"
          />
          <button className="absolute right-2 top-1/2 -translate-y-1/2 h-9 sm:h-10 px-4 rounded-xl bg-foreground text-background text-sm font-medium hover:opacity-90 transition-opacity">
            Continue
          </button>
        </div>
      </div>
    </section>
  );
}
