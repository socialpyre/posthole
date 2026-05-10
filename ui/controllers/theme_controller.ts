import { Controller } from "@hotwired/stimulus";

type Choice = "light" | "dark" | "system";
const ORDER: Choice[] = ["light", "dark", "system"];
const KEY = "postpit:theme";

export default class extends Controller<HTMLElement> {
  private mql?: MediaQueryList;
  private onMediaChange = (): void => this.applyEffective();

  connect(): void {
    this.mql = window.matchMedia("(prefers-color-scheme: dark)");
    this.attachMediaListener();
  }

  disconnect(): void {
    this.mql?.removeEventListener("change", this.onMediaChange);
  }

  cycle(): void {
    const current = (this.read() as Choice | null) ?? "light";
    const next = ORDER[(ORDER.indexOf(current) + 1) % ORDER.length];

    this.write(next);

    document.documentElement.setAttribute("data-theme-choice", next);

    this.applyEffective();
    this.attachMediaListener();
  }

  private applyEffective(): void {
    const choice = (this.read() as Choice | null) ?? "light";
    const dark = choice === "dark" || (choice === "system" && !!this.mql?.matches);

    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  }

  private attachMediaListener(): void {
    if (!this.mql) return;

    if ((this.read() ?? "light") === "system")
      this.mql.addEventListener("change", this.onMediaChange);
    else this.mql.removeEventListener("change", this.onMediaChange);
  }

  private read(): string | null {
    try {
      return localStorage.getItem(KEY);
    } catch {
      return null;
    }
  }

  private write(value: string): void {
    try {
      localStorage.setItem(KEY, value);
    } catch {
      // localStorage unavailable (private browsing); skip persistence.
    }
  }
}
