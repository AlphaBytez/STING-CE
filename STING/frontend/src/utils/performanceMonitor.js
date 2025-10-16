/**
 * Performance Monitor Utility
 * Tracks performance metrics to demonstrate theme performance differences
 */
import React from 'react';

class PerformanceMonitor {
  constructor() {
    this.metrics = {};
    this.observers = [];
    this.isMonitoring = false;
  }

  startMonitoring() {
    if (this.isMonitoring) return;
    
    this.isMonitoring = true;
    this.observeLayoutShifts();
    this.observePaintTiming();
    this.observeResourceTiming();
    this.monitorFrameRate();
  }

  stopMonitoring() {
    this.isMonitoring = false;
    this.observers.forEach(observer => observer.disconnect());
    this.observers = [];
  }

  observeLayoutShifts() {
    if (!window.PerformanceObserver) return;

    try {
      const observer = new PerformanceObserver((list) => {
        let cumulativeLayoutShift = 0;
        for (const entry of list.getEntries()) {
          if (!entry.hadRecentInput) {
            cumulativeLayoutShift += entry.value;
          }
        }
        this.metrics.cumulativeLayoutShift = (this.metrics.cumulativeLayoutShift || 0) + cumulativeLayoutShift;
      });

      observer.observe({ entryTypes: ['layout-shift'] });
      this.observers.push(observer);
    } catch (e) {
      console.warn('Layout shift observation not supported');
    }
  }

  observePaintTiming() {
    if (!window.PerformanceObserver) return;

    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.name === 'first-contentful-paint') {
            this.metrics.firstContentfulPaint = entry.startTime;
          }
          if (entry.name === 'largest-contentful-paint') {
            this.metrics.largestContentfulPaint = entry.startTime;
          }
        }
      });

      observer.observe({ entryTypes: ['paint', 'largest-contentful-paint'] });
      this.observers.push(observer);
    } catch (e) {
      console.warn('Paint timing observation not supported');
    }
  }

  observeResourceTiming() {
    if (!window.PerformanceObserver) return;

    try {
      const observer = new PerformanceObserver((list) => {
        let totalResourceTime = 0;
        let cssResourceTime = 0;
        let resourceCount = 0;

        for (const entry of list.getEntries()) {
          const duration = entry.responseEnd - entry.startTime;
          totalResourceTime += duration;
          resourceCount++;

          if (entry.name.includes('.css') || entry.name.includes('theme')) {
            cssResourceTime += duration;
          }
        }

        this.metrics.averageResourceTime = totalResourceTime / resourceCount;
        this.metrics.cssLoadTime = cssResourceTime;
        this.metrics.resourceCount = resourceCount;
      });

      observer.observe({ entryTypes: ['resource'] });
      this.observers.push(observer);
    } catch (e) {
      console.warn('Resource timing observation not supported');
    }
  }

  monitorFrameRate() {
    let lastTime = performance.now();
    let frameCount = 0;
    let totalFrameTime = 0;

    const measureFrame = (currentTime) => {
      if (!this.isMonitoring) return;

      const deltaTime = currentTime - lastTime;
      totalFrameTime += deltaTime;
      frameCount++;

      if (frameCount >= 60) { // Calculate FPS every 60 frames
        const averageFrameTime = totalFrameTime / frameCount;
        this.metrics.averageFPS = Math.round(1000 / averageFrameTime);
        frameCount = 0;
        totalFrameTime = 0;
      }

      lastTime = currentTime;
      requestAnimationFrame(measureFrame);
    };

    requestAnimationFrame(measureFrame);
  }

  getMetrics() {
    return {
      ...this.metrics,
      memoryUsage: this.getMemoryUsage(),
      renderingMetrics: this.getRenderingMetrics(),
      timestamp: Date.now()
    };
  }

  getMemoryUsage() {
    if (!performance.memory) {
      return { supported: false };
    }

    return {
      supported: true,
      usedJSHeapSize: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024), // MB
      totalJSHeapSize: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024), // MB
      jsHeapSizeLimit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024) // MB
    };
  }

  getRenderingMetrics() {
    const navigation = performance.getEntriesByType('navigation')[0];
    
    if (!navigation) {
      return { supported: false };
    }

    return {
      supported: true,
      domComplete: Math.round(navigation.domComplete),
      loadComplete: Math.round(navigation.loadEventEnd),
      domInteractive: Math.round(navigation.domInteractive),
      pageLoadTime: Math.round(navigation.loadEventEnd - navigation.navigationStart)
    };
  }

  compareThemePerformance(themeMetrics) {
    const currentMetrics = this.getMetrics();
    
    return {
      fpsImprovement: currentMetrics.averageFPS - (themeMetrics.averageFPS || 0),
      memoryReduction: (themeMetrics.memoryUsage?.usedJSHeapSize || 0) - (currentMetrics.memoryUsage?.usedJSHeapSize || 0),
      layoutShiftReduction: (themeMetrics.cumulativeLayoutShift || 0) - (currentMetrics.cumulativeLayoutShift || 0),
      paintTimeImprovement: (themeMetrics.largestContentfulPaint || 0) - (currentMetrics.largestContentfulPaint || 0)
    };
  }

  generatePerformanceReport() {
    const metrics = this.getMetrics();
    
    return {
      overall: this.getOverallScore(metrics),
      details: metrics,
      recommendations: this.getRecommendations(metrics),
      themeOptimization: this.getThemeOptimizationSuggestions(metrics)
    };
  }

  getOverallScore(metrics) {
    let score = 100;

    // Deduct points for poor metrics
    if (metrics.averageFPS < 30) score -= 20;
    else if (metrics.averageFPS < 45) score -= 10;

    if (metrics.cumulativeLayoutShift > 0.1) score -= 15;
    else if (metrics.cumulativeLayoutShift > 0.05) score -= 5;

    if (metrics.largestContentfulPaint > 4000) score -= 20;
    else if (metrics.largestContentfulPaint > 2500) score -= 10;

    if (metrics.memoryUsage?.usedJSHeapSize > 50) score -= 15;

    return Math.max(0, score);
  }

  getRecommendations(metrics) {
    const recommendations = [];

    if (metrics.averageFPS < 45) {
      recommendations.push({
        type: 'performance',
        priority: 'high',
        message: 'Low frame rate detected. Consider switching to Retro Terminal theme for better performance.',
        action: 'switch_theme'
      });
    }

    if (metrics.cumulativeLayoutShift > 0.1) {
      recommendations.push({
        type: 'stability',
        priority: 'medium',
        message: 'High layout shift detected. Retro Terminal theme has minimal layout changes.',
        action: 'optimize_layout'
      });
    }

    if (metrics.memoryUsage?.usedJSHeapSize > 50) {
      recommendations.push({
        type: 'memory',
        priority: 'medium',
        message: 'High memory usage. Retro Terminal theme uses fewer resources.',
        action: 'reduce_memory'
      });
    }

    return recommendations;
  }

  getThemeOptimizationSuggestions(metrics) {
    const suggestions = [];

    if (metrics.averageFPS < 30 || metrics.memoryUsage?.usedJSHeapSize > 100) {
      suggestions.push({
        theme: 'retro-terminal',
        reason: 'Critical performance issues detected',
        benefits: ['60+ FPS', 'Low memory usage', 'Fast rendering', 'No expensive effects']
      });
    } else if (metrics.averageFPS < 45 || metrics.cumulativeLayoutShift > 0.1) {
      suggestions.push({
        theme: 'retro-terminal',
        reason: 'Performance optimization recommended',
        benefits: ['Improved frame rate', 'Stable layout', 'Reduced resource usage']
      });
    }

    return suggestions;
  }
}

// Create a singleton instance
const performanceMonitor = new PerformanceMonitor();

// Hook for React components
export const usePerformanceMonitoring = (enabled = true) => {
  const [metrics, setMetrics] = React.useState(null);
  const [isMonitoring, setIsMonitoring] = React.useState(false);

  React.useEffect(() => {
    if (!enabled) return;

    performanceMonitor.startMonitoring();
    setIsMonitoring(true);

    const interval = setInterval(() => {
      setMetrics(performanceMonitor.getMetrics());
    }, 5000); // Update every 5 seconds

    return () => {
      clearInterval(interval);
      performanceMonitor.stopMonitoring();
      setIsMonitoring(false);
    };
  }, [enabled]);

  return {
    metrics,
    isMonitoring,
    generateReport: () => performanceMonitor.generatePerformanceReport(),
    compareThemes: (themeMetrics) => performanceMonitor.compareThemePerformance(themeMetrics)
  };
};

export default performanceMonitor;