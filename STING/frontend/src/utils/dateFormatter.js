/**
 * Timezone-aware date formatting utilities for STING platform.
 *
 * All timestamps from the backend are in UTC and should be converted
 * to the user's local timezone for display.
 */

/**
 * Get user's current timezone
 * @returns {string} IANA timezone identifier (e.g., 'America/New_York')
 */
export const getUserTimezone = () => {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
};

/**
 * Get timezone offset in hours
 * @returns {string} Timezone offset (e.g., 'UTC-5', 'UTC+2')
 */
export const getTimezoneOffset = () => {
  const offset = -new Date().getTimezoneOffset() / 60;
  const sign = offset >= 0 ? '+' : '';
  return `UTC${sign}${offset}`;
};

/**
 * Format UTC timestamp to user's local time
 * @param {string|Date} utcTimestamp - UTC timestamp (ISO string or Date object)
 * @param {string} style - Format style: 'full', 'long', 'medium', 'short', 'time', 'date', 'relative'
 * @param {string} timezone - Optional timezone override (defaults to user's timezone)
 * @returns {string} Formatted date string in user's local timezone
 *
 * @example
 * formatLocalTime('2025-11-25T04:30:00Z') // "Nov 25, 2025, 4:30 AM"
 * formatLocalTime('2025-11-25T04:30:00Z', 'short') // "11/25/25, 4:30 AM"
 * formatLocalTime('2025-11-25T04:30:00Z', 'time') // "4:30 AM"
 * formatLocalTime('2025-11-25T04:30:00Z', 'relative') // "5 minutes ago"
 */
export const formatLocalTime = (utcTimestamp, style = 'medium', timezone = null) => {
  if (!utcTimestamp) return 'N/A';

  try {
    const date = new Date(utcTimestamp);

    // Check if date is valid
    if (isNaN(date.getTime())) {
      console.warn('Invalid date:', utcTimestamp);
      return 'Invalid date';
    }

    const userTimezone = timezone || getUserTimezone();

    // Handle relative time
    if (style === 'relative') {
      return formatRelativeTime(date);
    }

    // Format options based on style
    let options = {
      timeZone: userTimezone
    };

    switch (style) {
      case 'full':
        options = {
          ...options,
          dateStyle: 'full',
          timeStyle: 'long'
        };
        break;
      case 'long':
        options = {
          ...options,
          dateStyle: 'long',
          timeStyle: 'medium'
        };
        break;
      case 'medium':
        options = {
          ...options,
          dateStyle: 'medium',
          timeStyle: 'short'
        };
        break;
      case 'short':
        options = {
          ...options,
          dateStyle: 'short',
          timeStyle: 'short'
        };
        break;
      case 'time':
        options = {
          ...options,
          timeStyle: 'short'
        };
        break;
      case 'date':
        options = {
          ...options,
          dateStyle: 'medium'
        };
        break;
      default:
        options = {
          ...options,
          dateStyle: 'medium',
          timeStyle: 'short'
        };
    }

    return new Intl.DateTimeFormat('en-US', options).format(date);
  } catch (error) {
    console.error('Error formatting date:', error, utcTimestamp);
    return 'Invalid date';
  }
};

/**
 * Format time as relative (e.g., "5 minutes ago")
 * @param {Date} date - Date to format
 * @returns {string} Relative time string
 */
export const formatRelativeTime = (date) => {
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  const diffMonth = Math.floor(diffDay / 30);
  const diffYear = Math.floor(diffDay / 365);

  if (diffSec < 60) {
    return diffSec === 1 ? '1 second ago' : `${diffSec} seconds ago`;
  } else if (diffMin < 60) {
    return diffMin === 1 ? '1 minute ago' : `${diffMin} minutes ago`;
  } else if (diffHour < 24) {
    return diffHour === 1 ? '1 hour ago' : `${diffHour} hours ago`;
  } else if (diffDay < 30) {
    return diffDay === 1 ? '1 day ago' : `${diffDay} days ago`;
  } else if (diffMonth < 12) {
    return diffMonth === 1 ? '1 month ago' : `${diffMonth} months ago`;
  } else {
    return diffYear === 1 ? '1 year ago' : `${diffYear} years ago`;
  }
};

/**
 * Format date range
 * @param {string|Date} startUtc - Start UTC timestamp
 * @param {string|Date} endUtc - End UTC timestamp
 * @param {string} style - Format style
 * @returns {string} Formatted date range
 *
 * @example
 * formatDateRange('2025-11-25T04:00:00Z', '2025-11-25T06:00:00Z')
 * // "Nov 25, 2025, 4:00 AM - 6:00 AM"
 */
export const formatDateRange = (startUtc, endUtc, style = 'medium') => {
  const start = formatLocalTime(startUtc, style);
  const end = formatLocalTime(endUtc, 'time'); // Just show time for end if same day

  const startDate = new Date(startUtc);
  const endDate = new Date(endUtc);

  // If same day, don't repeat the date
  if (startDate.toDateString() === endDate.toDateString()) {
    return `${start} - ${end}`;
  }

  return `${start} - ${formatLocalTime(endUtc, style)}`;
};

/**
 * Convert local time to UTC for sending to backend
 * @param {Date} localDate - Local date to convert
 * @returns {string} ISO 8601 UTC string
 */
export const toUTC = (localDate) => {
  return localDate.toISOString();
};

/**
 * Get current UTC time as ISO string
 * @returns {string} Current UTC time in ISO format
 */
export const getCurrentUTC = () => {
  return new Date().toISOString();
};

/**
 * React component helper: Format timestamp with auto-update for relative times
 * Use with useEffect to update relative times periodically
 *
 * Note: Import React and use hooks in your component:
 * import React, { useState, useEffect } from 'react';
 *
 * Example:
 * const [formattedTime, setFormattedTime] = useState(formatLocalTime(timestamp, 'relative'));
 * useEffect(() => {
 *   const interval = setInterval(() => {
 *     setFormattedTime(formatLocalTime(timestamp, 'relative'));
 *   }, 60000);
 *   return () => clearInterval(interval);
 * }, [timestamp]);
 */

// Export timezone info
export const timezoneInfo = {
  get timezone() {
    return getUserTimezone();
  },
  get offset() {
    return getTimezoneOffset();
  },
  get offsetMinutes() {
    return -new Date().getTimezoneOffset();
  }
};

export default {
  formatLocalTime,
  formatRelativeTime,
  formatDateRange,
  getUserTimezone,
  getTimezoneOffset,
  toUTC,
  getCurrentUTC,
  timezoneInfo
};
