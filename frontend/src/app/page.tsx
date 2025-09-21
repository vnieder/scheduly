'use client';

import { useState } from 'react';
import ScheduleBuilder from '@/components/ScheduleBuilder';
import ScheduleCalendar from '@/components/ScheduleCalendar';
import { BuildScheduleResponse } from '@/lib/api';

export default function Home() {
  const [scheduleData, setScheduleData] = useState<BuildScheduleResponse | null>(null);
  const [showCalendar, setShowCalendar] = useState(false);

  const handleScheduleBuilt = (data: BuildScheduleResponse) => {
    setScheduleData(data);
    setShowCalendar(true);
  };

  const handleBackToBuilder = () => {
    setShowCalendar(false);
    setScheduleData(null);
  };

  if (showCalendar && scheduleData) {
    return <ScheduleCalendar scheduleData={scheduleData} onBack={handleBackToBuilder} />;
  }

  return <ScheduleBuilder onScheduleBuilt={handleScheduleBuilt} />;
}
