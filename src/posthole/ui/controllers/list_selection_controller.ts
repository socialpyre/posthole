import { Controller } from "@hotwired/stimulus";

export default class extends Controller<HTMLElement> {
  static targets = ["row"];

  declare readonly rowTargets: HTMLAnchorElement[];

  connect(): void {
    const current = this.rowTargets.find((row) => row.getAttribute("aria-current") === "page");
    current?.scrollIntoView({ block: "nearest" });
  }

  select(event: Event): void {
    const link = event.currentTarget as HTMLAnchorElement;

    for (const row of this.rowTargets) row.removeAttribute("aria-current");
    link.setAttribute("aria-current", "page");
    this.element.setAttribute("data-inbox-pane", "detail");
  }
}
