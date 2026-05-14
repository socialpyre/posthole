import { Controller } from "@hotwired/stimulus";

// Source of truth for the active tab is the server's rendered
// `aria-selected` / `tabindex` / `hidden` markup; `connect()` does not
// reconcile against the URL. The URL only changes via `persist()` after
// user interaction. If you ever ship a hydration path that produces a
// stale DOM (Turbo morphing, cache-restored snapshots, etc.), revisit:
// you'd need to read `URL.searchParams.get(this.paramValue)` on connect
// and call `activate()` on the matching tab.
export default class extends Controller<HTMLElement> {
  static targets = ["tab", "panel"];

  static values = {
    param: String,
    defaultPanel: String,
  };

  declare readonly tabTargets: HTMLButtonElement[];
  declare readonly panelTargets: HTMLElement[];
  declare readonly paramValue: string;
  declare readonly defaultPanelValue: string;

  keydown(event: KeyboardEvent): void {
    const tabs = this.tabTargets;

    const current = event.currentTarget as HTMLButtonElement;
    const idx = tabs.indexOf(current);

    let next = idx;
    if (event.key === "ArrowRight") next = (idx + 1) % tabs.length;
    else if (event.key === "ArrowLeft") next = (idx - 1 + tabs.length) % tabs.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = tabs.length - 1;
    else return;

    event.preventDefault();

    tabs[next].focus();
    this.activate(tabs[next]);
  }

  select(event: Event): void {
    this.activate(event.currentTarget as HTMLButtonElement);
  }

  private activate(active: HTMLButtonElement): void {
    const panelKey = active.dataset.tabsKey;

    for (const tab of this.tabTargets) {
      const isActive = tab === active;
      tab.setAttribute("aria-selected", isActive ? "true" : "false");
      tab.tabIndex = isActive ? 0 : -1;
    }

    for (const panel of this.panelTargets) {
      panel.hidden = panel.dataset.panel !== panelKey;
    }

    if (panelKey) this.persist(panelKey);
  }

  private persist(panelKey: string): void {
    const url = new URL(window.location.href);

    if (panelKey === this.defaultPanelValue) {
      url.searchParams.delete(this.paramValue);
    } else {
      url.searchParams.set(this.paramValue, panelKey);
    }

    history.replaceState(history.state, "", url.toString());
  }
}
