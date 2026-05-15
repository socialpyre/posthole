import { Controller } from "@hotwired/stimulus";

type State = "live" | "reconnecting" | "offline";

const GRACE_MS = 5_000;
const HEARTBEAT_TIMEOUT_MS = 15_000;

export default class extends Controller<HTMLElement> {
  static targets = ["label"];
  static values = { stream: String };

  declare readonly labelTargets: HTMLElement[];
  declare readonly streamValue: string;

  private source?: EventSource;
  private graceTimer?: number;
  private heartbeatTimer?: number;

  connect(): void {
    this.apply("live");
    this.openSource();
    this.armHeartbeat();
  }

  disconnect(): void {
    this.closeSource();
    this.clearGraceTimer();
    this.clearHeartbeat();
  }

  private onOpen = (): void => {
    this.recover();
  };

  private onMessage = (): void => {
    this.recover();
  };

  private onError = (): void => {
    if (this.graceTimer !== undefined) return;
    if (this.element.dataset.livenessState === "offline") return;

    this.apply("reconnecting");
    this.graceTimer = window.setTimeout(() => {
      this.graceTimer = undefined;
      this.apply("offline");
    }, GRACE_MS);
  };

  private onHeartbeatTimeout = (): void => {
    this.heartbeatTimer = undefined;
    this.onError();
    this.reopenSource();
    this.armHeartbeat();
  };

  private recover(): void {
    this.clearGraceTimer();
    this.apply("live");
    this.armHeartbeat();
  }

  private openSource(): void {
    this.source = new EventSource(this.streamValue);
    this.source.addEventListener("open", this.onOpen);
    this.source.addEventListener("message", this.onMessage);
    this.source.addEventListener("ping", this.onMessage);
    this.source.addEventListener("error", this.onError);
  }

  private closeSource(): void {
    if (!this.source) return;
    this.source.removeEventListener("open", this.onOpen);
    this.source.removeEventListener("message", this.onMessage);
    this.source.removeEventListener("ping", this.onMessage);
    this.source.removeEventListener("error", this.onError);
    this.source.close();
    this.source = undefined;
  }

  private reopenSource(): void {
    this.closeSource();
    this.openSource();
  }

  private armHeartbeat(): void {
    this.clearHeartbeat();
    this.heartbeatTimer = window.setTimeout(this.onHeartbeatTimeout, HEARTBEAT_TIMEOUT_MS);
  }

  private clearHeartbeat(): void {
    if (this.heartbeatTimer !== undefined) {
      window.clearTimeout(this.heartbeatTimer);
      this.heartbeatTimer = undefined;
    }
  }

  private clearGraceTimer(): void {
    if (this.graceTimer !== undefined) {
      window.clearTimeout(this.graceTimer);
      this.graceTimer = undefined;
    }
  }

  private apply(state: State): void {
    if (this.element.dataset.livenessState === state) return;
    this.element.dataset.livenessState = state;
    for (const label of this.labelTargets) {
      label.hidden = label.dataset.livenessLabel !== state;
    }
  }
}
