'use client';

import { BuildScheduleResponse } from '@/lib/api';
import { useState } from 'react';

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
  };
}

export default function ScheduleCalendar({ scheduleData, onBack }: ScheduleCalendarProps) {
  const plan: SchedulePlan = scheduleData.plan;
  const sections = plan.sections || [];
  const [selectedCourse, setSelectedCourse] = useState<Section | null>(null);

  // Beautiful 7-color palette for unique class colors
  const colorPalette = [
    {
      primary: '#3B82F6', // Blue
      secondary: '#1E40AF',
      light: '#DBEAFE',
      gradient: 'from-blue-500 to-blue-600'
    },
    {
      primary: '#10B981', // Emerald
      secondary: '#047857',
      light: '#D1FAE5',
      gradient: 'from-emerald-500 to-emerald-600'
    },
    {
      primary: '#F59E0B', // Amber
      secondary: '#D97706',
      light: '#FEF3C7',
      gradient: 'from-amber-500 to-amber-600'
    },
    {
      primary: '#EF4444', // Red
      secondary: '#DC2626',
      light: '#FEE2E2',
      gradient: 'from-red-500 to-red-600'
    },
    {
      primary: '#8B5CF6', // Purple
      secondary: '#7C3AED',
      light: '#EDE9FE',
      gradient: 'from-purple-500 to-purple-600'
    },
    {
      primary: '#06B6D4', // Cyan
      secondary: '#0891B2',
      light: '#CFFAFE',
      gradient: 'from-cyan-500 to-cyan-600'
    },
    {
      primary: '#EC4899', // Pink
      secondary: '#DB2777',
      light: '#FCE7F3',
      gradient: 'from-pink-500 to-pink-600'
    }
  ];

  // Get color for a course based on its index
  const getCourseColor = (index: number) => {
    return colorPalette[index % colorPalette.length];
  };

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
            instructor: section.instructor
          }
        });
      }
    });
  });

  // Calculate time range for calendar
  let earliestMinutes = 24 * 60; // Latest possible time
  let latestMinutes = 0; // Earliest possible time
  
  sections.forEach(section => {
    const [startHour, startMin] = section.start.split(':').map(Number);
    const [endHour, endMin] = section.end?.split(':').map(Number) || [0, 0];
    
    const startMinutes = startHour * 60 + startMin;
    const endMinutes = endHour * 60 + endMin;
    
    earliestMinutes = Math.min(earliestMinutes, startMinutes);
    latestMinutes = Math.max(latestMinutes, endMinutes);
  });

  // Convert back to hours, rounding up for end time
  const minHour = Math.max(7, Math.floor(earliestMinutes / 60) - 1);
  const maxHour = Math.min(22, Math.ceil(latestMinutes / 60) + 1);
  const totalHours = maxHour - minHour;
  const calendarStartMinutes = minHour * 60;

  // Generate hour labels
  const hourLabels: Array<{ hour: number; period: string; minutes: number }> = [];
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
            <div className="w-20 p-4 text-center font-medium text-sm text-black/60 dark:text-white/60 border-r border-black/[.08] dark:border-white/[.12] bg-black/[.08] dark:bg-white/[.12]">
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
            <div className="w-20 bg-black/[.08] dark:bg-white/[.12] border-r border-black/[.08] dark:border-white/[.12] relative" style={{ height: `${totalHours * 60}px` }}>
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
                    {dayEvents.map((event, eventIndex) => {
                      const topPercent = ((event.startMinutes - calendarStartMinutes) / (totalHours * 60)) * 100;
                      const heightPercent = (event.duration / (totalHours * 60)) * 100;
                      const courseIndex = sections.findIndex(s => s.crn === event.extendedProps.crn);
                      const colors = getCourseColor(courseIndex);
                      
                      return (
                        <div
                          key={event.id}
                          className="absolute left-1 right-1 rounded-xl shadow-lg border-2 cursor-pointer transition-all duration-300 hover:shadow-2xl hover:scale-105 group overflow-hidden"
                          style={{
                            top: `${topPercent}%`,
                            height: `${heightPercent}%`,
                            background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.secondary} 100%)`,
                            borderColor: colors.secondary,
                            boxShadow: `0 4px 20px ${colors.primary}40`
                          }}
                          onClick={() => {
                            const section = sections.find(s => s.crn === event.extendedProps.crn);
                            if (section) setSelectedCourse(section);
                          }}
                          title={`${event.extendedProps.course} - ${event.extendedProps.section}\nTime: ${formatTime(event.startTime)} - ${formatTime(event.endTime)}\nInstructor: ${event.extendedProps.instructor || 'TBD'}\nClick for more details`}
                        >
                          <div className="p-2 h-full flex flex-col justify-center relative">
                            {/* Subtle overlay for better text readability */}
                            <div className="absolute inset-0 bg-black/10 group-hover:bg-black/20 transition-colors duration-300"></div>
                            
                            <div className="relative z-10">
                              <div className="text-white text-xs font-semibold leading-tight drop-shadow-sm">
                                {event.title}
                              </div>
                              <div className="text-white/90 text-xs mt-1 drop-shadow-sm">
                                {formatTime(event.startTime)} - {formatTime(event.endTime)}
                              </div>
                              {event.extendedProps.instructor && (
                                <div className="text-white/80 text-xs mt-0.5 drop-shadow-sm truncate">
                                  {event.extendedProps.instructor}
                                </div>
                              )}
                            </div>
                            
                            {/* Hover effect indicator */}
                            <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                              <div className="w-2 h-2 bg-white/60 rounded-full"></div>
                            </div>
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
          <h3 className="text-lg font-semibold mb-6">Course Details</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {sections.map((section, index) => {
              const colors = getCourseColor(index);
              return (
                <div 
                  key={index} 
                  className="group relative p-6 rounded-2xl bg-white dark:bg-black/40 border border-black/[.08] dark:border-white/[.12] cursor-pointer transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 overflow-hidden"
                  onClick={() => setSelectedCourse(section)}
                  style={{
                    boxShadow: `0 4px 20px ${colors.primary}20`
                  }}
                >
                  {/* Gradient overlay on hover */}
                  <div 
                    className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-300"
                    style={{
                      background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.secondary} 100%)`
                    }}
                  ></div>
                  
                  {/* Color accent bar */}
                  <div 
                    className="absolute top-0 left-0 right-0 h-1 rounded-t-2xl"
                    style={{ backgroundColor: colors.primary }}
                  ></div>
                  
                  <div className="relative z-10">
                    {/* Course header */}
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <div className="font-semibold text-base text-gray-900 dark:text-white group-hover:text-gray-800 dark:group-hover:text-gray-100 transition-colors">
                          {section.course}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                          Section {section.section}
                        </div>
                      </div>
                      <div 
                        className="w-3 h-3 rounded-full flex-shrink-0 mt-1"
                        style={{ backgroundColor: colors.primary }}
                      ></div>
                    </div>
                    
                    {/* Course details */}
                    <div className="space-y-3 text-sm">
                      <div className="flex items-center gap-3">
                        <div className="w-5 h-5 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
                          <svg className="w-3 h-3 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                        </div>
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Days:</span>
                          <span className="ml-2 font-medium text-gray-900 dark:text-white">
                            {Array.isArray(section.days) ? section.days.join(', ') : section.days}
                          </span>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3">
                        <div className="w-5 h-5 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
                          <svg className="w-3 h-3 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </div>
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Time:</span>
                          <span className="ml-2 font-medium text-gray-900 dark:text-white">
                            {section.start} - {section.end}
                          </span>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3">
                        <div className="w-5 h-5 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
                          <svg className="w-3 h-3 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                          </svg>
                        </div>
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Instructor:</span>
                          <span className="ml-2 font-medium text-gray-900 dark:text-white">
                            {section.instructor || 'TBD'}
                          </span>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3">
                        <div className="w-5 h-5 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
                          <svg className="w-3 h-3 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                        </div>
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Credits:</span>
                          <span className="ml-2 font-medium text-gray-900 dark:text-white">
                            {section.credits}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    {/* Click indicator */}
                    <div className="mt-4 flex items-center text-xs text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors">
                      <span>Click for more details</span>
                      <svg className="w-3 h-3 ml-1 group-hover:translate-x-1 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Course Detail Modal */}
      {selectedCourse && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div 
              className="relative p-6 text-white"
              style={{
                background: `linear-gradient(135deg, ${getCourseColor(sections.findIndex(s => s.crn === selectedCourse.crn)).primary} 0%, ${getCourseColor(sections.findIndex(s => s.crn === selectedCourse.crn)).secondary} 100%)`
              }}
            >
              <button
                onClick={() => setSelectedCourse(null)}
                className="absolute top-4 right-4 w-8 h-8 rounded-full bg-white/20 hover:bg-white/30 transition-colors flex items-center justify-center"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
              
              <div className="pr-12">
                <h2 className="text-2xl font-bold mb-2">{selectedCourse.course}</h2>
                <p className="text-white/90 text-lg">Section {selectedCourse.section}</p>
                <p className="text-white/80 text-sm mt-1">CRN: {selectedCourse.crn}</p>
              </div>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-6">
              {/* Course Information Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-10 h-10 rounded-xl flex items-center justify-center"
                      style={{ backgroundColor: `${getCourseColor(sections.findIndex(s => s.crn === selectedCourse.crn)).primary}20` }}
                    >
                      <svg className="w-5 h-5" style={{ color: getCourseColor(sections.findIndex(s => s.crn === selectedCourse.crn)).primary }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Days</p>
                      <p className="font-semibold text-gray-900 dark:text-white">
                        {Array.isArray(selectedCourse.days) ? selectedCourse.days.join(', ') : selectedCourse.days}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div 
                      className="w-10 h-10 rounded-xl flex items-center justify-center"
                      style={{ backgroundColor: `${getCourseColor(sections.findIndex(s => s.crn === selectedCourse.crn)).primary}20` }}
                    >
                      <svg className="w-5 h-5" style={{ color: getCourseColor(sections.findIndex(s => s.crn === selectedCourse.crn)).primary }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Time</p>
                      <p className="font-semibold text-gray-900 dark:text-white">
                        {selectedCourse.start} - {selectedCourse.end}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-10 h-10 rounded-xl flex items-center justify-center"
                      style={{ backgroundColor: `${getCourseColor(sections.findIndex(s => s.crn === selectedCourse.crn)).primary}20` }}
                    >
                      <svg className="w-5 h-5" style={{ color: getCourseColor(sections.findIndex(s => s.crn === selectedCourse.crn)).primary }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Instructor</p>
                      <p className="font-semibold text-gray-900 dark:text-white">
                        {selectedCourse.instructor || 'TBD'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div 
                      className="w-10 h-10 rounded-xl flex items-center justify-center"
                      style={{ backgroundColor: `${getCourseColor(sections.findIndex(s => s.crn === selectedCourse.crn)).primary}20` }}
                    >
                      <svg className="w-5 h-5" style={{ color: getCourseColor(sections.findIndex(s => s.crn === selectedCourse.crn)).primary }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Credits</p>
                      <p className="font-semibold text-gray-900 dark:text-white">
                        {selectedCourse.credits}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Additional Information */}
              <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Course Information</h3>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4">
                  <p className="text-sm text-gray-600 dark:text-gray-300">
                    This course is part of your current schedule. You can view it in the calendar above or in the course list below.
                  </p>
                </div>
              </div>

              {/* Modal Actions */}
              <div className="flex justify-end gap-3 pt-4">
                <button
                  onClick={() => setSelectedCourse(null)}
                  className="px-6 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
                >
                  Close
                </button>
                <button
                  onClick={() => {
                    // Here you could add functionality to add to favorites, export, etc.
                    setSelectedCourse(null);
                  }}
                  className="px-6 py-2 rounded-xl text-white font-medium transition-all duration-300 hover:shadow-lg"
                  style={{
                    background: `linear-gradient(135deg, ${getCourseColor(sections.findIndex(s => s.crn === selectedCourse.crn)).primary} 0%, ${getCourseColor(sections.findIndex(s => s.crn === selectedCourse.crn)).secondary} 100%)`
                  }}
                >
                  Add to Favorites
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}