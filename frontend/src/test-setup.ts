import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// jsdom polyfills for libraries that rely on layout APIs (Tiptap/ProseMirror)
if (typeof Range !== "undefined") {
  if (!Range.prototype.getClientRects) {
    // @ts-expect-error - polyfill
    Range.prototype.getClientRects = function () {
      return {
        item: () => null,
        length: 0,
        [Symbol.iterator]: function* () {},
      };
    };
  }
  if (!Range.prototype.getBoundingClientRect) {
    // @ts-expect-error - polyfill
    Range.prototype.getBoundingClientRect = function () {
      return { x: 0, y: 0, width: 0, height: 0, top: 0, right: 0, bottom: 0, left: 0, toJSON: () => ({}) };
    };
  }
}
if (typeof Element !== "undefined") {
  if (!Element.prototype.getClientRects) {
    // @ts-expect-error - polyfill
    Element.prototype.getClientRects = function () {
      return {
        item: () => null,
        length: 0,
        [Symbol.iterator]: function* () {},
      };
    };
  }
  if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = function () {};
  }
}

afterEach(() => {
  cleanup();
});
