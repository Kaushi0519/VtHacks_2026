"use client";
// One shared ticking clock for every countdown, so all timers on screen agree to the second.
import { useSyncExternalStore } from "react";

const TICK_MS = 250;
let now = Date.now();
const listeners = new Set<() => void>();
let timer: ReturnType<typeof setInterval> | null = null;

function subscribe(listener: () => void) {
  listeners.add(listener);
  timer ??= setInterval(() => {
    now = Date.now();
    listeners.forEach((l) => l());
  }, TICK_MS);
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0 && timer) {
      clearInterval(timer);
      timer = null;
    }
  };
}

export const useNow = (): number => useSyncExternalStore(subscribe, () => now, () => now);
