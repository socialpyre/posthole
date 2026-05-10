import { Controller } from "@hotwired/stimulus";

const COLLAPSE_KEY = "postpit:sidebar-collapsed";

export default class extends Controller<HTMLElement> {
  open(): void {
    document.documentElement.setAttribute("data-drawer-open", "");
  }

  close(): void {
    document.documentElement.removeAttribute("data-drawer-open");
  }

  toggleCollapse(): void {
    const root = document.documentElement;
    const collapsed = root.hasAttribute("data-sidebar-collapsed");
    if (collapsed) {
      root.removeAttribute("data-sidebar-collapsed");
      this.write(null);
    } else {
      root.setAttribute("data-sidebar-collapsed", "");
      this.write("1");
    }
  }

  private write(value: string | null): void {
    try {
      if (value === null) localStorage.removeItem(COLLAPSE_KEY);
      else localStorage.setItem(COLLAPSE_KEY, value);
    } catch {
      // localStorage unavailable; skip persistence.
    }
  }
}
