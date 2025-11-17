import { useState, useCallback } from 'react';
import type { Dispatch, SetStateAction } from 'react';

/**
 * A drop-in replacement for useState that prevents loading states from being set to false
 * when the URL contains ?debugLoading=true query parameter.
 *
 * This is useful for UI development to keep loading states visible for styling and testing.
 *
 * @param initialValue - The initial loading state (typically true)
 * @returns A tuple [isLoading, setIsLoading] with the same API as useState
 *
 * @example
 * ```tsx
 * // Replace: const [isLoading, setIsLoading] = useState(true);
 * // With:    const [isLoading, setIsLoading] = useDebugLoading(true);
 *
 * // Usage with ?debugLoading=true in URL:
 * setIsLoading(false); // Will NOT update state - keeps loading visible
 *
 * // Usage without query parameter:
 * setIsLoading(false); // Works normally
 * ```
 */
export function useDebugLoading(initialValue: boolean = false): [boolean, Dispatch<SetStateAction<boolean>>] {
  const [loading, setLoading] = useState(initialValue);

  const setLoadingWithDebug = useCallback((value: SetStateAction<boolean>) => {
    // Check if debug mode is enabled via query parameter
    const isDebugMode = new URLSearchParams(window.location.search).get('debugLoading') === 'true';

    if (!isDebugMode) {
      // Normal mode - allow all updates
      setLoading(value);
      return;
    }

    // Debug mode - prevent setting to false
    if (typeof value === 'function') {
      // Handle functional updates: setLoading(prev => !prev)
      setLoading((prevLoading) => {
        const newValue = value(prevLoading);
        // Only apply the update if it's not transitioning to false
        return newValue === false ? prevLoading : newValue;
      });
    } else {
      // Handle direct values: setLoading(false)
      if (value !== false) {
        setLoading(value);
      }
      // If value is false, do nothing (keep loading state visible)
    }
  }, []);

  return [loading, setLoadingWithDebug];
}
