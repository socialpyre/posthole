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

    // Past the 5s grace window but before the 15s watchdog — proves the
    // grace timer was actually canceled rather than just delayed.
    vi.advanceTimersByTime(10_000);
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

  it("watchdog: silent disconnect with no error event still flips to reconnecting + reopens", async () => {
    const { root, unmount } = await mountController<Liveness>({
      identifier: "liveness",
      controllerClass: LivenessController,
      html: FIXTURE,
    });
    teardown = unmount;

    expect(FakeEventSource.instances.length).toBe(1);

    // No error, no pings — the server is silently dead, EventSource is stuck
    // on a half-open socket. The watchdog must catch it.
    vi.advanceTimersByTime(15_000);
    expect(root.dataset.livenessState).toBe("reconnecting");
    // The source was reopened so the browser drops the stale socket.
    expect(FakeEventSource.instances.length).toBe(2);

    // After the existing 5s grace, with still no recovery, go offline.
    vi.advanceTimersByTime(5_000);
    expect(root.dataset.livenessState).toBe("offline");
  });

  it("watchdog: ping on the reopened source recovers and re-arms the watchdog", async () => {
    const { root, unmount } = await mountController<Liveness>({
      identifier: "liveness",
      controllerClass: LivenessController,
      html: FIXTURE,
    });
    teardown = unmount;

    vi.advanceTimersByTime(15_000); // watchdog fires, source reopens
    expect(FakeEventSource.instances.length).toBe(2);
    expect(root.dataset.livenessState).toBe("reconnecting");

    // A ping on the NEW source — proves we're listening on the reopened one.
    currentSource().emit("ping");
    expect(root.dataset.livenessState).toBe("live");

    // Watchdog should be re-armed: another silent stretch trips it again.
    vi.advanceTimersByTime(15_000);
    expect(root.dataset.livenessState).toBe("reconnecting");
    expect(FakeEventSource.instances.length).toBe(3);
  });

  it("watchdog: recovery via ping re-arms the watchdog even after an error", async () => {
    const { root, unmount } = await mountController<Liveness>({
      identifier: "liveness",
      controllerClass: LivenessController,
      html: FIXTURE,
    });
    teardown = unmount;

    // Transient drop + recovery via ping.
    currentSource().emit("error");
    expect(root.dataset.livenessState).toBe("reconnecting");
    currentSource().emit("ping");
    expect(root.dataset.livenessState).toBe("live");

    // Watchdog must still be running after recovery — 15s of silence trips it.
    vi.advanceTimersByTime(15_000);
    expect(root.dataset.livenessState).toBe("reconnecting");
  });

  it("repeated errors after grace expires do not bounce offline back to reconnecting", async () => {
    const { root, unmount } = await mountController<Liveness>({
      identifier: "liveness",
      controllerClass: LivenessController,
      html: FIXTURE,
    });
    teardown = unmount;

    currentSource().emit("error");
    vi.advanceTimersByTime(5_000);
    expect(root.dataset.livenessState).toBe("offline");

    // Simulate the browser's auto-retry storm: each failed reconnect fires
    // another `error`. None of them should flip us back to "reconnecting".
    for (let i = 0; i < 5; i++) {
      currentSource().emit("error");
      vi.advanceTimersByTime(3_000);
    }
    expect(root.dataset.livenessState).toBe("offline");
  });

  it("watchdog: mid-grace silence still re-arms the watchdog for a second silent stall", async () => {
    const { root, unmount } = await mountController<Liveness>({
      identifier: "liveness",
      controllerClass: LivenessController,
      html: FIXTURE,
    });
    teardown = unmount;

    // First: transient drop arms the grace timer.
    currentSource().emit("error");
    expect(root.dataset.livenessState).toBe("reconnecting");

    // Watchdog fires while grace is still armed — onError short-circuits,
    // but the watchdog must still re-arm itself.
    vi.advanceTimersByTime(15_000);
    expect(FakeEventSource.instances.length).toBe(2);

    // Grace fires → offline.
    vi.advanceTimersByTime(5_000);
    expect(root.dataset.livenessState).toBe("offline");

    // Recover, then a second silent stall: the watchdog should still trip.
    currentSource().emit("ping");
    expect(root.dataset.livenessState).toBe("live");
    vi.advanceTimersByTime(15_000);
    expect(root.dataset.livenessState).toBe("reconnecting");
    expect(FakeEventSource.instances.length).toBe(3);
  });

  it("watchdog: error on the reopened source does not break the grace guard", async () => {
    const { root, unmount } = await mountController<Liveness>({
      identifier: "liveness",
      controllerClass: LivenessController,
      html: FIXTURE,
    });
    teardown = unmount;

    vi.advanceTimersByTime(15_000); // watchdog fires, source reopens
    expect(root.dataset.livenessState).toBe("reconnecting");
    expect(FakeEventSource.instances.length).toBe(2);

    // Reopened source immediately errors — guard should swallow it so we
    // don't restart the grace cycle.
    currentSource().emit("error");
    expect(root.dataset.livenessState).toBe("reconnecting");
    vi.advanceTimersByTime(5_000);
    expect(root.dataset.livenessState).toBe("offline");
  });

  it("watchdog: pings emitted on a closed source are no-ops (no zombie listeners)", async () => {
    const { root, unmount } = await mountController<Liveness>({
      identifier: "liveness",
      controllerClass: LivenessController,
      html: FIXTURE,
    });
    teardown = unmount;

    const stale = currentSource();
    vi.advanceTimersByTime(15_000); // watchdog reopens
    expect(FakeEventSource.instances.length).toBe(2);
    expect(root.dataset.livenessState).toBe("reconnecting");

    // Stale source's listeners must have been detached on close.
    stale.emit("ping");
    expect(root.dataset.livenessState).toBe("reconnecting");
  });

  it("watchdog: regular pings reset the timer so the badge stays live", async () => {
    const { root, unmount } = await mountController<Liveness>({
      identifier: "liveness",
      controllerClass: LivenessController,
      html: FIXTURE,
    });
    teardown = unmount;

    // Server is healthy: ping every 10s, well inside the 15s window.
    for (let i = 0; i < 5; i++) {
      vi.advanceTimersByTime(10_000);
      currentSource().emit("ping");
    }
    expect(root.dataset.livenessState).toBe("live");
    expect(FakeEventSource.instances.length).toBe(1);
  });
});
