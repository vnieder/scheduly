"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { apiClient, BuildScheduleResponse } from "@/lib/api";
import { useUser } from "@/lib/user-context";

type FormStep = "school" | "major" | "loading" | "calendar";

interface ScheduleBuilderProps {
  onScheduleBuilt: (data: BuildScheduleResponse) => void;
  onAuthRequired: () => void;
}

export default function ScheduleBuilder({
  onScheduleBuilt,
  onAuthRequired,
}: ScheduleBuilderProps) {
  const { user, isLoading } = useUser();
  const [currentStep, setCurrentStep] = useState<FormStep>("school");
  const [school, setSchool] = useState("");
  const [major, setMajor] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleContinue = async () => {
    setError(null);

    if (currentStep === "school") {
      if (!school.trim()) {
        setError("Please enter your school");
        return;
      }
      setCurrentStep("major");
    } else if (currentStep === "major") {
      if (!major.trim()) {
        setError("Please enter your major");
        return;
      }

      // Check if user is authenticated before building schedule
      if (!user && !isLoading) {
        onAuthRequired();
        return;
      }

      // Build schedule
      setCurrentStep("loading");

      try {
        const response = await apiClient.buildSchedule({
          school: school.trim(),
          major: major.trim(),
          term: "2251", // Default term - could be made configurable
          utterance: "", // No preferences for now
        });

        onScheduleBuilt(response);
        setCurrentStep("calendar");
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to build schedule"
        );
        setCurrentStep("major"); // Go back to major step on error
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleContinue();
    }
  };

  const getPlaceholder = () => {
    switch (currentStep) {
      case "school":
        return "What college do you attend?";
      case "major":
        return "What is your major?";
      default:
        return "";
    }
  };

  const getInputValue = () => {
    switch (currentStep) {
      case "school":
        return school;
      case "major":
        return major;
      default:
        return "";
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (currentStep === "school") {
      setSchool(value);
    } else if (currentStep === "major") {
      setMajor(value);
    }
  };

  const getButtonText = () => {
    switch (currentStep) {
      case "school":
        return "Continue";
      case "major":
        return user ? "Build Schedule" : "Sign in to Build";
      case "loading":
        return "Building...";
      default:
        return "Continue";
    }
  };

  const isButtonDisabled = () => {
    return (
      currentStep === "loading" ||
      (currentStep === "school" && !school.trim()) ||
      (currentStep === "major" && !major.trim())
    );
  };

  const isInputDisabled = () => {
    return currentStep === "loading";
  };

  if (currentStep === "loading") {
    return (
      <section className="mx-auto max-w-3xl min-h-[calc(100vh-8rem)] flex flex-col justify-center px-4 sm:px-6 py-16 sm:py-24">
        <div className="text-center space-y-4 sm:space-y-6">
          <div className="w-16 h-16 mx-auto border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin"></div>
          <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight font-camera">
            Building your schedule...
          </h2>
          <p className="text-base sm:text-lg text-black/60 dark:text-white/60">
            Finding the best courses for {major} at {school}
          </p>
        </div>
      </section>
    );
  }

  if (currentStep === "calendar") {
    return null; // Calendar component will be rendered by parent
  }

  return (
    <section className="mx-auto max-w-3xl min-h-[calc(100vh-8rem)] flex flex-col justify-center px-4 sm:px-6 py-16 sm:py-24">
      <motion.div
        className="text-center space-y-4 sm:space-y-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        <motion.h1
          className="text-3xl sm:text-5xl font-semibold tracking-tight font-camera"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
        >
          Build your dream schedule
        </motion.h1>
        <motion.p
          className="text-base sm:text-xl text-black/60 dark:text-white/60"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4, ease: "easeOut" }}
        >
          The easiest way to build schedules that fit into your life.
        </motion.p>
      </motion.div>

      <motion.div
        className="mt-8 sm:mt-10"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.6, ease: "easeOut" }}
      >
        <label htmlFor="input" className="sr-only">
          {getPlaceholder()}
        </label>
        <div className="relative">
          <motion.input
            id="input"
            type="text"
            placeholder={getPlaceholder()}
            value={getInputValue()}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            disabled={isInputDisabled()}
            className="w-full h-12 sm:h-14 rounded-2xl border border-black/[.12] dark:border-white/[.18] bg-white dark:bg-black/40 px-4 pr-28 text-base sm:text-lg outline-none focus:ring-0 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed autofill-fix"
            whileFocus={{ scale: 1.02 }}
            transition={{ duration: 0.2 }}
          />
          <motion.button
            onClick={handleContinue}
            disabled={isButtonDisabled()}
            className="absolute right-2 top-1/2 -translate-y-1/2 h-9 sm:h-10 px-4 rounded-xl bg-foreground text-background text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            transition={{ duration: 0.2 }}
          >
            {getButtonText()}
          </motion.button>
        </div>

        {error && (
          <motion.div
            className="mt-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
          >
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          </motion.div>
        )}

        {/* Authentication prompt for major step */}
        {currentStep === "major" && !user && !isLoading && (
          <motion.div
            className="mt-6 p-4 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="flex items-center space-x-3">
              <div className="flex-shrink-0">
                <svg
                  className="w-5 h-5 text-blue-600 dark:text-blue-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="flex-1">
                <p className="text-sm text-blue-800 dark:text-blue-200">
                  <strong>Sign in required:</strong> To build and save your
                  schedule, please sign in first.
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </motion.div>
    </section>
  );
}
