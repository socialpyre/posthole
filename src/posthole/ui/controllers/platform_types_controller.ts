import { Controller } from "@hotwired/stimulus";

export default class extends Controller<HTMLElement> {
  static targets = ["typeSelect"];

  declare readonly typeSelectTarget: HTMLSelectElement;
  declare readonly hasTypeSelectTarget: boolean;

  connect(): void {
    this.applyFilter();
  }

  filter(): void {
    this.applyFilter();
  }

  private applyFilter(): void {
    if (!this.hasTypeSelectTarget) return;

    const platform = this.selectedPlatform();
    const select = this.typeSelectTarget;
    let clearedHidden = false;

    for (const group of select.querySelectorAll("optgroup")) {
      const matches = !platform || group.dataset.platform === platform;
      group.hidden = !matches;
      group.disabled = !matches;
      if (!matches) {
        for (const opt of group.querySelectorAll("option")) {
          if (opt.selected) clearedHidden = true;
        }
      }
    }

    if (clearedHidden) select.value = "";
  }

  private selectedPlatform(): string {
    const checked = this.element.querySelector<HTMLInputElement>('input[name="platform"]:checked');
    return checked?.value ?? "";
  }
}
