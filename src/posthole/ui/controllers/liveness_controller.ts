import { Controller } from "@hotwired/stimulus";

// State machine:
//   live          — EventSource open and we have received at least one ping
//                   recently (or the page just loaded, which is optimistically
//                   live since the server obviously responded).
//   reconnecting  — EventSource fired `error`. The browser is auto-retrying;
//                   we stay in this state until either a fresh `message`
//                   arrives (back to live) or the grace timer fires (offline).
//   offline       — Grace timer expired without recovery. Stays here until
//                   a future `message` lands.
//
// CSS reads `data-liveness-state` on the wrapper and toggles dot color +
// pulse animation + label. The badge has three labels stamped into the
// markup, one per state; the controller flips which one is visible.

type State = "live" | "reconnecting" | "offline";

const GRACE_MS = 5_000;

export default class extends Controller<HTMLElement> {
  static targets = ["label"];
  static values = { stream: String };

  declare readonly labelTargets: HTMLElement[];
  declare readonly streamValue: string;

  private source?: EventSource;
  private graceTimer?: number;

  connect(): void {
    this.apply("live");
    this.source = new EventSource(this.streamValue);
    this.source.addEventListener("open", this.onOpen);
    this.source.addEventListener("message", this.onMessage);
    this.source.addEventListener("ping", this.onMessage);
    this.source.addEventListener("error", this.onError);
  }

  disconnect(): void {
    this.source?.removeEventListener("open", this.onOpen);
    this.source?.removeEventListener("message", this.onMessage);
    this.source?.removeEventListener("ping", this.onMessage);
    this.source?.removeEventListener("error", this.onError);
    this.source?.close();
    this.source = undefined;

    if (this.graceTimer !== undefined) {
      window.clearTimeout(this.graceTimer);
      this.graceTimer = undefined;
    }
  }

  private onOpen = (): void => {
    this.recover();
  };

  private onMessage = (): void => {
    this.recover();
  };

  private onError = (): void => {
    // EventSource fires `error` on every transient drop while it auto-retries.
    // If we're already in a non-live state, don't reset the grace timer —
    // that would extend the "reconnecting" window indefinitely on flaky
    // networks. Only the first error after a recovery starts the timer.
    if (this.graceTimer !== undefined) return;
    this.apply("reconnecting");
    this.graceTimer = window.setTimeout(() => {
      this.graceTimer = undefined;
      this.apply("offline");
    }, GRACE_MS);
  };

  private recover(): void {
    if (this.graceTimer !== undefined) {
      window.clearTimeout(this.graceTimer);
      this.graceTimer = undefined;
    }
    this.apply("live");
  }

  private apply(state: State): void {
    if (this.element.dataset.livenessState === state) return;
    this.element.dataset.livenessState = state;
    for (const label of this.labelTargets) {
      label.hidden = label.dataset.livenessLabel !== state;
    }
  }
}
