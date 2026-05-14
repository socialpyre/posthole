import { Controller } from "@hotwired/stimulus";

export default class extends Controller<HTMLElement> {
  static targets = ["slide", "dot", "counter", "prev", "next"];

  declare readonly counterTarget: HTMLElement;
  declare readonly dotTargets: HTMLElement[];
  declare readonly hasCounterTarget: boolean;
  declare readonly hasNextTarget: boolean;
  declare readonly hasPrevTarget: boolean;
  declare readonly nextTarget: HTMLButtonElement;
  declare readonly prevTarget: HTMLButtonElement;
  declare readonly slideTargets: HTMLElement[];

  private active = 0;

  connect(): void {
    this.element.addEventListener("keydown", this.onKeydown);
    if (!this.element.hasAttribute("tabindex")) this.element.tabIndex = 0;

    const initial = this.slideTargets.findIndex((s) => s.hasAttribute("data-active"));

    this.active = initial === -1 ? 0 : initial;
    this.render();
  }

  disconnect(): void {
    this.element.removeEventListener("keydown", this.onKeydown);
  }

  go(event: Event): void {
    const idx = Number((event.currentTarget as HTMLElement).dataset.index ?? "0");
    this.setActive(idx);
  }

  next(): void {
    this.setActive(Math.min(this.active + 1, this.slideTargets.length - 1));
  }

  prev(): void {
    this.setActive(Math.max(this.active - 1, 0));
  }

  private onKeydown = (event: KeyboardEvent): void => {
    if (event.key === "ArrowRight") {
      event.preventDefault();
      this.next();
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      this.prev();
    }
  };

  private render(): void {
    const idx = this.active;
    const last = this.slideTargets.length - 1;

    this.slideTargets.forEach((slide, i) => {
      slide.toggleAttribute("data-active", i === idx);
      slide.setAttribute("aria-hidden", i === idx ? "false" : "true");
    });

    this.dotTargets.forEach((dot, i) => dot.toggleAttribute("data-active", i === idx));

    if (this.hasCounterTarget) {
      this.counterTarget.textContent = `${idx + 1}/${this.slideTargets.length}`;
    }

    if (this.hasPrevTarget) this.prevTarget.hidden = idx === 0;
    if (this.hasNextTarget) this.nextTarget.hidden = idx === last;
  }

  private setActive(idx: number): void {
    this.active = idx;
    this.render();
  }
}
