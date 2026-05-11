import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ThemeController from "../theme_controller.ts";
import { mountController } from "../../__specs__/helpers.ts";

const ROOT = document.documentElement;
const KEY = "posthole:theme";
const FIXTURE = `<button data-controller="theme"></button>`;

type Theme = InstanceType<typeof ThemeController>;

let teardown: (() => void) | undefined;
let addListener: ReturnType<typeof vi.fn>;
let removeListener: ReturnType<typeof vi.fn>;
let systemMatches = false;

function installMatchMedia() {
  const factory = (query: string): MediaQueryList =>
    ({
      matches: systemMatches,
      media: query,
      onchange: null,
      addEventListener: addListener,
      removeEventListener: removeListener,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }) as unknown as MediaQueryList;

  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: vi.fn(factory),
  });
}

beforeEach(() => {
  localStorage.clear();
  ROOT.removeAttribute("data-theme");
  ROOT.removeAttribute("data-theme-choice");
  systemMatches = false;
  addListener = vi.fn();
  removeListener = vi.fn();
  installMatchMedia();
});

afterEach(() => {
  teardown?.();
  teardown = undefined;
});

describe("theme_controller", () => {
  it("cycle() rotates light → dark → system → light and writes localStorage each step", async () => {
    const { controller, unmount } = await mountController<Theme>({
      identifier: "theme",
      controllerClass: ThemeController,
      html: FIXTURE,
    });
    teardown = unmount;

    controller.cycle();
    expect(localStorage.getItem(KEY)).toBe("dark");
    expect(ROOT.getAttribute("data-theme-choice")).toBe("dark");
    expect(ROOT.getAttribute("data-theme")).toBe("dark");

    controller.cycle();
    expect(localStorage.getItem(KEY)).toBe("system");
    expect(ROOT.getAttribute("data-theme-choice")).toBe("system");

    controller.cycle();
    expect(localStorage.getItem(KEY)).toBe("light");
    expect(ROOT.getAttribute("data-theme")).toBe("light");
  });

  it("cycle to system with prefers-color-scheme:dark applies data-theme='dark'", async () => {
    localStorage.setItem(KEY, "dark");
    systemMatches = true;

    const { controller, unmount } = await mountController<Theme>({
      identifier: "theme",
      controllerClass: ThemeController,
      html: FIXTURE,
    });
    teardown = unmount;

    controller.cycle();

    expect(localStorage.getItem(KEY)).toBe("system");
    expect(ROOT.getAttribute("data-theme")).toBe("dark");
  });

  it("cycle to system with prefers-color-scheme:light applies data-theme='light'", async () => {
    localStorage.setItem(KEY, "dark");
    systemMatches = false;

    const { controller, unmount } = await mountController<Theme>({
      identifier: "theme",
      controllerClass: ThemeController,
      html: FIXTURE,
    });
    teardown = unmount;

    controller.cycle();

    expect(ROOT.getAttribute("data-theme")).toBe("light");
  });

  it("attaches the media-change listener only when the choice is 'system'", async () => {
    const { controller, unmount } = await mountController<Theme>({
      identifier: "theme",
      controllerClass: ThemeController,
      html: FIXTURE,
    });
    teardown = unmount;

    // Initial connect with no stored choice (defaults to "light") removes the listener.
    expect(addListener).not.toHaveBeenCalled();

    controller.cycle(); // → dark
    expect(addListener).not.toHaveBeenCalled();

    controller.cycle(); // → system
    expect(addListener).toHaveBeenCalledWith("change", expect.any(Function));
  });
});
