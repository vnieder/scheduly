"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import ScheduleBuilder from "@/components/ScheduleBuilder";
import ScheduleCalendar from "@/components/ScheduleCalendar";
// import HistorySidebar from "@/components/HistorySidebar";
import { BuildScheduleResponse } from "@/lib/api";

export default function Home() {
  // Temporarily disable user context
  const user = null;
  const isLoading = false;
  const router = useRouter();
  const [scheduleData, setScheduleData] =
    useState<BuildScheduleResponse | null>(null);
  const [showCalendar, setShowCalendar] = useState(false);
  const [, setShowHistorySidebar] = useState(false);
  // Authentication removed - no auth checks needed

  const handleScheduleBuilt = (data: BuildScheduleResponse) => {
    setScheduleData(data);
    setShowCalendar(true);
  };

  // Auth requirement removed

  const handleBackToBuilder = () => {
    setShowCalendar(false);
    setScheduleData(null);
  };

  // const handleSaveCurrentSchedule = async () => {
  //   if (!scheduleData || !user) return;

  //   try {
  //     // This would be implemented to save the current schedule
  //     console.log("Saving current schedule...", scheduleData);
  //     // You would call the API here to save the schedule
  //   } catch (error) {
  //     console.error("Failed to save schedule:", error);
  //   }
  // };

  // const handleLoadSchedule = async (scheduleId: string) => {
  //   if (!user) return;

  //   try {
  //     // This would be implemented to load a saved schedule
  //     console.log("Loading schedule:", scheduleId);
  //     // You would call the API here to load the schedule
  //   } catch (error) {
  //     console.error("Failed to load schedule:", error);
  //   }
  // };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-16 h-16 border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin"></div>
      </div>
    );
  }

  // Temporarily allow unauthenticated users to see the form
  // if (!user) {
  //   return null; // Will redirect to signin
  // }

  if (showCalendar && scheduleData) {
    return (
      <>
        <ScheduleCalendar
          scheduleData={scheduleData}
          onBack={handleBackToBuilder}
          onShowHistory={() => setShowHistorySidebar(true)}
        />
        {/* <HistorySidebar
          isOpen={showHistorySidebar}
          onClose={() => setShowHistorySidebar(false)}
          onLoadSchedule={handleLoadSchedule}
          onSaveCurrentSchedule={handleSaveCurrentSchedule}
        /> */}
      </>
    );
  }

  return (
    <ScheduleBuilder
      onScheduleBuilt={handleScheduleBuilt}
      onAuthRequired={() => {}} // No-op since auth is removed
    />
  );
}
