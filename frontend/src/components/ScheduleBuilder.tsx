"use client";

import { useState } from "react";
import { apiClient, BuildScheduleResponse } from "@/lib/api";

type FormStep = "school" | "major" | "loading" | "calendar";

interface ScheduleBuilderProps {
  onScheduleBuilt: (data: BuildScheduleResponse) => void;
}

export default function ScheduleBuilder({
  onScheduleBuilt,
}: ScheduleBuilderProps) {
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
        return "Build Schedule";
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
      <div className="text-center space-y-4 sm:space-y-6">
        <h1 className="text-3xl sm:text-5xl font-semibold tracking-tight font-camera">
          Build your dream schedule
        </h1>
        <p className="text-base sm:text-xl text-black/60 dark:text-white/60">
          The easiest way to build schedules that fit into your life.
        </p>
      </div>

      <div className="mt-8 sm:mt-10">
        <label htmlFor="input" className="sr-only">
          {getPlaceholder()}
        </label>
        <div className="relative">
          <input
            id="input"
            type="text"
            placeholder={getPlaceholder()}
            value={getInputValue()}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            disabled={isInputDisabled()}
            className="w-full h-12 sm:h-14 rounded-2xl border border-black/[.12] dark:border-white/[.18] bg-white dark:bg-black/40 px-4 pr-28 text-base sm:text-lg outline-none focus:ring-2 focus:ring-black/10 dark:focus:ring-white/20 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            onClick={handleContinue}
            disabled={isButtonDisabled()}
            className="absolute right-2 top-1/2 -translate-y-1/2 h-9 sm:h-10 px-4 rounded-xl bg-foreground text-background text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {getButtonText()}
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}
      </div>
    </section>
  );
}
