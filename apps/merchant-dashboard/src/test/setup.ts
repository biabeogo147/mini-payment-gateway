import * as matchers from "@testing-library/jest-dom/matchers";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeAll, expect, vi } from "vitest";

expect.extend(matchers);

beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, "offsetWidth", {
    configurable: true,
    get() {
      return 640;
    },
  });
  Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
    configurable: true,
    get() {
      return 320;
    },
  });
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(
    () =>
      ({
        width: 640,
        height: 320,
        top: 0,
        left: 0,
        right: 640,
        bottom: 320,
        x: 0,
        y: 0,
        toJSON: () => undefined,
      }) as DOMRect,
  );

  class TestResizeObserver {
    private readonly callback: ResizeObserverCallback;

    constructor(callback: ResizeObserverCallback) {
      this.callback = callback;
    }

    observe(target: Element) {
      this.callback(
        [
          {
            target,
            contentRect: {
              width: 640,
              height: 320,
              top: 0,
              left: 0,
              right: 640,
              bottom: 320,
              x: 0,
              y: 0,
              toJSON: () => undefined,
            } as DOMRectReadOnly,
          } as ResizeObserverEntry,
        ],
        this,
      );
    }

    unobserve() {
      return undefined;
    }

    disconnect() {
      return undefined;
    }
  }

  vi.stubGlobal("ResizeObserver", TestResizeObserver);
});

afterEach(() => {
  cleanup();
});
