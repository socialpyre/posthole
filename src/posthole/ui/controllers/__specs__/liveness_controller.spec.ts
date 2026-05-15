import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import LivenessController from "../liveness_controller.ts";
import { mountController } from "../../__specs__/helpers.ts";

const FIXTURE = `
  <span data-controller="liveness"
        data-liveness-stream-value="/_health/stream"
        data-liveness-state="live">
    <span data-liveness-target="label" data-liveness-label="live">live</span>
    <span data-liveness-target="label" data-liveness-label="reconnecting" hidden>reconnecting</span>
    <span data-liveness-target="label" data-liveness-label="offline" hidden>offline</span>
  </span>
`;

type Liveness = InstanceType<typeof LivenessController>;

// EventSource isn't part of jsdom — fake it.
type Listener = (event: Event) => void;
class FakeEventSource {
  static instances: FakeEventSource[] = [];

  url: string;
  private listeners: Record<string, Listener[]> = {};

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: Listener): void {
    (this.listeners[type] ??= []).push(listener);
  }

  removeEventListener(type: string, listener: Listener): void {
    const list = this.listeners[type];
    if (!list) return;
    const idx = list.indexOf(listener);
    if (idx !== -1) list.splice(idx, 1);
  }

  close(): void {
    this.listeners = {};
  }

  emit(type: string, event: Event = new Event(type)): void {
    for (const listener of this.listeners[type] ?? []) listener(event);
  }
}

let teardown: (() => void) | undefined;

beforeEach(() => {
  vi.useFakeTimers();
  FakeEventSource.instances = [];
  (globalThis as unknown as { EventSource: typeof FakeEventSource }).EventSource = FakeEventSource;
});

afterEach(() => {
  teardown?.();
  teardown = undefined;
  vi.useRealTimers();
});

function currentSource(): FakeEventSource {
  const last = FakeEventSource.instances[FakeEventSource.instances.length - 1];
  if (!last) throw new Error("no EventSource constructed");
  return last;
}

function visibleLabel(root: HTMLElement): string | null {
  const visible = [...root.querySelectorAll<HTMLElement>("[data-liveness-target='label']")].find(
    (el) => !el.hidden,
  );
  return visible?.dataset.livenessLabel ?? null;
}

describe("liveness_controller", () => {
  it("starts optimistically in the live state and opens a stream", async () => {
    const { root, unmount } = await mountController<Liveness>({
      identifier: "liveness",
      controllerClass: LivenessController,
      html: FIXTURE,
    });
    teardown = unmount;

    expect(root.dataset.livenessState).toBe("live");
    expect(visibleLabel(root)).toBe("live");
    expect(currentSource().url).toBe("/_health/stream");
  });

  it("transitions live → reconnecting on error, then offline after the grace timer", async () => {
    const { root, unmount } = await mountController<Liveness>({
      identifier: "liveness",
      controllerClass: LivenessController,
      html: FIXTURE,
    });
    teardown = unmount;

    currentSource().emit("error");
    expect(root.dataset.livenessState).toBe("reconnecting");
    expect(visibleLabel(root)).toBe("reconnecting");

    vi.advanceTimersByTime(5_000);
    expect(root.dataset.livenessState).toBe("offline");
    expect(visibleLabel(root)).toBe("offline");
  });

  it("recovery before the grace timer cancels the offline transition", async () => {
    const { root, unmount } = await mountController<Liveness>({
      identifier: "liveness",
      controllerClass: LivenessController,
      html: FIXTURE,
    });
    teardown = unmount;

    currentSource().emit("error");
    expect(root.dataset.livenessState).toBe("reconnecting");

    currentSource().emit("ping");
    expect(root.dataset.livenessState).toBe("live");

    vi.advanceTimersByTime(60_000);
    expect(root.dataset.livenessState).toBe("live");
  });

  it("repeated errors during reconnecting do not extend the grace window", async () => {
    const { root, unmount } = await mountController<Liveness>({
      identifier: "liveness",
      controllerClass: LivenessController,
      html: FIXTURE,
    });
    teardown = unmount;

    currentSource().emit("error");
    vi.advanceTimersByTime(3_000);
    currentSource().emit("error"); // would-be reset — must be a no-op
    vi.advanceTimersByTime(2_000); // total 5s → grace expires
    expect(root.dataset.livenessState).toBe("offline");
  });

  it("recovers from offline when a ping eventually lands", async () => {
    const { root, unmount } = await mountController<Liveness>({
      identifier: "liveness",
      controllerClass: LivenessController,
      html: FIXTURE,
    });
    teardown = unmount;

    currentSource().emit("error");
    vi.advanceTimersByTime(5_000);
    expect(root.dataset.livenessState).toBe("offline");

    currentSource().emit("ping");
    expect(root.dataset.livenessState).toBe("live");
  });
});
