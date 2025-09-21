'use client';

import { BuildScheduleResponse } from '@/lib/api';

interface ScheduleCalendarProps {
  scheduleData: BuildScheduleResponse;
  onBack: () => void;
}

interface Section {
  course: string;
  crn: string;
  section: string;
  days: string[] | string;
  start: string;
  end: string;
  location?: string;
  instructor?: string;
  credits: number;
}

interface SchedulePlan {
  term: string;
  totalCredits: number;
  sections: Section[];
  explanations: string[];
  alternatives: any[];
}

interface CalendarEvent {
  id: string;
  title: string;
  startTime: string;
  endTime: string;
  day: string;
  startMinutes: number;
  endMinutes: number;
  duration: number;
  extendedProps: {
    course: string;
    section: string;
    crn: string;
    instructor?: string;
    location?: string;
  };
}

export default function ScheduleCalendar({ scheduleData, onBack }: ScheduleCalendarProps) {
  const plan: SchedulePlan = scheduleData.plan;
  const sections = plan.sections || [];

  // Handle case where no sections are available
  if (!sections || sections.length === 0) {
    return (
      <div className="min-h-screen bg-background">
        {/* Header */}
        <div className="border-b border-black/[.08] dark:border-white/[.12] bg-background/70 backdrop-blur">
          <div className="mx-auto max-w-6xl px-4 sm:px-6 h-16 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={onBack}
                className="flex items-center gap-2 text-sm text-black/60 dark:text-white/60 hover:text-black dark:hover:text-white transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Back
              </button>
              <h1 className="text-xl font-semibold">Your Schedule</h1>
            </div>
          </div>
        </div>

        {/* No Schedule Content */}
        <div className="mx-auto max-w-3xl px-4 sm:px-6 py-16 sm:py-24">
          <div className="text-center space-y-4 sm:space-y-6">
            <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight font-camera">
              No Schedule Found
            </h2>
            <p className="text-base sm:text-lg text-black/60 dark:text-white/60">
              We couldn't find any available courses for your selection. Please try again with different parameters.
            </p>
            <div className="mt-8">
              <button
                onClick={onBack}
                className="px-6 py-3 rounded-xl bg-foreground text-background font-medium hover:opacity-90 transition-opacity"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Day mapping
  const dayMapping: { [key: string]: { index: number; short: string } } = {
    'Mon': { index: 0, short: 'Mon' },
    'Monday': { index: 0, short: 'Mon' },
    'Tue': { index: 1, short: 'Tue' },
    'Tuesday': { index: 1, short: 'Tue' },
    'Wed': { index: 2, short: 'Wed' },
    'Wednesday': { index: 2, short: 'Wed' },
    'Thu': { index: 3, short: 'Thu' },
    'Thursday': { index: 3, short: 'Thu' },
    'Fri': { index: 4, short: 'Fri' },
    'Friday': { index: 4, short: 'Fri' }
  };

  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];

  // Convert sections to calendar events
  const events: CalendarEvent[] = [];

  sections.forEach((section) => {
    const dayList = typeof section.days === 'string' 
      ? section.days.split(',').map(d => d.trim()) 
      : section.days;
    
    dayList.forEach(dayName => {
      const dayInfo = dayMapping[dayName];
      if (dayInfo) {
        // Parse time and convert to minutes from start of day
        const [startHour, startMin] = section.start.split(':').map(Number);
        const [endHour, endMin] = section.end?.split(':').map(Number) || [0, 0];
        
        const startMinutes = startHour * 60 + startMin;
        const endMinutes = endHour * 60 + endMin;
        const duration = endMinutes - startMinutes;

        events.push({
          id: `${section.crn}-${dayName}`,
          title: `${section.course} (${section.section})`,
          startTime: section.start,
          endTime: section.end,
          day: dayName,
          startMinutes,
          endMinutes,
          duration,
          extendedProps: {
            course: section.course,
            section: section.section,
            crn: section.crn,
            instructor: section.instructor,
            location: section.location
          }
        });
      }
    });
  });

  // Calculate time range for calendar
  let earliestHour = 24;
  let latestHour = 0;
  
  sections.forEach(section => {
    const [startHour] = section.start.split(':').map(Number);
    const [endHour] = section.end?.split(':').map(Number) || [0];
    earliestHour = Math.min(earliestHour, startHour);
    latestHour = Math.max(latestHour, endHour);
  });

  const minHour = Math.max(7, earliestHour - 1);
  const maxHour = Math.min(22, latestHour + 1);
  const totalHours = maxHour - minHour;
  const calendarStartMinutes = minHour * 60;

  // Generate hour labels
  const hourLabels = [];
  for (let hour = minHour; hour < maxHour; hour++) {
    const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    const period = hour < 12 ? 'AM' : 'PM';
    hourLabels.push({
      hour: displayHour,
      period,
      minutes: (hour - minHour) * 60
    });
  }

  // Helper function to get events for a specific day
  const getEventsForDay = (dayIndex: number) => {
    return events.filter(event => dayMapping[event.day]?.index === dayIndex);
  };

  // Helper function to format time for display
  const formatTime = (time: string) => {
    const [hour, min] = time.split(':').map(Number);
    const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    const period = hour < 12 ? 'AM' : 'PM';
    return `${displayHour}:${min.toString().padStart(2, '0')} ${period}`;
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b border-black/[.08] dark:border-white/[.12] bg-background/70 backdrop-blur">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-sm text-black/60 dark:text-white/60 hover:text-black dark:hover:text-white transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back
            </button>
            <h1 className="text-xl font-semibold">Your Schedule</h1>
          </div>
          <div className="text-sm text-black/60 dark:text-white/60">
            Session: {scheduleData.session_id.slice(0, 8)}...
          </div>
        </div>
      </div>

      {/* Schedule Content */}
      <div className="mx-auto max-w-6xl px-4 sm:px-6 py-8">
        {/* Schedule Summary */}
        <div className="mb-8 p-6 rounded-2xl bg-white dark:bg-black/40 border border-black/[.08] dark:border-white/[.12]">
          <h2 className="text-lg font-semibold mb-4">Schedule Summary</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-black/60 dark:text-white/60">Total Courses:</span>
              <span className="ml-2 font-medium">{sections.length}</span>
            </div>
            <div>
              <span className="text-black/60 dark:text-white/60">Total Credits:</span>
              <span className="ml-2 font-medium">{plan.totalCredits}</span>
            </div>
            <div>
              <span className="text-black/60 dark:text-white/60">Session ID:</span>
              <span className="ml-2 font-mono text-xs">{scheduleData.session_id}</span>
            </div>
          </div>
        </div>

        {/* Custom Calendar */}
        <div className="bg-white dark:bg-black/40 rounded-2xl border border-black/[.08] dark:border-white/[.12] overflow-hidden">
          {/* Calendar Header */}
          <div className="flex border-b border-black/[.08] dark:border-white/[.12]">
            <div className="w-20 p-4 text-center font-medium text-sm text-black/60 dark:text-white/60 border-r border-black/[.08] dark:border-white/[.12]">
            </div>
            {days.map((day) => (
              <div key={day} className="flex-1 p-4 text-center font-semibold text-sm border-r border-black/[.08] dark:border-white/[.12] last:border-r-0">
                {day}
              </div>
            ))}
          </div>

          {/* Calendar Body */}
          <div className="relative flex">
            {/* Time Column */}
            <div className="w-20 bg-white dark:bg-black/40 border-r border-black/[.08] dark:border-white/[.12] relative" style={{ height: `${totalHours * 60}px` }}>
              {/* Hour Lines for time column */}
              {hourLabels.map((hourLabel, index) => (
                <div
                  key={index}
                  className="absolute left-0 right-0 border-t border-black/[.08] dark:border-white/[.12]"
                  style={{
                    top: `${(hourLabel.minutes / (totalHours * 60)) * 100}%`
                  }}
                />
              ))}
              
              {/* Time Labels */}
              {hourLabels.map((hourLabel, index) => (
                <div
                  key={index}
                  className="absolute text-xs text-black/60 dark:text-white/60 font-medium"
                  style={{
                    top: `${(hourLabel.minutes / (totalHours * 60)) * 100}%`,
                    left: '50%',
                    transform: 'translateX(-50%) translateY(-50%)'
                  }}
                >
                  {hourLabel.hour} {hourLabel.period}
                </div>
              ))}
            </div>

            {/* Day Columns */}
            <div className="flex-1 flex relative" style={{ height: `${totalHours * 60}px` }}>
              {days.map((day, dayIndex) => {
                const dayEvents = getEventsForDay(dayIndex);
                
                return (
                  <div
                    key={day}
                    className="flex-1 relative border-r border-black/[.08] dark:border-white/[.12] last:border-r-0"
                  >
                    {/* Hour Lines for day columns */}
                    {hourLabels.map((hourLabel, index) => (
                      <div
                        key={index}
                        className="absolute left-0 right-0 border-t border-black/[.08] dark:border-white/[.12]"
                        style={{
                          top: `${(hourLabel.minutes / (totalHours * 60)) * 100}%`
                        }}
                      />
                    ))}
                    
                    {/* Events for this day */}
                    {dayEvents.map((event) => {
                      const topPercent = ((event.startMinutes - calendarStartMinutes) / (totalHours * 60)) * 100;
                      const heightPercent = (event.duration / (totalHours * 60)) * 100;
                      
                      return (
                        <div
                          key={event.id}
                          className="absolute left-1 right-1 rounded-lg shadow-sm border cursor-pointer transition-all hover:shadow-md group"
                          style={{
                            top: `${topPercent}%`,
                            height: `${heightPercent}%`,
                            backgroundColor: '#3b82f6',
                            borderColor: '#1d4ed8'
                          }}
                          title={`${event.extendedProps.course} - ${event.extendedProps.section}\nTime: ${formatTime(event.startTime)} - ${formatTime(event.endTime)}\nLocation: ${event.extendedProps.location || 'TBD'}\nInstructor: ${event.extendedProps.instructor || 'TBD'}`}
                        >
                          <div className="p-2 h-full flex flex-col justify-center">
                            <div className="text-white text-xs font-medium leading-tight">
                              {event.title}
                            </div>
                            <div className="text-white/80 text-xs mt-1">
                              {formatTime(event.startTime)} - {formatTime(event.endTime)}
                            </div>
                            {event.extendedProps.location && (
                              <div className="text-white/70 text-xs mt-1 truncate">
                                {event.extendedProps.location}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Course List */}
        <div className="mt-8">
          <h3 className="text-lg font-semibold mb-4">Course Details</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sections.map((section, index) => (
              <div key={index} className="p-4 rounded-xl bg-white dark:bg-black/40 border border-black/[.08] dark:border-white/[.12]">
                <div className="font-medium text-sm">{section.course}</div>
                <div className="text-xs text-black/60 dark:text-white/60 mb-2">Section {section.section}</div>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-black/60 dark:text-white/60">Days:</span>
                    <span>{Array.isArray(section.days) ? section.days.join(', ') : section.days}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-black/60 dark:text-white/60">Time:</span>
                    <span>{section.start} - {section.end}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-black/60 dark:text-white/60">Location:</span>
                    <span>{section.location || 'TBD'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-black/60 dark:text-white/60">Instructor:</span>
                    <span>{section.instructor || 'TBD'}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}